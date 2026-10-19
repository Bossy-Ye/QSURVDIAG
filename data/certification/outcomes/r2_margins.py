"""Revision 2, step 2.2: numerical margins of every endpoint-state and observation decision.

For each pair: state margin = | |<psi_P|psi_M>| - 1 | (the quantity the frozen state_equal
compares with eps_num) and observation margin = max_z |p_P(z) - p_M(z)| (obs_equal).
The error policy needs the largest margin decided equal, the smallest decided different,
and the number of margins inside the guard band [1e-12, 1e-6]. This recomputation covers
all 599 primary pairs, the 1,537-pair corpus frame and the 143 executed width-set pairs,
and so replaces the pre-recovery eps_num sweep, which covered 261 cases.
"""
import csv, json, os, sys
import numpy as np
sys.path.insert(0, "/Users/mac/Desktop/ZX-STUDY/paper-artifact/github/code/qsurvdiag")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_lib as L, e1_relations as REL
from r2_corpus_width import state, find, PROG
PA = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/"
OUT = os.path.dirname(os.path.abspath(__file__))

def margins(sva, svb):
    sm = abs(abs(np.vdot(sva, svb)) - 1.0)
    om = float(np.max(np.abs(np.abs(sva) ** 2 - np.abs(svb) ** 2)))
    return sm, om

def main():
    rows = []
    for r in csv.DictReader(open(PA + "github/results/recovered/599_B1_REFERENCE_RERUN_FRESH.csv")):
        m = L.MUT[r["mutant_id"]]; sva, _, n = REL._orig_cache(m["subject"])
        svb = REL._sv(m["gates"], n); sm, om = margins(sva, svb)
        rows.append({"arm": "primary", "pair": r["mutant_id"], "state_margin": sm, "obs_margin": om,
                     "R_S_frozen": r["R_S"], "R_O_frozen": r["R_O"]})
    for r in (json.loads(l) for l in open(PA + "github/results/corpus/T2A_STRATIFIED_RAW.jsonl")):
        sva, _ = state(PROG + f"{r['case_set']}/{r['pair_id']}_origin.qasm")
        svb, _ = state(PROG + f"{r['case_set']}/{r['pair_id']}_mutant.qasm")
        sm, om = margins(sva, svb)
        rows.append({"arm": "corpus", "pair": r["pair_id"], "state_margin": sm, "obs_margin": om,
                     "R_S_frozen": str(r["R_S"]).lower(), "R_O_frozen": str(r["R_O"]).lower()})
    for r in csv.DictReader(open(PA + "github/results/scale/B2_SCALE_FRESH.csv")):
        po, pm = find(r["pair_id"], "origin"), find(r["pair_id"], "mutant")
        if not po or not pm or r["status"] != "OK": continue
        sva, _ = state(po); svb, _ = state(pm); sm, om = margins(sva, svb)
        rows.append({"arm": "width", "pair": r["pair_id"], "state_margin": sm, "obs_margin": om,
                     "R_S_frozen": r["R_S"], "R_O_frozen": r["R_O"]})
    with open(os.path.join(OUT, "R2_MARGINS.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("rows", len(rows))

if __name__ == "__main__":
    main()
