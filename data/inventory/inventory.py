"""Inventory of the evidence, per population.

Usage:
  python3 -I inventory.py <package_root> <qmutbench_download_dir> <corpus_files.tsv> <out_dir>

Reads only records of the package (never writes there; final records with the v3 amendment applied,
scripts/lib/witness_order.py) and the pinned QMutBench program
files fetched by fetch_corpus.sh (verified here against the SHA-256 values in the package's corpus
case manifests).  Writes:
  <out_dir>/cases_all.csv           one row per (population, case): site, operator, class, outcome, witness, margin
  <out_dir>/summary.json            every count printed below
  <out_dir>/inventory_tables.txt    the printed tables (stdout copy)

Position rule (the study's own frozen rule, representation.position_third):
  G = number of gates of the ORIGINAL mutable body (QMutBench: gate statements, excluding
      declarations, barrier and measure);
  anchor = index of the replaced/deleted gate, or, for an insertion, the gap index = number of
      original gates preceding the inserted gate (0 = before the first gate, G = after the last);
  rel = anchor / G; early if rel < 1/3, middle if rel < 2/3, late otherwise;
  first gate = anchor == 0 (insertion before gate 0, or replacement/deletion of gate 0).
Sources of the anchor: location strings 'ins@k', 'rep@k', 'del@k' (20 circuits, external, MQT Bench);
QMutBench pairs: the single line the mutant file inserts, deletes or replaces relative to the original file
(line diff of the hash-verified files); the index in the QMutBench file name is not a gate or line index
of the file and is not used.  Ambiguous runs (inserted/deleted gate equal to its neighbour) are flagged.
"""
import csv
import collections
import hashlib
import json
import os
import re
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import witness_order  # noqa: E402

THETA = 0.05
C = collections.Counter
LBA = {"x", "y", "h", "sx", "sxdg", "rx", "ry"}
PHASE = {"z", "s", "sdg", "t", "tdg", "p", "rz", "u1"}
GENERAL1 = {"u", "u2", "u3"}
REPORT_NAME = {"CL1": "contract equivalence", "CL2": "executed-input equality", "CL3": "observation limitation",
               "CL4": "suite omission", "CL5": "below-tolerance difference", "Unresolved": "Unresolved",
               "NA_KILLED": "killed"}
OUT_LINES = []


def out(*a):
    s = " ".join(str(x) for x in a)
    OUT_LINES.append(s)
    print(s)


def rd(path):
    with open(path, newline="") as f:
        return witness_order.final(path, list(csv.DictReader(f)))


def third(anchor, G):
    if G <= 0:
        return "early"
    r = anchor / G
    return "early" if r < 1 / 3 else ("middle" if r < 2 / 3 else "late")


def gclass(name, arity=None):
    name = name.lower()
    if name == "id":
        return "identity"
    if name in LBA:
        return "local_basis_amplitude"
    if name in PHASE:
        return "phase_parameterized"
    if name in GENERAL1:
        return "general_1q"
    return "entangling_controlled"


def gclass_q(name):
    if name.startswith("block:"):
        return "multi-gate block"
    return gclass(name)


OPN = {"gate_insertion": "insert", "gate_replacement": "replace", "gate_deletion": "delete",
       "ins": "insert", "rep": "replace", "del": "delete", "Add": "insert", "Replace": "replace", "Remove": "delete"}


def parse_loc(loc):
    m = re.match(r"(ins|del|rep)@(\d+):(.*)$", loc)
    op, k, rest = m.group(1), int(m.group(2)), m.group(3)
    if op == "ins":
        gate = rest.split("[")[0]
    elif op == "rep":
        gate = rest.split("->")[1]
    else:
        gate = rest
    return OPN[op], k, gate


# ----------------------------------------------------------------------------------- QMutBench
DIAG = {"z", "s", "sdg", "t", "tdg", "rz", "p", "u1", "cp", "cu1", "cz", "rzz", "id"}
NONGATE = ("OPENQASM", "include", "qreg", "creg", "barrier", "measure")


def qasm_lines(text):
    return [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]


def is_gate(ln):
    return not ln.split("(")[0].split()[0] in NONGATE


def gname(ln):
    return ln.split("(")[0].split()[0]


