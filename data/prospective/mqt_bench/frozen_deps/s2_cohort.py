"""S2: prospective mutant cohort generation + eligibility freeze.
Frozen sampling: enumerate ALL sites, then a deterministic largest-remainder allocation over the 9
(operator, gate_class) strata, taking the first k per stratum after sorting by (location, sha256(definition)).
NO RNG is consumed. Preflight is INGESTION-ONLY: qutest lint + an assertion-free run. Kill/survive is never
computed or recorded in S2.
RUN: .venv-qutest-audit/bin/python research_repair/phase5_validation/s2_cohort/s2_cohort.py
"""
import csv, hashlib, json, os, subprocess, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "cross_tool_stage", "qutest"))
import qutest_adapter as QA
from rq3_feasibility_gate.core import mutants as MUT
from rq3_feasibility_gate.core.representation import canon_json, circuit_hash

S1 = os.path.join(ROOT, "research_repair", "phase5_validation", "s1_materialization")
SUBJ = json.load(open(os.path.join(S1, "S1_SUBJECTS.json")))
BASE_SEED = 20260730
PER_SUBJECT = 30
OPS = ("gate_deletion", "gate_insertion", "gate_replacement")
CLS = ("local_basis_amplitude", "phase_parameterized", "entangling_controlled")
STRATA = [(o, c) for o in OPS for c in CLS]
QUTEST = str(Path(ROOT) / ".venv-qutest-audit" / "bin" / "qutest")


def largest_remainder(avail: dict, total: int) -> dict:
    """Frozen allocation: proportional to availability, remainders by largest fraction then stratum order."""
    live = {k: v for k, v in avail.items() if v > 0}
    if not live:
        return {k: 0 for k in avail}
    S = sum(live.values())
    exact = {k: total * v / S for k, v in live.items()}
    base = {k: min(int(exact[k]), live[k]) for k in live}
    alloc = dict(base)
    while sum(alloc.values()) < total:
        cand = [k for k in live if alloc[k] < live[k]]
        if not cand:
            break
        cand.sort(key=lambda k: (-(exact[k] - base[k]), STRATA.index(k)))
        alloc[cand[0]] += 1
    return {k: alloc.get(k, 0) for k in avail}


def preflight(gates, n):
    """INGESTION-ONLY. (a) qutest lint on an assertion-free test; (b) assertion-free execution.
    Returns (class, detail). Never computes or inspects a kill/survive verdict."""
    text = QA.make_test(gates, n, [])                       # no //% expect pragmas at all
    with tempfile.NamedTemporaryFile("w", suffix=".qasm", delete=False) as f:
        f.write(text); p = f.name
    try:
        lint = subprocess.run([QUTEST, "lint", p], capture_output=True, text=True, timeout=120)
        if "error" in (lint.stdout + lint.stderr).lower() and lint.returncode != 0:
            return "UNSUPPORTED_LINT", (lint.stdout + lint.stderr).strip().splitlines()[-1][:120]
        run = subprocess.run([QUTEST, "run", p], capture_output=True, text=True, timeout=180)
        out = (run.stdout + run.stderr).strip()
        summ = out.splitlines()[-1] if out else ""
        if "error" in summ.lower():
            return "UNSUPPORTED_INGESTION", summ[:120]
        if "passed" in summ or "1 total" in summ:
            return "EXECUTABLE", summ[:120]
        return "UNSUPPORTED_UNKNOWN", (summ or out)[:120]
    finally:
        Path(p).unlink(missing_ok=True)


