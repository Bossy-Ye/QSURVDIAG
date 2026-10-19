"""Pass 56E: run-to-run variability of QUTest 0.1.0's structural path (runner.run_test transpiles without a seed).
For each of the 85 contract-equivalent pairs, T independent trials; each trial transpiles the original and the mutant
afresh through QUTest's own parser/transpile path and evaluates 'expect gateset subset_of [original's names]'.
Also records (a) distinct transpiled gate sets per original program and (b) whether an original fails a gate-set
assertion whose allowed set came from another transpilation of itself. Deterministic code, no simulation.
Writes only to paper-artifact/audit_pass56E/outputs/."""
import csv, json, sys, collections
Q = "/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot"; OUT = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/audit_pass56E/outputs"
sys.path.insert(0, f"{Q}/cross_tool_stage/qutest")
from qutest_adapter import make_test
from qutest.parser.qasm_parser import parse_test_source
from qutest.backends import resolve_backend
from qiskit import qasm3, transpile
T = 40
rd = lambda p: list(csv.DictReader(open(p)))
def tnames(gates, n):
    tc = parse_test_source(make_test(gates, n, []))[0]
    t = transpile(qasm3.loads(tc.qasm_source), backend=resolve_backend("ideal", 42))
    return frozenset({i.operation.name for i in t.data} - {"measure", "barrier"})
pairs = []
led = [r for r in rd(f"{Q}/paper_freeze/CANONICAL_RESULT_LEDGER.csv") if r["final_semantic_status"] == "EQUIVALENT"]
MP = {r["mutant_id"]: r for r in rd(f"{Q}/final_empirical_study/MUTANT_POPULATION.csv")}
PM = {r["program"]: r for r in rd(f"{Q}/final_empirical_study/PROGRAM_MANIFEST.csv")}
for r in led:
    m = MP[r["mutant_id"]]; p = PM[m["program"]]
    pairs.append(("construction", r["mutant_id"], m["program"], json.loads(p["base_gates"]), json.loads(m["mutated_gates"]), int(p["n"])))
S1 = {s["subject"]: s for s in json.load(open(f"{Q}/research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json"))}
S2 = {r["mutant_id"]: r for r in rd(f"{Q}/research_repair/phase5_validation/s2_cohort/S2_SAMPLED_MUTANTS.csv")}
for a in rd(f"{Q}/research_repair/phase5_validation/s3_certification/S3_QUTEST_ADMISSIBILITY.csv"):
    if a["contract_equivalent"] != "True": continue
    s = S1[S2[a["mutant_id"]]["subject"]]; bg = s["base_gates"]; bg = json.loads(bg) if isinstance(bg, str) else bg
    pairs.append(("prospective", a["mutant_id"], s["subject"], bg, json.loads(S2[a["mutant_id"]]["mutated_gates"]), int(S2[a["mutant_id"]]["n"])))
rows = []; orig_sets = collections.defaultdict(set); self_fail = collections.Counter(); self_trials = collections.Counter()
for pop, mid, prog, base, mut, n in pairs:
    k = 0
    for _ in range(T):
        ob, om = tnames(base, n), tnames(mut, n); orig_sets[(pop, prog)].add(ob)
        k += not (om <= ob)
        ob2 = tnames(base, n); self_trials[(pop, prog)] += 1; self_fail[(pop, prog)] += not (ob2 <= ob)
    rows.append({"population": pop, "mutant_id": mid, "program": prog, "separated_trials": k, "trials": T})
with open(f"{OUT}/QUTEST_GATESET_VARIABILITY_T40.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
S = {}
for pop in ("construction", "prospective"):
    P = [r for r in rows if r["population"] == pop]
    S[pop] = {"pairs": len(P), "always_separated": sum(r["separated_trials"] == T for r in P),
              "never_separated": sum(r["separated_trials"] == 0 for r in P),
              "sometimes_separated": sum(0 < r["separated_trials"] < T for r in P),
              "mean_separated_per_trial": round(sum(r["separated_trials"] for r in P) / T, 2),
              "originals": len({r["program"] for r in P}),
              "originals_with_varying_gate_set": sum(1 for (p, g), v in orig_sets.items() if p == pop and len(v) > 1),
              "originals_failing_own_assertion_some_trial": sum(1 for (p, g), v in self_fail.items() if p == pop and v > 0)}
json.dump(S, open(f"{OUT}/QUTEST_GATESET_VARIABILITY_T40_SUMMARY.json", "w"), indent=1); print(json.dumps(S, indent=1))