def qmb_site(orig_text, mut_text, mut_file):
    """Site of one QMutBench pair from the file contents.

    The index in the QMutBench file name is not a gate or line index of the exported file (checked:
    it does not match), so the site is read from a diff of the gate statements (declarations, barrier
    and measure excluded) of original and mutant:
      p     = length of the common prefix of the two gate lists  -> first changed original gate index;
      insert: one added gate; its gap index lies in [Gm - smax - 1, p] (a range only when the inserted
              gate repeats its neighbour); anchor = lower end, anchor_max = upper end;
      replace: one changed gate at index p ('ReplaceGate_<g>' names the REPLACED gate <g>);
      delete: RemoveGate_k may remove a block of several exported gates (a high-level gate exported as
              several basis gates); anchor = first removed gate, anchor_max = last changed gate,
              n_removed = Go - Gm.
    """
    o, m = qasm_lines(orig_text), qasm_lines(mut_text)
    og = [ln for ln in o if is_gate(ln)]
    mg = [ln for ln in m if is_gate(ln)]
    Go, Gm = len(og), len(mg)
    nongate_same = [ln for ln in o if not is_gate(ln)] == [ln for ln in m if not is_gate(ln)]
    mo = re.match(r"AddGate_([A-Za-z0-9]+)_inGap_(\d+)_\.qasm$", mut_file)
    mr = re.match(r"ReplaceGate_([A-Za-z0-9]+)_inPositionOfGate_(\d+)\.qasm$", mut_file)
    md = re.match(r"RemoveGate_(\d+)_\.qasm$", mut_file)
    p = 0
    while p < min(Go, Gm) and og[p] == mg[p]:
        p += 1
    smax = 0
    while smax < min(Go, Gm) and og[Go - 1 - smax] == mg[Gm - 1 - smax]:
        smax += 1
    sc = min(smax, min(Go, Gm) - p)
    check, n_removed, old_gate = "ok", 0, ""
    if mo:
        op, gate, k = "insert", mo.group(1), int(mo.group(2))
        anchor, anchor_max = max(0, Gm - smax - 1), p
        if not (Gm == Go + 1 and anchor <= anchor_max and gname(mg[p]) == gate):
            check = "MISMATCH"
    elif mr:
        op, k = "replace", int(mr.group(2))
        anchor = anchor_max = p
        if p < Go and p < Gm:
            gate, old_gate = gname(mg[p]), gname(og[p])
        else:
            gate = "?"
        # the gate named in the file name is sometimes the replaced and sometimes the new gate of the
        # exported file, so it is not checked; the exported gate lists must differ in exactly one gate
        if not (Gm == Go and Go - sc - p == 1):
            check = "MISMATCH"
    elif md:
        op, k = "delete", int(md.group(1))
        n_removed = Go - Gm
        # mutant gate list must be a subsequence of the original gate list
        it = iter(og)
        subseq = all(any(g == x for x in it) for g in mg)
        if n_removed == 1:
            anchor, anchor_max = max(0, Go - smax - 1), p
            gate = gname(og[p])
        else:
            # removed positions: greedy left-to-right alignment of the subsequence
            removed, j = [], 0
            for i, g in enumerate(og):
                if j < Gm and mg[j] == g:
                    j += 1
                else:
                    removed.append(i)
            anchor, anchor_max = (removed[0], removed[-1]) if removed else (p, p)
            gate = "block:" + "+".join(sorted({gname(og[i]) for i in removed}))
        if n_removed < 1 or not subseq:
            check = "MISMATCH"
    else:
        raise ValueError(mut_file)
    if not nongate_same:
        check = "MISMATCH_nongate"
    # the study's sufficient condition for observation limitation (T3_1_ENTAILED_VS_CONTINGENT.json):
    # every gate from the first divergence index onward is diagonal in BOTH lists
    entailed = all(gname(x) in DIAG for x in og[p:]) and all(gname(x) in DIAG for x in mg[p:])
    # stratification variable of T2A_ELIGIBILITY.csv: the difference touches a diagonal operator
    if op == "insert":
        touched = [gname(mg[p])]
    elif op == "replace":
        touched = [gname(og[p]), gname(mg[p])] if p < Go else []
    else:
        touched = [g for g in re.split(r"[:+]", gate) if g and g != "block"]
    touches_diag = any(g in DIAG for g in touched)
    if check == "ok" and anchor != anchor_max:
        check = "ok_range" if op != "delete" or n_removed == 1 else "ok_block"
    return {"op": op, "gate": gate, "old_gate": old_gate, "anchor": anchor, "anchor_max": anchor_max, "G": Go,
            "check": check, "qmb_index": k, "n_removed": n_removed, "entailed": entailed,
            "touches_diag": touches_diag, "terminal": anchor_max >= Go - (0 if op == "insert" else 1)}


# ----------------------------------------------------------------------------------- loaders
def final_index(path, key):
    return {r[key]: r for r in rd(path)}


def native_index(root):
    idx = {}
    for r in rd(os.path.join(root, "data/certification/outcomes/R2V_NATIVE.csv")):
        idx[(r["arm"], r["case"], r["purpose"])] = r
    return idx


def base_row(pop, sub, case, program, family, n, op, gate, gcls, anchor, G, contract, exe_input, fin):
    row = {
        "population": pop, "subpopulation": sub, "case": case, "program": program, "family": family, "n": n,
        "operator": op, "mutation_gate": gate, "gate_class": gcls, "anchor": anchor, "G": G,
        "rel_pos": round(anchor / G, 4) if G else "", "third": third(anchor, G), "first_gate": anchor == 0,
        "contract": contract, "executed_input": exe_input,
    }
    for k in ("native_verdict", "kills", "v2_candidate", "v2_report", "unmet", "undecided_relation",
              "w_kind", "w_key", "w_d", "c_kind", "c_key", "c_d", "decisive_d", "ob13_source", "margin_obs",
              "margin_state", "margin_contract"):
        row[k] = fin.get(k, "") if fin else ""
    return row


def entailed_lists(base, mut):
    """Sufficient condition of observation limitation on gate lists: from the first divergence onward
    every gate is diagonal in both lists (same rule as T3_1_ENTAILED_VS_CONTINGENT.json)."""
    p = 0
    while p < min(len(base), len(mut)) and base[p] == mut[p]:
        p += 1
    return all(g["gate"] in DIAG for g in base[p:]) and all(g["gate"] in DIAG for g in mut[p:])


def load_primary(root):
    fd = os.path.join(root, "data/prospective/mqt_bench/frozen_deps")
    fin = final_index(os.path.join(root, "data/certification/outcomes/R2V_FINAL_PRIMARY.csv"), "mutant_id")
    pm = {r["program"]: r for r in rd(os.path.join(fd, "PROGRAM_MANIFEST.csv"))}
    rows, checks = [], C()
    for r in rd(os.path.join(fd, "MUTANT_POPULATION.csv")):
        base = json.loads(pm[r["program"]]["base_gates"])
        G = len(base)
        checks["dev_G_matches_manifest"] += int(G == int(pm[r["program"]]["gate_count"]))
        op, k, gate = parse_loc(r["location"])
        mut = json.loads(r["mutated_gates"])
        if op == "delete":
            ok = mut == base[:k] + base[k + 1:]
        elif op == "insert":
            ok = mut[:k] + mut[k + 1:] == base and mut[k]["gate"] == gate
        else:
            ok = len(mut) == G and all(mut[i] == base[i] for i in range(G) if i != k) and mut[k]["gate"] == gate
        checks["dev_location_reconstructs"] += int(ok)
        checks["dev_rxx_rzz"] += int(any(g["gate"] in ("rxx", "rzz") for g in mut))
        f = fin.get(r["mutant_id"])
        if f is None:
            checks["dev_missing_final"] += 1
            continue
        contract = f["contract"]
        row = base_row("20 circuits", "development", r["mutant_id"], r["program"], r["family"], int(r["n"]),
                       op, gate, r["gate_class"], k, G, contract, "|0...0>", f)
        row["entailed_diag"] = entailed_lists(base, mut)
        row["terminal"] = k >= G - (0 if op == "insert" else 1)
        rows.append(row)
    subj = {s["subject"]: s for s in json.load(open(os.path.join(fd, "S1_SUBJECTS.json")))}
    for r in rd(os.path.join(fd, "S2_GENERATED_MUTANTS.csv")):
        f = fin.get(r["mutant_id"])
        G = len(subj[r["subject"]]["base_gates"])
        op, k, gate = parse_loc(r["location"])
        checks["add_anchor_matches"] += int(k == int(r["anchor_index"]))
        checks["add_third_matches"] += int(third(k, G) == {"first": "early", "middle": "middle", "last": "late"}[r["third"]])
        if f is None:
            checks["add_not_in_final(excluded)"] += 1
            checks["add_excluded_ids:" + r["mutant_id"]] += 1
            continue
        row = base_row("20 circuits", "additional", r["mutant_id"], r["subject"], r["family"], int(r["n"]),
                       op, gate, r["gate_class"], k, G, f["contract"], "|0...0>", f)
        row["entailed_diag"] = entailed_lists(subj[r["subject"]]["base_gates"], json.loads(r["mutated_gates"]))
        row["terminal"] = k >= G - (0 if op == "insert" else 1)
        rows.append(row)
    checks["final_rows"] = len(fin)
    return rows, checks


