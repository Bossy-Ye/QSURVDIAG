"""Experiment 2, Part A steps 4-6: the analytic decision-resolution surface.

d_a comes from exact evidence only; no sampled outcome redefines it.
"""
import csv, json
import numpy as np
from collections import Counter
import e1_relations as REL
from e1_lib import MUT, nq, outreg, suite_terms
from decision_bound import bound_record, EQ4_ROW, NOT_COVERED
from qsurvdiag_confirmatory import (T, F, U, certify, empirical,
                                    compare_threshold, exists_above)
from e1_07_diagnose import contract_equivalent

THETAS = [0.01, 0.025, 0.05, 0.10, 0.25, 0.50]
NS = [500, 2000, 8000]
R = 12
D = {r["mutant_id"]: r for r in csv.DictReader(open("E1_DIAGNOSTIC_TABLE.csv"))
     if r["suite"] == "S_MIN"}

def family_of(kind):
    return {"marginal": "marginal", "observable": "observable",
            "probability": "probability", "entropy": "entropy",
            "distribution": "distribution"}[kind]

def universe_detail(pa, pb, n):
    """Every instance of the closed count-substrate universe with its family."""
    out = []
    for q in range(n):
        out.append(("marginal", f"m[{q}]",
                    abs(REL.marginal_p1(pa, n, q) - REL.marginal_p1(pb, n, q))))
    for m in range(1, 2 ** n):
        qs = [q for q in range(n) if (m >> q) & 1]
        out.append(("observable", "Z" + "Z".join(map(str, qs)),
                    abs(REL.zprod(pa, n, qs) - REL.zprod(pb, n, qs))))
    for i in range(2 ** n):
        out.append(("probability", format(i, f"0{n}b"), abs(pa[i] - pb[i])))
    ea = float(-(pa[pa > 0] * np.log2(pa[pa > 0])).sum())
    eb = float(-(pb[pb > 0] * np.log2(pb[pb > 0])).sum())
    out.append(("entropy", "H", abs(ea - eb)))
    out.append(("distribution", "TVD", float(0.5 * np.abs(pa - pb).sum())))
    return out

grid, bounds = [], []
for mid, b in D.items():
    sub = b["subject"]; n = nq[sub]
    sva, pa, _ = REL._orig_cache(sub)
    pb = REL.probs(REL._sv(MUT[mid]["gates"], n))
    R_S = REL.state_equal(sva, REL._sv(MUT[mid]["gates"], n))
    R_O = REL.obs_equal(pa, pb)
    R_C = contract_equivalent(mid)
    U_all = universe_detail(pa, pb, n)
    # CORRECTION 8 (conformance category 8).  The decisive instance is the largest
    # d_a over the admissible universe ENTIRE.  The superseded line filtered
    # U_all by `EQ4_ROW.get(x[0]) is not None`, so a family with no finite-shot row
    # left the Stage-2 maximum -- a Stage-3 object editing a Stage-2 comparison.
    # Section III: the bound "does not define R_A^theta or R_T^theta, which compare
    # d_a against theta analytically".
    dec_fam, dec_inst, dec_d = max(U_all, key=lambda x: x[2])
    ent = next(x for x in U_all if x[0] == "entropy")
    smin = suite_terms(sub)["S_MIN"]
    sd = [("marginal", f"m[{t[0]}]", abs(REL.marginal_p1(pa, n, t[0]) - REL.marginal_p1(pb, n, t[0])))
          for t in smin]
    s_fam, s_inst, s_d = max(sd, key=lambda x: x[2]) if sd else ("", "", 0.0)
    for th in THETAS:
        # CORRECTION 9: three-valued, over unrounded stored values, applied to the
        # universe-decisive comparison, the suite-decisive comparison and the
        # recorded entropy companion alike.
        R_A = exists_above([x[2] for x in U_all], th)
        R_T = compare_threshold(s_d, th)
        R_ent = compare_threshold(ent[2], th)
        rel = {"R_C": T if R_C else F, "R_S": T if R_S else F, "R_O": T if R_O else F,
               "R_A": R_A, "R_T": R_T}
        res = certify(rel, {f"OB{i:02d}": "satisfied" for i in range(1, 20)})
        grid.append({"mutant_id": mid, "subject": sub, "n": n,
                     "profile": "QT_0_1_0__COUNT_SUBSTRATE", "theta": th,
                     "R_C": R_C, "R_S": R_S, "R_O": R_O,
                     "R_A": R_A.value, "R_T": R_T.value, "R_entropy": R_ent.value,
                     "candidate_report": res["candidate"] or "",
                     "decisive_family": dec_fam, "decisive_instance": dec_inst,
                     "decisive_d_a": round(dec_d, 8),
                     "suite_family": s_fam, "suite_instance": s_inst,
                     "suite_d_a": round(s_d, 8),
                     "entropy_d_a": round(ent[2], 8),
                     "baseline_diagnosis": b["diagnostic_outcome"]})
        for N in NS:
            for fam, inst, d in ((dec_fam, dec_inst, dec_d), ("entropy", "H", ent[2])):
                # CORRECTION 7: the entropy row now exists and, like the
                # distribution row, is a function of |Omega|, so both receive
                # omega_bits.  The superseded code passed it only for the
                # distribution family and then overwrote the entropy verdict with
                # "NA_UNKNOWN_FROM_EQ4"; entropy is inside Eq. (5) now, so the
                # override is removed and the row speaks for itself.
                br = bound_record(f"{mid}|{inst}", fam, d, th, N, R,
                                  omega_bits=n if fam in ("distribution", "entropy")
                                  else None)
                br.update({"mutant_id": mid, "subject": sub, "n": n,
                           "assertion_instance": inst, "role":
                           "decisive" if fam != "entropy" else "entropy_companion"})
                bounds.append(br)

with open("E2_ANALYTIC_GRID.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(grid[0].keys())); w.writeheader(); w.writerows(grid)
with open("E2_BOUND_RESULTS.csv", "w", newline="") as fh:
    keys = sorted({k for r in bounds for k in r})
    w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
    w.writeheader(); w.writerows(bounds)
print("analytic grid rows:", len(grid), " bound rows:", len(bounds))
for th in THETAS:
    c = Counter(r["candidate_report"] or "none" for r in grid if r["theta"] == th)
    print(f"  theta={th:<6} {dict(sorted(c.items()))}")
print("bound status:", dict(Counter(r["bound_status"] for r in bounds)))
