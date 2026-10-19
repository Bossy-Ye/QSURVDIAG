"""A1b extension -- NOT in the original B5 plan, added after A1b's registered
prediction only partially held.  Exact references cut false-fail repetitions by
77 % but left nine cells guard-invalid at one failure in twelve.  This asks
whether the residual is finite-shot noise by raising N on those cells alone.
"""
import csv, json, sys, time
sys.path.insert(0, "."); sys.path.insert(0, "../cross_tool_stage/qutest")
from e1_lib import orig, nq, suite_terms
import e1_relations as REL
import qutest_adapter as QA

OUT, R = "definitive_rerun_b5", 12
BUDGETS = (2000, 8000, 32000)
RES = [r for r in csv.DictReader(open(f"{OUT}/B5_A1B_GUARD_EXACT.csv"))
       if r["exact_ref_guard"] == "FALSE_FAIL"]
print(f"residual guard-invalid cells at exact references: {len(RES)}\n")
print(f"{'subject':12}{'suite':10}{'assn':>5}   " + "".join(f"N={b:<8}" for b in BUDGETS))

def asserts(sub, suite):
    n = nq[sub]; p = REL.probs(REL._sv(orig[sub], n)); a = []
    for t in suite_terms(sub)[suite]:
        if len(t) == 1:
            a.append(QA.marginal_assertion(t[0], round(REL.marginal_p1(p, n, t[0]), 4)))
        else:
            a.append(f'//% expect observable "{" ".join(f"Z{q}" for q in t)}" ~= '
                     f'{round(REL.zprod(p, n, list(t)), 4)} atol={QA.ATOL}')
    return a

rows, t0 = [], time.time()
for r in RES:
    sub, suite = r["subject"], r["suite"]; n = nq[sub]; a = asserts(sub, suite)
    out = {"subject": sub, "suite": suite, "n_assertions": len(a), "reps": R}
    cells = []
    for N in BUDGETS:
        v = [QA.run_qutest(QA.make_test(orig[sub], n, a, shots=N, seed=QA.SEED + i))[0]
             for i in range(R)]
        f = sum(1 for x in v if x == "KILLED"); out[f"false_fails_N{N}"] = f
        cells.append(f"{f}/{R:<6}")
    rows.append(out)
    print(f"  {sub:12}{suite:10}{len(a):>5}   " + "".join(f"{c:<10}" for c in cells))

with open(f"{OUT}/B5_A1B_EXT_SHOTS.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
print()
for N in BUDGETS:
    clean = sum(1 for r in rows if r[f"false_fails_N{N}"] == 0)
    print(f"  N = {N:<6} cells clean: {clean} of {len(rows)}")
print(f"elapsed {time.time()-t0:.0f}s")
json.dump({"cells": len(rows), "budgets": list(BUDGETS),
           "clean_by_budget": {str(N): sum(1 for r in rows if r[f"false_fails_N{N}"] == 0)
                               for N in BUDGETS}},
          open(f"{OUT}/B5_A1B_EXT_SUMMARY.json", "w"), indent=1)