def load_external(root):
    fin = final_index(os.path.join(root, "data/certification/outcomes/R2V_FINAL_EXTERNAL.csv"), "case")
    freeze = json.load(open(os.path.join(root, "data/external/protocol/EXTERNAL_COHORT_FREEZE_v3.json")))
    inputs = {r["subject"]: r["prepared_state"] for r in freeze["realized_inputs"]}
    alloc = rd(os.path.join(root, "data/external/cohort/EXTERNAL_ALLOCATION.csv"))
    # original gate count = mutant gate count corrected by the operator
    gco = collections.defaultdict(set)
    for r in alloc:
        d = {"gate_insertion": -1, "gate_deletion": 1, "gate_replacement": 0}[r["operator"]]
        gco[r["subject"]].add(int(r["gate_count"]) + d)
    rows, checks = [], C()
    checks["external_subjects_with_consistent_G"] = sum(len(v) == 1 for v in gco.values())
    for r in alloc:
        G = min(gco[r["subject"]])
        op, k, gate = parse_loc(r["location"])
        checks["anchor_matches"] += int(k == int(r["anchor_index"]))
        checks["third_matches"] += int(third(k, G) == {"first": "early", "middle": "middle", "last": "late"}[r["third"]])
        f = fin[r["mutant_id"]]
        exe = inputs.get(r["subject"], "fixed input (original state preparation)")
        rows.append(base_row("external", r["group"], r["mutant_id"], r["subject"], r["subject"], int(r["n_qubits"]),
                             op, gate, r["gate_class"], k, G, f["contract"], exe, f))
    return rows, checks


def load_mqt(root):
    d = os.path.join(root, "data/prospective/mqt_bench")
    man = rd(os.path.join(d, "population/MUTANT_MANIFEST.csv"))
    subj = {r["subject"]: r for r in rd(os.path.join(d, "subjects/SUBJECT_MANIFEST.csv"))}
    c3 = final_index(os.path.join(d, "records/stage_c/C3_REPORTS.csv"), "case")
    cases = final_index(os.path.join(d, "records/analysis/PASS3C_CASES.csv"), "mutant_id")
    rows, checks = [], C()
    for r in man:
        G = int(subj[r["subject"]]["body_gates"])
        op, k, gate = parse_loc(r["location"])
        checks["anchor_matches"] += int(k == int(r["anchor_index"]))
        checks["third_matches"] += int(third(k, G) == {"first": "early", "middle": "middle", "last": "late"}[r["third"]])
        f = dict(c3[r["mutant_id"]])
        pc = cases[r["mutant_id"]]
        checks["report_agrees_pass3c"] += int(pc["v2_report"] == f["v2_report"])
        exe = subj[r["subject"]]["declared_input"]
        row = base_row("MQT Bench", r["family"], r["mutant_id"], r["subject"], r["family"], int(r["n"]),
                       op, gate, r["gate_class"], k, G, f["contract"], exe, f)
        for k2 in ("ob13_kills_of_12", "ob13_guard_fails_of_3", "ob15_kills_of_12", "d1_mutant_kills_of_12",
                   "d1_original_false_failures_of_12", "d1_outcome", "d2_operative_rung", "d2_outcome",
                   "d2_paired_agreement_of_12", "d2_independent_mutant_kills_of_12", "bound_b13", "bound_guard"):
            row[k2] = pc.get(k2, "")
        rows.append(row)
    return rows, checks


def load_qmb_sites(root, dl, tsv):
    sites, checks = {}, C()
    for r in csv.DictReader(open(tsv, newline=""), delimiter="\t"):
        po = os.path.join(dl, r["orig_sha256"] + ".qasm")
        pmu = os.path.join(dl, r["mut_sha256"] + ".qasm")
        ob, mb = open(po, "rb").read(), open(pmu, "rb").read()
        if hashlib.sha256(ob).hexdigest() != r["orig_sha256"] or hashlib.sha256(mb).hexdigest() != r["mut_sha256"]:
            raise SystemExit("hash mismatch for " + r["case_key"])
        checks["orig_hash_ok"] += int(hashlib.sha256(ob).hexdigest() == r["orig_sha256"])
        checks["mut_hash_ok"] += int(hashlib.sha256(mb).hexdigest() == r["mut_sha256"])
        s = qmb_site(ob.decode(), mb.decode(), r["mutant_file"])
        checks["site_check_" + s["check"]] += 1
        s.update({"original_id": r["original_id"], "family": r["family"], "mutant_file": r["mutant_file"],
                  "case_set": r["case_set"]})
        sites[r["case_key"]] = s
        sites.setdefault("_by_short", {})
    by_short = {}
    for ck, s in sites.items():
        if ck == "_by_short":
            continue
        by_short.setdefault(ck.split("/")[1], []).append(ck)
    sites.pop("_by_short")
    return sites, by_short, checks


