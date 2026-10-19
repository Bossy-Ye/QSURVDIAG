"""Revision 2, step 4.1: a cheap diagnostic workflow against QSurvDiag.

Cheap workflow, per diagnosed pair:
  1. contract, endpoint-state and observation relations (identical to QSurvDiag's);
  2. if the observations differ, search single-qubit Z marginals and two-qubit Z
     correlators for an assertion above theta;
  3. otherwise escalate to the exhaustive universe.
It settles CL1, CL2 and CL3 exactly as QSurvDiag does, names a CL4 repair whenever a
low-order witness exists, and must escalate every pair whose only witnesses are
higher-order (or that has none, i.e. a CL5 candidate). Runtime is the analytic evaluation
time of the witness search against the frozen full-universe enumeration.
Execution cost in shots is structural: the study's QUTest harness evaluates every
assertion of a suite on the same N-shot execution per repetition (qutest_adapter.make_test).
"""
import csv, json, os, sys, time, itertools
import numpy as np
sys.path.insert(0, "/Users/mac/Desktop/ZX-STUDY/paper-artifact/github/code/qsurvdiag")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_lib as L, e1_relations as REL
from r2_corpus_width import state, PROG
PA = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/"
OUT = os.path.dirname(os.path.abspath(__file__))
THETA = 0.05

def cheap_max(pa, pb, n):
    d = [abs(REL.marginal_p1(pa, n, q) - REL.marginal_p1(pb, n, q)) for q in range(n)]
    d += [abs(REL.zprod(pa, n, [i, j]) - REL.zprod(pb, n, [i, j]))
          for i, j in itertools.combinations(range(n), 2)]
    return max(d) if d else 0.0

def timed(f, *a):
    t = time.perf_counter(); v = f(*a); return v, time.perf_counter() - t

def row_for(arm, pid, report, pa, pb, n):
    cm, tc = timed(cheap_max, pa, pb, n)
    ud, tf = timed(REL.universe_diffs, pa, pb, n)
    return {"arm": arm, "pair": pid, "n": n, "report": report, "cheap_max": cm,
            "cheap_witness": cm > THETA, "full_max": max(ud), "t_cheap_s": tc, "t_full_s": tf}

def main():
    rows = []
    ref = csv.DictReader(open(PA + "github/results/recovered/599_B1_REFERENCE_RERUN_FRESH.csv"))
    for r in ref:
        rep = r["diagnostic_outcome"]
        if rep in ("NA_KILLED",): continue
        m = L.MUT[r["mutant_id"]]; sva, pa, n = REL._orig_cache(m["subject"])
        pb = REL.probs(REL._sv(m["gates"], n))
        rows.append(row_for("primary", r["mutant_id"], rep, pa, pb, n))
    for r in (json.loads(l) for l in open(PA + "github/results/corpus/T2A_STRATIFIED_RAW.jsonl")):
        rep = r["diagnostic_outcome"]
        if rep in ("NA_KILLED",): continue
        if rep in ("CL4", "CL5"):
            sva, n = state(PROG + f"{r['case_set']}/{r['pair_id']}_origin.qasm")
            svb, _ = state(PROG + f"{r['case_set']}/{r['pair_id']}_mutant.qasm")
            rows.append(row_for("corpus", r["pair_id"], rep, np.abs(sva) ** 2, np.abs(svb) ** 2, n))
        else:
            rows.append({"arm": "corpus", "pair": r["pair_id"], "n": r["n"], "report": rep})
    for r in csv.DictReader(open(PA + "github/results/scale/B2_SCALE_FRESH.csv")):
        rep = r["report"]
        if rep in ("NA_KILLED", ""): continue
        if rep in ("CL4", "CL5"):
            from r2_corpus_width import find
            sva, n = state(find(r["pair_id"], "origin")); svb, _ = state(find(r["pair_id"], "mutant"))
            rows.append(row_for("width", r["pair_id"], rep, np.abs(sva) ** 2, np.abs(svb) ** 2, n))
        else:
            rows.append({"arm": "width", "pair": r["pair_id"], "n": r["n"], "report": rep})
    keys = sorted({k for x in rows for k in x})
    with open(os.path.join(OUT, "R2_CHEAP_BASELINE.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("rows", len(rows))

if __name__ == "__main__":
    main()