opp_rows, gen_rows, samp_rows, log_rows = [], [], [], []
for s in SUBJ:
    sid, n, gates = s["subject"], s["n"], s["base_gates"]
    pool, ineligible = MUT.complete_pool(gates, n, sid)
    # ---- 1-3. complete inventory of opportunities, keyed by the 9 frozen strata
    seen = set()
    dedup = []
    for m in pool:
        h = m["mutated_hash"]
        dup = h in seen
        opp_rows.append({"subject": sid, "operator": m["op"], "gate_class": m["gate_class"],
                         "location": m["spec"], "anchor_index": m["anchor_index"], "third": m["third"],
                         "mutated_hash": h, "definition_sha256": hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest(),
                         "exact_duplicate_of_earlier_site": dup, "statically_eligible": True})
        if not dup:
            seen.add(h); dedup.append(m)
    for m in ineligible:
        opp_rows.append({"subject": sid, "operator": m["op"], "gate_class": m["gate_class"],
                         "location": m["spec"], "anchor_index": m["anchor_index"], "third": m["third"],
                         "mutated_hash": m["mutated_hash"],
                         "definition_sha256": hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest(),
                         "exact_duplicate_of_earlier_site": False, "statically_eligible": False})
    # ---- 4. frozen deterministic draw
    by = {k: [] for k in STRATA}
    for m in dedup:
        k = (m["op"], m["gate_class"])
        if k in by:
            by[k].append(m)
    for k in by:                                   # frozen order: (location, sha256(definition)) ascending
        by[k].sort(key=lambda m: (m["spec"], hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest()))
    avail = {k: len(by[k]) for k in STRATA}
    alloc = largest_remainder(avail, PER_SUBJECT)
    picked, short = [], {}
    for k in STRATA:
        take = by[k][:alloc[k]]
        picked += [(k, m) for m in take]
        if len(take) < alloc[k]:
            short[k] = alloc[k] - len(take)
    # redistribute any shortfall by the same rule over strata with remaining capacity
    redis = {}
    deficit = PER_SUBJECT - len(picked)
    if deficit > 0:
        rem = {k: max(0, avail[k] - alloc[k]) for k in STRATA}
        extra = largest_remainder(rem, deficit)
        for k in STRATA:
            if extra[k]:
                add = by[k][alloc[k]:alloc[k] + extra[k]]
                picked += [(k, m) for m in add]
                redis[k] = len(add)
    for k in STRATA:
        log_rows.append({"subject": sid, "operator": k[0], "gate_class": k[1],
                         "sites_available_deduped": avail[k], "allocation": alloc[k],
                         "drawn": sum(1 for kk, _ in picked if kk == k),
                         "shortfall": short.get(k, 0), "redistribution_received": redis.get(k, 0)})
    for j, (k, m) in enumerate(picked):
        mid = f"{sid}#h{j:02d}"
        row = {"mutant_id": mid, "subject": sid, "family": s["family"], "n": n,
               "contract_id": s["contract_id"], "operator": m["op"], "gate_class": m["gate_class"],
               "location": m["spec"], "anchor_index": m["anchor_index"], "third": m["third"],
               "mutated_hash": m["mutated_hash"],
               "definition_sha256": hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest(),
               "gate_count_delta": len(m["mutated_gates"]) - len(gates),
               "mutated_gates": json.dumps(m["mutated_gates"])}
        gen_rows.append(row); samp_rows.append(row)
    print(f"{sid:20s} pool={len(pool):5d} eligible_dedup={len(dedup):5d} drawn={len(picked)}")

# ---- 10-11. ingestion-only preflight
pre_rows, exc_rows = [], []
for r in samp_rows:
    cls, detail = preflight(json.loads(r["mutated_gates"]), r["n"])
    pre_rows.append({"mutant_id": r["mutant_id"], "subject": r["subject"],
                     "preflight_class": cls, "preflight_detail": detail,
                     "assertions_in_preflight": 0,
                     "eligibility": "ELIGIBLE_NATIVE" if cls == "EXECUTABLE" else "EXCLUDED_NATIVE_INVALID",
                     "kill_survive_inspected": False})
    if cls != "EXECUTABLE":
        exc_rows.append({"mutant_id": r["mutant_id"], "subject": r["subject"], "operator": r["operator"],
                         "gate_class": r["gate_class"], "location": r["location"],
                         "exclusion_class": cls, "exclusion_reason": detail,
                         "obligation_failed": "OB01_native_eligibility",
                         "removed_from_attribution_denominator": True})