def load_corpus(root, sites):
    fin = rd(os.path.join(root, "data/certification/outcomes/R2V_FINAL_CORPUS.csv"))
    elig = {(r["case_set"], r["pair_id"]): r for r in rd(os.path.join(root, "data/scalability/corpus/T2A_ELIGIBILITY.csv"))}
    rows = []
    for f in fin:
        s = sites[f["case_key"]]
        cs, cid = f["case"].split("/")
        row = base_row("corpus", cs, f["case_key"], s["original_id"], s["family"], int(f["n"]), s["op"], s["gate"],
                       gclass_q(s["gate"]), s["anchor"], s["G"], f["contract"], "|0...0>", f)
        row["diagonal_stratum"] = elig.get((cs, cid), {}).get("diagonal_stratum", "")
        row["anchor_max"] = s["anchor_max"]
        row["third_max"] = third(s["anchor_max"], s["G"])
        row["site_check"] = s["check"]
        row["qmb_index"] = s["qmb_index"]
        row["n_removed"] = s["n_removed"]
        row["replaced_gate"] = s["old_gate"]
        row["entailed_diag"] = s["entailed"]
        row["touches_diag_recomputed"] = s["touches_diag"]
        row["terminal"] = s["terminal"]
        row["mutant_file"] = s["mutant_file"]
        rows.append(row)
    return rows


def load_width(root, sites, by_short):
    e4 = rd(os.path.join(root, "data/scalability/E4_SCALE_MANIFEST.csv"))
    fin = final_index(os.path.join(root, "data/certification/outcomes/R2V_FINAL_WIDTH.csv"), "case")
    rows, checks = [], C()
    for r in e4:
        cks = by_short.get(r["pair_id"], [])
        checks["corpus_keys_found_%d" % len(cks)] += 1
        s = sites[cks[0]]
        prov = r["provenance"]
        if "/" in prov:
            checks["path_matches_corpus_manifest"] += int(prov.split()[-1] == s["original_id"] + "/" + s["mutant_file"])
        f = fin.get(r["pair_id"])
        row = base_row("width set", "executed" if f else "not executed (" + r["ineligibility_reason"] + ")",
                       r["pair_id"], s["original_id"], s["family"], int(r["n"]), s["op"], s["gate"], gclass_q(s["gate"]),
                       s["anchor"], s["G"], r["contract"], "|0...0>", f or {})
        row["declared_outputs"] = r["declared_outputs"]
        row["anchor_max"] = s["anchor_max"]
        row["third_max"] = third(s["anchor_max"], s["G"])
        row["site_check"] = s["check"]
        row["corpus_case_key"] = cks[0]
        rows.append(row)
    return rows, checks


# ----------------------------------------------------------------------------------- analyses
def assertion_type(kind, key, n=None):
    if not kind:
        return ""
    if kind == "zmask":
        m = int(key)
        bits = [i for i in range(64) if m >> i & 1]
        if len(bits) == 2:
            return "Z-product w2 adjacent" if bits[1] - bits[0] == 1 else "Z-product w2 non-adjacent"
        return "Z-product w%d" % len(bits)
    return kind


def status(row):
    nv, rep, cand = row["native_verdict"], row["v2_report"], row["v2_candidate"]
    if not nv:
        return "not executed"
    if nv == "KILLED":
        return "killed"
    if nv == "SPLIT":
        return "split verdict"
    return "stable survivor"


def table(title, rows, keyf, cols, colf):
    out("")
    out("### " + title)
    cnt = collections.defaultdict(C)
    for r in rows:
        cnt[keyf(r)][colf(r)] += 1
    keys = sorted(cnt, key=lambda k: (str(k)))
    out("| " + " | ".join(["group"] + cols + ["total"]) + " |")
    out("|" + "---|" * (len(cols) + 2))
    tot = C()
    for k in keys:
        out("| " + " | ".join([str(k)] + [str(cnt[k][c]) for c in cols] + [str(sum(cnt[k].values()))]) + " |")
        tot.update(cnt[k])
    out("| " + " | ".join(["**all**"] + [str(tot[c]) for c in cols] + [str(sum(tot.values()))]) + " |")
    return {str(k): dict(v) for k, v in cnt.items()}


def pop_summary(name, rows, summary):
    S = {}
    ex = [r for r in rows if r["native_verdict"]]
    S["pairs"] = len(rows)
    S["executed"] = len(ex)
    S["programs"] = len({r["program"] for r in rows})
    S["families"] = len({r["family"] for r in rows})
    S["families_list"] = dict(C(r["family"] for r in rows))
    S["sites_program_anchor"] = len({(r["program"], r["anchor"]) for r in rows})
    S["sites_program_kind_anchor"] = len({(r["program"], r["operator"] == "insert", r["anchor"]) for r in rows})
    S["operator"] = dict(C(r["operator"] for r in rows))
    S["gate_class"] = dict(C(r["gate_class"] for r in rows))
    S["third"] = dict(C(r["third"] for r in rows))
    S["first_gate"] = sum(r["first_gate"] for r in rows)
    S["contract"] = dict(C(r["contract"] for r in rows))
    S["executed_inputs"] = dict(C(r["executed_input"] for r in rows))
    S["status"] = dict(C(status(r) for r in rows))
    S["survive_ge1_run"] = sum(1 for r in ex if r["native_verdict"] in ("SURVIVED", "SPLIT"))
    S["candidate"] = dict(C(r["v2_candidate"] or "-" for r in ex if r["native_verdict"] != "KILLED"))
    S["report"] = dict(C(r["v2_report"] for r in ex))
    S["reported_outcomes"] = sum(1 for r in ex if r["v2_report"].startswith("CL"))
    S["unresolved_reasons"] = dict(C(unres_reason(r) for r in ex if r["v2_report"] == "Unresolved"))
    summary[name] = S
    out("")
    out("## Population: %s" % name)
    out("pairs %d, executed %d, distinct original programs %d, families %d, distinct sites (program, gate index) %d"
        % (S["pairs"], S["executed"], S["programs"], S["families"], S["sites_program_anchor"]))
    out("operators", S["operator"], "| gate classes", S["gate_class"])
    out("position thirds", S["third"], "| at first gate", S["first_gate"])
    out("contracts", S["contract"])
    out("executed inputs", S["executed_inputs"])
    out("status", S["status"], "| survive >=1 run", S["survive_ge1_run"], "| reported outcomes", S["reported_outcomes"])
    out("candidates (non-killed)", S["candidate"])
    out("reports", S["report"])
    out("Unresolved by reason", S["unresolved_reasons"])
    return S


