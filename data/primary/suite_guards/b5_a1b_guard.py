"""A1b -- re-run the original-program guard with EXACT analytic references.

Everything else is unchanged: same subjects, same four systematic suites, same
N = 2000, same R = 12, same ATOL, same seeds.  The only variable is whether each
assertion's reference is the exact analytic value or a 2000-shot estimate.
Plan hash ac1f75d4.
"""
import csv, json, sys, time
sys.path.insert(0, "."); sys.path.insert(0, "../cross_tool_stage/qutest")
from e1_lib import orig, nq, suite_terms
import e1_relations as REL
import qutest_adapter as QA

OUT, R = "definitive_rerun_b5", 12
SUITES = ("S_MIN", "S_COVER", "S_FAMILY", "S_BOTH")

def exact_assertions(sub):
    n = nq[sub]; p = REL.probs(REL._sv(orig[sub], n))
    out = {}
    for suite, terms in suite_terms(sub).items():
        a = []
        for t in terms:
            if len(t) == 1:
                a.append(QA.marginal_assertion(t[0], round(REL.marginal_p1(p, n, t[0]), 4)))
            else:
                zs = " ".join(f"Z{q}" for q in t)
                a.append(f'//% expect observable "{zs}" ~= '
                         f'{round(REL.zprod(p, n, list(t)), 4)} atol={QA.ATOL}')
        out[suite] = a
    return out

OLD = {(r["subject"], r["suite"]): r for r in csv.DictReader(open("SUITE_GUARD_LEDGER.csv"))}
rows, t0 = [], time.time()
print(f"{'subject':16} {'suite':9} {'assn':>4}  sampled-ref guard   exact-ref guard")
for sub in sorted(nq):
    A = exact_assertions(sub); n = nq[sub]
    for suite in SUITES:
        a = A[suite]
        v = [QA.run_qutest(QA.make_test(orig[sub], n, a, seed=QA.SEED + r))[0] for r in range(R)]
        fails = sum(1 for x in v if x == "KILLED")
        old = OLD.get((sub, suite), {})
        rows.append({"subject": sub, "suite": suite, "n_assertions": len(a),
                     "sampled_ref_guard": old.get("guard", ""),
                     "sampled_ref_false_fails": old.get("false_fails", ""),
                     "exact_ref_false_fails": fails, "reps": R,
                     "exact_ref_guard": "CLEAN" if fails == 0 else "FALSE_FAIL"})
        mark = "  <-- cleared" if old.get("guard") == "FALSE_FAIL" and fails == 0 else ""
        print(f"  {sub:16} {suite:9} {len(a):4}  {old.get('guard',''):11} "
              f"{old.get('false_fails','')}/{R:<3}  {'CLEAN' if fails==0 else 'FALSE_FAIL':11} {fails}/{R}{mark}")

with open(f"{OUT}/B5_A1B_GUARD_EXACT.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
before = sum(1 for r in rows if r["sampled_ref_guard"] == "FALSE_FAIL")
after  = sum(1 for r in rows if r["exact_ref_guard"] == "FALSE_FAIL")
print(f"\nguard-invalid cells: {before} with a sampled reference -> {after} with an exact reference")
print(f"elapsed {time.time()-t0:.0f}s")
json.dump({"cells": len(rows), "false_fail_sampled_reference": before,
           "false_fail_exact_reference": after, "N": QA.INNER_SHOTS, "R": R,
           "atol": QA.ATOL}, open(f"{OUT}/B5_A1B_SUMMARY.json", "w"), indent=1)
