"""Revision 2, step 3.1 (sensitivity): how the excluded count kinds separate CL5 pairs.

For every corpus and width-set pair that stays CL5 under the full distribution family
(RAcert false in R2_CORPUS_WIDTH_PAIRS.csv), this records whether Pearson correlation or
the most-frequent check exceeds theta, and for each separating correlation whether one of
its two bits is set in fewer than one shot in N = 2000 in both programs. Such a bit is
constant in any sample of that size with high probability, so QUTest's constant-bit
convention returns the same value for both programs and the analytic separation cannot be
reproduced by execution. For the largest correlation change of each pair it also records
the two bits' probabilities.
"""
import csv, os, sys
import numpy as np
sys.path.insert(0, "/Users/mac/Desktop/ZX-STUDY/paper-artifact/github/code/qsurvdiag")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_relations as REL
from r2_corpus_width import state, PROG, find
from r2_primary import pearson_all, most_frequent_sep

OUT = os.path.dirname(os.path.abspath(__file__))
N, THETA = 2000, 0.05
rare = lambda p: p < 1.0 / N or p > 1.0 - 1.0 / N

def main():
    rows = []
    for r in csv.DictReader(open(os.path.join(OUT, "R2_CORPUS_WIDTH_PAIRS.csv"))):
        if r["report"] != "CL5" or r["RAcert"] != "false":
            continue
        if r["arm"] == "corpus":
            sa, n = state(PROG + f"{r['case_set']}/{r['pair_id']}_origin.qasm")
            sb, _ = state(PROG + f"{r['case_set']}/{r['pair_id']}_mutant.qasm")
        else:
            sa, n = state(find(r["pair_id"], "origin")); sb, _ = state(find(r["pair_id"], "mutant"))
        pa, pb = np.abs(sa) ** 2, np.abs(sb) ** 2
        ca, cb = pearson_all(pa, n), pearson_all(pb, n)
        seps = [k for k in ca if abs(ca[k] - cb[k]) > THETA]
        def rare_pair(k):
            return any(rare(REL.marginal_p1(pa, n, q)) and rare(REL.marginal_p1(pb, n, q)) for q in k)
        kmax = max(ca, key=lambda k: abs(ca[k] - cb[k])) if ca else None
        mf = most_frequent_sep(pa, pb)
        rows.append({
            "arm": r["arm"], "case_set": r["case_set"], "pair_id": r["pair_id"], "n": n,
            "max_U5": max(REL.universe_diffs(pa, pb, n)),
            "correlation_separations": len(seps),
            "rare_bit_correlation_separations": sum(1 for k in seps if rare_pair(k)),
            "most_frequent_separates": bool(mf is not None and mf > THETA),
            "separated_by_excluded_kinds": bool(seps) or bool(mf is not None and mf > THETA),
            "only_rare_bit_separations": bool(seps) and all(rare_pair(k) for k in seps)
                                         and not (mf is not None and mf > THETA),
            "max_corr_pair": "" if kmax is None else f"{kmax[0]}-{kmax[1]}",
            "max_corr_change": 0.0 if kmax is None else abs(ca[kmax] - cb[kmax]),
            "max_corr_bit_p1_original": "" if kmax is None else
                ";".join(f"{REL.marginal_p1(pa, n, q):.3g}" for q in kmax),
            "max_corr_bit_p1_mutant": "" if kmax is None else
                ";".join(f"{REL.marginal_p1(pb, n, q):.3g}" for q in kmax)})
    with open(os.path.join(OUT, "R2_CONDITIONAL_SEPARATIONS.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("rows", len(rows))

if __name__ == "__main__":
    main()