def unres_reason(r):
    if r["native_verdict"] == "SPLIT":
        return "split verdict" + (" (CL4 candidate)" if r["v2_candidate"] == "CL4" else " (predicted kill)")
    if r["undecided_relation"]:
        return "undecided margin " + r["undecided_relation"]
    if r["v2_candidate"] == "CL4":
        return "CL4 candidate, unmet " + r["unmet"]
    return "other " + r["unmet"]


def pos_label(r):
    if r["first_gate"]:
        return "first gate"
    return r["third"] + " (not first)"


POSCOLS = ["first gate", "early (not first)", "middle (not first)", "late (not first)"]


def outcome_label(r):
    if not r["native_verdict"]:
        return "not executed"
    if r["native_verdict"] == "KILLED":
        return "killed"
    if r["v2_report"] == "Unresolved":
        return "Unresolved"
    return REPORT_NAME[r["v2_report"]]


OUTCOLS = ["killed", "contract equivalence", "executed-input equality", "observation limitation",
           "below-tolerance difference", "suite omission", "Unresolved"]


def designs(rows, with_register=False):
    """Distinct repaired suites: (original program, [declared register], added assertion)."""
    keys = set()
    for r in rows:
        k = (r["program"], r.get("declared_outputs", "") if with_register else "", r["w_kind"], r["w_key"])
        keys.add(k)
    return keys


def margin_bins(vals):
    b = C()
    for v in vals:
        m = round(v - THETA, 9)
        if m <= 0:
            b["<=0"] += 1
        elif m < 0.01:
            b["(0,0.01)"] += 1
        elif m < 0.05:
            b["[0.01,0.05)"] += 1
        elif m < 0.1:
            b["[0.05,0.10)"] += 1
        elif m < 0.45:
            b["[0.10,0.45)"] += 1
        else:
            b[">=0.45"] += 1
    return b


MBINS = ["<=0", "(0,0.01)", "[0.01,0.05)", "[0.05,0.10)", "[0.10,0.45)", ">=0.45"]