elig = {p["mutant_id"] for p in pre_rows if p["eligibility"] == "ELIGIBLE_NATIVE"}
print(f"\npreflight: {len(pre_rows)} sampled | ELIGIBLE_NATIVE {len(elig)} | EXCLUDED_NATIVE_INVALID {len(exc_rows)}")

# ---- 9. structural signatures only; semantic signature INPUTS recorded, classes deferred to S3
sig_rows = []
for r in samp_rows:
    s = next(x for x in SUBJ if x["subject"] == r["subject"])
    sig_rows.append({"mutant_id": r["mutant_id"], "subject": r["subject"], "n": r["n"],
        "eligibility": "ELIGIBLE_NATIVE" if r["mutant_id"] in elig else "EXCLUDED_NATIVE_INVALID",
        "structural_signature_syntactic": r["mutated_hash"],
        "structural_signature_definition": r["definition_sha256"],
        "structural_gate_count_delta": r["gate_count_delta"],
        "structural_stratum": f"{r['operator']}/{r['gate_class']}", "structural_third": r["third"],
        "original_program_hash": s["program_hash"], "output_register_qubits": json.dumps(s["output_register_qubits"]),
        "contract_id": r["contract_id"],
        "semantic_signature_state_class": "DEFERRED_TO_S3",
        "semantic_signature_observation_class": "DEFERRED_TO_S3",
        "deferral_reason": "endpoint-state and observation classes are S3 semantic evidence; computing them in S2 would expose the partition shape before the cohort boundary"})

# ---- cross-tool case map
xt_rows = []
for r in samp_rows:
    if r["mutant_id"] not in elig:
        continue
    xt_rows.append({"mutant_id": r["mutant_id"], "subject": r["subject"], "contract_id": r["contract_id"],
        "qutest_profiles": "QT_0_1_0__COUNT_SUBSTRATE;QT_0_1_0__STATE_SUBSTRATE;QT_0_1_0__STRUCTURAL_ROLE_AUDIT;QT_0_1_0__EXPANDED_STATE_SENSITIVITY",
        "qucheck_profiles": "QC_0_0_2__FROZEN_XYZ;QC_0_0_2__DIFFERENTIAL_MARGINAL",
        "shared_claim_classes": "CL3_PROFILE_INVISIBLE;CL4_REALIZED_SUITE_OMISSION;CL5_CONFIGURATION_RELATIVE;CL6_ABSTAIN",
        "qutest_only_claim_classes": "CL1_CONTRACT_EQUIVALENT;CL2_STATE_EQUIVALENT_UNDER_REALIZED_INPUT",
        "qutest_only_reason": "both need an exact endpoint-state or contract relation that a count-only substrate cannot decide",
        "cross_tool_shared_case": True})

def wcsv(fn, rows):
    with open(os.path.join(HERE, fn), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
wcsv("S2_MUTATION_OPPORTUNITIES.csv", opp_rows)
wcsv("S2_GENERATED_MUTANTS.csv", gen_rows)
wcsv("S2_SAMPLED_MUTANTS.csv", samp_rows)
wcsv("S2_NATIVE_PREFLIGHT.csv", pre_rows)
wcsv("S2_ELIGIBILITY_EXCLUSIONS.csv", exc_rows if exc_rows else [{"mutant_id": "", "subject": "", "operator": "",
     "gate_class": "", "location": "", "exclusion_class": "NONE", "exclusion_reason": "no sampled mutant failed the ingestion-only preflight",
     "obligation_failed": "", "removed_from_attribution_denominator": False}])
wcsv("S2_EFFECT_SIGNATURE_INPUTS.csv", sig_rows)
wcsv("S2_CROSS_TOOL_CASE_MAP.csv", xt_rows)
json.dump({"log": log_rows}, open(os.path.join(HERE, "_s2_sampling_log.json"), "w"), indent=1)
print("dup mutated_hash within a subject (should be 0):",
      sum(1 for sid in {r['subject'] for r in samp_rows}
          for h, c in Counter(r["mutated_hash"] for r in samp_rows if r["subject"] == sid).items() if c > 1))