def main(root, dl, tsv, od):
    os.makedirs(od, exist_ok=True)
    summary = {"theta": THETA}
    prim, ck1 = load_primary(root)
    ext, ck2 = load_external(root)
    mqt, ck3 = load_mqt(root)
    sites, by_short, ck4 = load_qmb_sites(root, dl, tsv)
    corp = load_corpus(root, sites)
    wid, ck5 = load_width(root, sites, by_short)
    summary["checks"] = {"primary": dict(ck1), "external": dict(ck2), "mqt": dict(ck3), "qmutbench_files": dict(ck4),
                         "width": dict(ck5)}
    out("# Inventory tables (generated by inventory.py)")
    out("")
    out("Integrity checks:", json.dumps(summary["checks"], sort_keys=True))
    nat = native_index(root)

    pops = [("20 circuits (599)", prim), ("20 circuits: development (450)", [r for r in prim if r["subpopulation"] == "development"]),
            ("20 circuits: additional (149)", [r for r in prim if r["subpopulation"] == "additional"]),
            ("external (270)", ext), ("MQT Bench (120)", mqt), ("width set (162 listed)", wid),
            ("corpus <=14 qubits (1537)", corp)]
    for name, rows in pops:
        pop_summary(name, rows, summary)

    # ---- position x outcome per population
    summary["position_x_outcome"] = {}
    for name, rows in pops:
        summary["position_x_outcome"][name] = table("Position x outcome: " + name, rows, outcome_label, POSCOLS, pos_label)

    # ---- operator / class x outcome for the causes
    summary["operator_x_outcome"] = {}
    for name, rows in pops:
        summary["operator_x_outcome"][name] = table("Operator x outcome: " + name, rows, outcome_label,
                                                    ["insert", "replace", "delete"], lambda r: r["operator"])
    summary["class_x_cause"] = {}
    for name, rows in pops:
        rr = [r for r in rows if r["v2_report"] in ("CL3", "CL4", "CL5")]
        summary["class_x_cause"][name] = table("Gate class x cause (reported CL3/CL4/CL5): " + name, rr,
                                               lambda r: REPORT_NAME[r["v2_report"]],
                                               ["local_basis_amplitude", "phase_parameterized", "entangling_controlled",
                                                "multi-gate block", "identity"], lambda r: r["gate_class"])

    # ---- family x cause
    summary["family_x_outcome"] = {}
    for name, rows in [("external (270)", ext), ("MQT Bench (120)", mqt), ("width set (162 listed)", wid),
                       ("corpus <=14 qubits (1537)", corp), ("20 circuits (599)", prim)]:
        summary["family_x_outcome"][name] = table("Family x outcome: " + name, rows, lambda r: r["family"], OUTCOLS,
                                                  outcome_label)

    # ---- causes beyond the first gate: list counts by population
    out("")
    out("### Causes at non-first-gate sites (reported outcomes)")
    beyond = {}
    for name, rows in pops:
        for cl in ("CL3", "CL4"):
            rr = [r for r in rows if r["v2_report"] == cl]
            nf = [r for r in rr if not r["first_gate"]]
            mid = [r for r in nf if r["third"] in ("middle", "late")]
            beyond[(name, cl)] = (len(rr), len(nf), len(mid))
            out("- %s %s: %d reported, %d not at first gate, %d at middle/late third; distinct non-first sites %d; programs %d"
                % (name, REPORT_NAME[cl], len(rr), len(nf), len(mid), len({(r['program'], r['anchor']) for r in nf}),
                   len({r['program'] for r in nf})))
    summary["beyond_first_gate"] = {"%s|%s" % k: v for k, v in beyond.items()}

    # ---- repair designs and assertion types
    out("")
    out("### Repair designs (distinct repaired suites) and distinguishing-assertion types")
    summary["designs"] = {}
    for name, rows, wr in [("20 circuits (599)", prim, False), ("20 circuits: development (450)", [r for r in prim if r["subpopulation"] == "development"], False),
                           ("20 circuits: additional (149)", [r for r in prim if r["subpopulation"] == "additional"], False),
                           ("external (270)", ext, False), ("MQT Bench (120)", mqt, False),
                           ("width set (162 listed)", wid, True), ("corpus <=14 qubits (1537)", corp, False)]:
        so = [r for r in rows if r["v2_report"] == "CL4"]
        cand = [r for r in rows if r["v2_candidate"] == "CL4"]
        d_so, d_c = designs(so, wr), designs(cand, wr)
        at = C(assertion_type(r["w_kind"], r["w_key"]) for r in so)
        at_d = C(assertion_type(k[2], k[3]) for k in d_so)
        per_design = C((r["program"], r.get("declared_outputs", "") if wr else "", r["w_kind"], r["w_key"]) for r in so)
        top = per_design.most_common(5)
        prog_so = len({r["program"] for r in so})
        fam_so = dict(C(r["family"] for r in so))
        summary["designs"][name] = {"SO_reported": len(so), "SO_distinct_designs": len(d_so),
                                    "SO_candidates": len(cand), "candidate_distinct_designs": len(d_c),
                                    "assertion_type_pairs": dict(at), "assertion_type_designs": dict(at_d),
                                    "SO_programs": prog_so, "SO_families": fam_so,
                                    "largest_designs": [[list(k), v] for k, v in top],
                                    "designs_with_1_pair": sum(1 for v in per_design.values() if v == 1),
                                    "SO_sites": len({(r["program"], r["anchor"]) for r in so})}
        out("- %s: %d reported SO -> %d distinct (original, added assertion) designs over %d programs, %d sites; "
            "%d candidates -> %d designs" % (name, len(so), len(d_so), prog_so,
                                             summary["designs"][name]["SO_sites"], len(cand), len(d_c)))
        out("    assertion types (pairs):", dict(at), "| (designs):", dict(sorted(at_d.items(), key=lambda kv: (-kv[1], kv[0]))))
        out("    largest designs:", top, "| designs used by one pair only:", summary["designs"][name]["designs_with_1_pair"])
        out("    SO by family:", fam_so)

    # ---- margins
    out("")
    out("### Decisive difference margins d - theta (theta = 0.05)")
    summary["margins"] = {}
    out("| population / set | n | " + " | ".join(MBINS) + " | min d-theta | median |")
    out("|" + "---|" * (len(MBINS) + 4))
    for name, rows in pops:
        for lab, sel in (("reported SO", lambda r: r["v2_report"] == "CL4"),
                         ("SO candidates (all)", lambda r: r["v2_candidate"] == "CL4"),
                         ("withheld SO candidates", lambda r: r["v2_candidate"] == "CL4" and r["v2_report"] != "CL4"),
                         ("below-tolerance (decisive = largest diff)", lambda r: r["v2_report"] == "CL5")):
            vals = [float(r["w_d"] or r["decisive_d"]) for r in rows if sel(r) and (r["w_d"] or r["decisive_d"])]
            if not vals:
                continue
            b = margin_bins(vals)
            mm = min(vals) - THETA
            med = statistics.median(vals) - THETA
            summary["margins"]["%s|%s" % (name, lab)] = {"n": len(vals), "bins": dict(b), "min": mm, "median": med}
            out("| %s / %s | %d | %s | %.4f | %.4f |" % (name, lab, len(vals), " | ".join(str(b[x]) for x in MBINS), mm, med))

    # near-threshold SO and their native confirmation
    out("")
    out("### Near-threshold suite-omission candidates (d - theta < 0.05) and native confirmation (OB13 kills of 12)")
    near = []
    arm_of = {"20 circuits": "primary", "external": "external", "corpus": "corpus", "width set": "width"}
    for rows in (prim, ext, mqt, wid, corp):
        for r in rows:
            if r["v2_candidate"] == "CL4" and r["w_d"] and float(r["w_d"]) - THETA < 0.05:
                if r["population"] == "MQT Bench":
                    k = r.get("ob13_kills_of_12", "")
                    gf = r.get("ob13_guard_fails_of_3", "")
                else:
                    nr = nat.get((arm_of[r["population"]], r["case"], "OB13"))
                    k = nr["kills"] if nr else ("recorded B4 repair" if r["ob13_source"] else "")
                    gf = nr["guard_fails"] if nr else ""
                near.append((r["population"], r["case"], r["program"], r["family"], r["operator"], r["third"],
                             r["first_gate"], assertion_type(r["w_kind"], r["w_key"]), round(float(r["w_d"]) - THETA, 4),
                             k, gf, r["v2_report"], r["unmet"]))
    near.sort(key=lambda t: (t[0], t[8]))
    cnt = C((t[0], t[11] == "CL4") for t in near)
    out("counts (population, certified):", dict((str(k), v) for k, v in cnt.items()))
    kills_dist = collections.defaultdict(C)
    for t in near:
        kills_dist[(t[0], t[11])][str(t[9])] += 1
    for k, v in sorted(kills_dist.items()):
        out("  %s report=%s OB13 kills:" % k, dict(sorted(v.items())))
    summary["near_threshold"] = [list(t) for t in near]
    # MQT near threshold explicitly
    for t in near:
        if t[0] != "corpus":
            out("  ", t)
    out("  corpus near-threshold, certified: %d; withheld: %d" % (
        sum(1 for t in near if t[0] == "corpus" and t[11] == "CL4"), sum(1 for t in near if t[0] == "corpus" and t[11] != "CL4")))
    # all corpus SO margins by assertion type
    out("")
    out("### Corpus reported SO: margin bin x assertion type")
    so = [r for r in corp if r["v2_report"] == "CL4"]
    summary["corpus_so_margin_x_type"] = table("corpus SO margin x assertion type", so,
                                               lambda r: assertion_type(r["w_kind"], r["w_key"]), MBINS,
                                               lambda r: list(margin_bins([float(r["w_d"])]).keys())[0])

    # ---- certification and seeds
    out("")
    out("### Certification and independently seeded execution")
    cert = {}
    for name, rows in pops:
        so = [r for r in rows if r["v2_report"] == "CL4"]
        cert[name] = {"SO_certified": len(so), "OB13_from_recorded_repair": sum(1 for r in so if r["ob13_source"]),
                      "CL3_reported": sum(1 for r in rows if r["v2_report"] == "CL3")}
    mq = [r for r in mqt if r.get("d1_outcome")]
    cert["MQT Bench (120)"]["fresh_seed_D1_repairs"] = dict(C(r["d1_outcome"] for r in mq))
    cert["MQT Bench (120)"]["fresh_seed_D1_by_report"] = dict(C((r["v2_report"], r["d1_outcome"]) and r["v2_report"] + ":" + r["d1_outcome"] for r in mq))
    m2 = [r for r in mqt if r.get("d2_outcome")]
    cert["MQT Bench (120)"]["fresh_seed_D2_observation"] = dict(C(r["d2_outcome"] for r in m2))
    cert["MQT Bench (120)"]["D2_rungs"] = dict(C(r["d2_operative_rung"] for r in m2))
    cert["MQT Bench (120)"]["bound_kill_guard"] = dict(C(r["bound_b13"] + "/" + r["bound_guard"] for r in mqt if r["v2_candidate"] == "CL4"))
    summary["certification"] = cert
    for k, v in cert.items():
        out("-", k, json.dumps(v))

    # ---- combined suite versus single-witness repair on the 79 primary SO (records only)
    suite = rd(os.path.join(root, "data/primary/records/599_B5_A1G_POPULATION.csv"))
    guard = rd(os.path.join(root, "data/primary/suites/SUITE_GUARD_LEDGER.csv"))
    gl = {(r["subject"], r["suite"]): r for r in guard}
    sk = {(r["mutant_id"], r["suite"]): r for r in suite}
    so = [r for r in prim if r["v2_report"] == "CL4"]
    comb = C()
    added_both, added_rep = [], []
    for r in so:
        comb[sk[(r["case"], "S_BOTH")]["outcome"]] += 1
        added_both.append(int(gl[(r["program"], "S_BOTH")]["n_assertions"]) - int(gl[(r["program"], "S_MIN")]["n_assertions"]))
        added_rep.append(1)
    ff = {s: sum(int(gl[(p, s)]["false_fails"]) for p in {r["program"] for r in prim}) for s in ("S_MIN", "S_BOTH", "S_FAMILY", "S_COVER")}
    g8 = {(r["subject"], r["suite"]): r for r in rd(os.path.join(root, "data/primary/decision/B5_A1G_GUARD.csv"))}
    ff8 = {s: sum(int(g8[(p, s)]["false_fails"]) for p in {r["program"] for r in prim}) for s in ("S_MIN", "S_BOTH", "S_FAMILY", "S_COVER")}
    summary["combined_vs_repair_primary"] = {"SO": len(so), "combined_outcome_on_SO": dict(comb),
                                             "assertions_added_combined_total": sum(added_both),
                                             "assertions_added_combined_median": statistics.median(added_both),
                                             "assertions_added_repair_total": sum(added_rep),
                                             "original_false_fails_SUITE_GUARD_LEDGER_sampled_ref_N2000": ff,
                                             "original_false_fails_B5_A1G_GUARD_analytic_N8000": ff8,
                                             "subjects": len({r['program'] for r in so})}
    out("")
    out("### Combined suite (S_BOTH) vs single-witness repair on the 79 primary suite omissions (records only)")
    out(json.dumps(summary["combined_vs_repair_primary"]))
    # corpus/width/mqt/external: is the witness an assertion the combined suite would contain?
    out("Witness contained in a combined suite (all-qubit marginals + adjacent two-qubit Z products):")
    summary["witness_in_combined"] = {}
    for name, rows in pops:
        so = [r for r in rows if r["v2_report"] == "CL4"]
        if not so:
            continue
        inside = C("yes" if (r["w_kind"] == "marginal" or assertion_type(r["w_kind"], r["w_key"]) == "Z-product w2 adjacent") else "no/unknown" for r in so)
        summary["witness_in_combined"][name] = dict(inside)
        out("  ", name, dict(inside))

    # ---- 20 circuits: sufficient condition x position for CL3
    ol = [r for r in prim if r["v2_report"] == "CL3"]
    summary["primary_ol_entailed_x_pos"] = table("20 circuits CL3 entailed x position", ol,
                                                 lambda r: "entailed (sufficient condition)" if r["entailed_diag"] else "contingent",
                                                 POSCOLS, pos_label)
    summary["primary_ol_terminal"] = dict(C("terminal" if r["terminal"] else "not terminal" for r in ol))
    out("20 circuits CL3 terminal-site:", summary["primary_ol_terminal"], "| entailed among all 599:",
        dict(C((r["entailed_diag"], r["v2_report"]) and "%s:%s" % (r["entailed_diag"], r["v2_report"]) for r in prim if r["entailed_diag"])))
    # ---- corpus details
    out("")
    out("### Corpus observation limitations: sufficient condition (all gates from first divergence diagonal in both) x position")
    ol = [r for r in corp if r["v2_report"] == "CL3"]
    summary["corpus_ol_entailed_x_pos"] = table("corpus CL3 entailed x position", ol,
                                                lambda r: "entailed (sufficient condition)" if r["entailed_diag"] else "contingent",
                                                POSCOLS, pos_label)
    summary["corpus_ol_terminal"] = {"entailed=%s|terminal=%s" % k: v for k, v in C((r["entailed_diag"], r["terminal"]) for r in ol).items()}
    out("CL3 (entailed, terminal-site) counts:", {str(k): v for k, v in summary["corpus_ol_terminal"].items()})
    so = [r for r in corp if r["v2_report"] == "CL4"]
    summary["corpus_so_terminal"] = {"terminal=%s" % k: v for k, v in C(r["terminal"] for r in so).items()}
    out("CL4 terminal-site counts:", {str(k): v for k, v in summary["corpus_so_terminal"].items()})
    summary["corpus_so_type_x_pos"] = table("corpus CL4 assertion type x position", so,
                                            lambda r: assertion_type(r["w_kind"], r["w_key"]), POSCOLS, pos_label)
    summary["corpus_cause_x_blockdelete"] = {"%s|block=%s" % k: v for k, v in C((r["v2_report"], r["gate_class"] == "multi-gate block") for r in corp if r["v2_report"] in ("CL3", "CL4")).items()}
    out("cause x block-deletion:", {str(k): v for k, v in summary["corpus_cause_x_blockdelete"].items()})
    for cl in ("CL3", "CL4"):
        rr = [r for r in corp if r["v2_report"] == cl]
        out("corpus %s: programs %d, families %d %s" % (cl, len({r["program"] for r in rr}), len({r["family"] for r in rr}), dict(C(r["family"] for r in rr))))
        summary["corpus_%s_programs" % cl] = len({r["program"] for r in rr})
    # withheld candidates among stable survivors
    wh = [r for r in corp if r["v2_candidate"] == "CL4" and r["v2_report"] == "Unresolved"]
    rows45 = []
    for r in wh:
        nr = nat.get(("corpus", r["case"], "OB13"))
        rows45.append((r["native_verdict"], r["unmet"], list(margin_bins([float(r["w_d"])]).keys())[0],
                       nr["kills"] if nr else "not run", nr["guard_fails"] if nr else ""))
    summary["corpus_withheld_candidates"] = {"|".join(map(str, k)): v for k, v in C(rows45).items()}
    out("corpus withheld CL4 candidates (verdict, unmet, margin bin, OB13 kills, OB13 guard fails): n=%d" % len(rows45))
    for k, v in sorted(C(rows45).items()):
        out("   ", k, v)
    st = [t_ for t_ in rows45 if t_[0] == "SURVIVED"]
    out("  stable-survivor withheld: %d; OB13-only with margin<0.05 and kills 5..11: %d" % (
        len(st), sum(1 for t_ in st if t_[1] == "OB13" and t_[2] in ("(0,0.01)", "[0.01,0.05)") and t_[3] not in ("not run", "12"))))
    # nesting: width set vs corpus
    co = {r["case"]: r for r in corp}
    nest = C()
    for r in wid:
        c = co[r["corpus_case_key"]]
        nest[(r["v2_report"] or "not executed", c["v2_report"])] += 1
    summary["width_vs_corpus_reports"] = {"|".join(k): v for k, v in nest.items()}
    out("width-set report vs corpus report for the same 162 pairs:", dict(nest))
    dup = C((r["case"].split("/")[1]) for r in corp)
    out("corpus case ids appearing in two case sets (QRA ids reused by qra_cases_v1_1, distinct content):",
        sum(1 for v in dup.values() if v > 1))
    tsvrows = list(csv.DictReader(open(tsv, newline=""), delimiter="\t"))
    pairs_ = C((r["orig_sha256"], r["mut_sha256"]) for r in tsvrows)
    out("distinct (original sha, mutant sha) among corpus pairs:", len(pairs_), "| duplicated:", sum(1 for v in pairs_.values() if v > 1))
    summary["corpus_distinct_content_pairs"] = len(pairs_)

    # ---- OB13 kill rate versus margin, every native confirmation run (R2V_NATIVE.csv + MQT C2_NATIVE.csv)
    out("")
    out("### Native confirmation (witness alone, N=2000, seeds 42-53): kills of 12 by margin d - theta")
    runs = [(r["arm"], float(r["inst_d"]), int(r["kills"]), int(r["guard_fails"])) for r in
            rd(os.path.join(root, "data/certification/outcomes/R2V_NATIVE.csv")) if r["purpose"] == "OB13"]
    runs += [("mqt", float(r["inst_d"]), int(r["kills"]), int(r["guard_fails"])) for r in
             rd(os.path.join(root, "data/prospective/mqt_bench/records/stage_c/C2_NATIVE.csv")) if r["purpose"] == "OB13"]
    kb = collections.defaultdict(C)
    for arm, d, k, g in runs:
        b = list(margin_bins([d]).keys())[0]
        kb[b]["runs"] += 1
        kb[b]["12/12"] += int(k == 12)
        kb[b]["<12"] += int(k < 12)
    out("| margin bin | OB13 runs | killed 12/12 | killed <12 |")
    out("|---|---|---|---|")
    for b in MBINS:
        if kb[b]["runs"]:
            out("| %s | %d | %d | %d |" % (b, kb[b]["runs"], kb[b]["12/12"], kb[b]["<12"]))
    summary["ob13_by_margin"] = {b: dict(kb[b]) for b in MBINS if kb[b]["runs"]}
    # ---- MQT per subject (paper table check)
    out("")
    out("### MQT Bench per subject: I/R/D, sites, first gate")
    for s in sorted({r["program"] for r in mqt}):
        rr = [r for r in mqt if r["program"] == s]
        oc = C(r["operator"] for r in rr)
        out("  %s I/R/D %d/%d/%d sites %d first-gate %d" % (s, oc["insert"], oc["replace"], oc["delete"],
                                                            len({r["anchor"] for r in rr}), sum(r["first_gate"] for r in rr)))
    # ---- corpus diagonal stratum among stable survivors (Section 5.6)
    ss = [r for r in corp if r["native_verdict"] == "SURVIVED"]
    dg = C((r["diagonal_stratum"], r["v2_report"] == "CL3") for r in ss)
    out("corpus stable survivors by diagonal stratum (stratum, is CL3):", {str(k): v for k, v in dg.items()})
    summary["corpus_stable_by_stratum"] = {"%s|%s" % k: v for k, v in dg.items()}

    # ---- Bugs4Q defects
    dd = rd(os.path.join(root, "data/external/defects/B3_REAL_DEFECTS_FRESH.csv"))
    el = rd(os.path.join(root, "data/external/defects/B3_QUTEST_ELIGIBILITY_FRESH.csv"))
    fd = rd(os.path.join(root, "data/certification/outcomes/R2V_FINAL_DEFECT.csv"))
    summary["bugs4q"] = {"defects": len(dd), "evidence_depth": dict(C(r["evidence_depth"] for r in dd)),
                         "eligibility": dict(C(r["qutest_eligibility"] for r in el)),
                         "final": [(r["defect_id"], r["native_verdict"], r["v2_candidate"], r["v2_report"], r["unmet"], r["w_kind"]) for r in fd]}
    out("")
    out("### Bugs4Q:", json.dumps(summary["bugs4q"]))
    # ---- write
    fields = []
    for rows in (prim, ext, mqt, wid, corp):
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
    with open(os.path.join(od, "cases_all.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rows in (prim, ext, mqt, wid, corp):
            for r in rows:
                w.writerow(r)
    with open(os.path.join(od, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True, default=str)
    with open(os.path.join(od, "inventory_tables.txt"), "w") as f:
        f.write("\n".join(OUT_LINES) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:5])
