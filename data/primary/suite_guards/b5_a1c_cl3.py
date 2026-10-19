"""A1c -- the registered test.

With the guard clean on every cell (exact references, N = 8000), every baseline
CL3 case is evaluable under S_FAMILY and S_BOTH.  Property III.3 says no
same-profile suite change can kill a CL3 case, so the registered prediction is
0 kills.  A single kill refutes the structural claim.  Plan hash ac1f75d4.
"""
import csv, json, sys, time
sys.path.insert(0, "."); sys.path.insert(0, "../cross_tool_stage/qutest")
from e1_lib import orig, nq, suite_terms, MUT
import e1_relations as REL
import qutest_adapter as QA

B1, OUT, R, N = "definitive_rerun_b1", "definitive_rerun_b5", 12, 8000
SUITES = ("S_FAMILY", "S_BOTH", "S_COVER")

def asserts(sub, suite):
    n = nq[sub]; p = REL.probs(REL._sv(orig[sub], n)); a = []
    for t in suite_terms(sub)[suite]:
        if len(t) == 1:
            a.append(QA.marginal_assertion(t[0], round(REL.marginal_p1(p, n, t[0]), 4)))
        else:
            a.append(f'//% expect observable "{" ".join(f"Z{q}" for q in t)}" ~= '
                     f'{round(REL.zprod(p, n, list(t)), 4)} atol={QA.ATOL}')
    return a

CL3 = [r for r in csv.DictReader(open(f"{B1}/B1_REFERENCE_RERUN_FRESH.csv"))
       if r["diagnostic_outcome"] == "CL3"]
print(f"baseline CL3 cases: {len(CL3)}   suites: {SUITES}   exact references, N = {N}, R = {R}\n")

rows, t0 = [], time.time()
for k, r in enumerate(CL3, 1):
    mid = r["mutant_id"]; m = MUT[mid]; sub = m["subject"]; n = nq[sub]
    line = []
    for suite in SUITES:
        a = asserts(sub, suite)
        g = [QA.run_qutest(QA.make_test(orig[sub], n, a, shots=N, seed=QA.SEED + i))[0]
             for i in range(R)]
        gf = sum(1 for v in g if v == "KILLED")
        if gf:
            rows.append({"mutant_id": mid, "subject": sub, "suite": suite,
                         "guard_false_fails": gf, "kills": "", "reps": R,
                         "outcome": "VOID_NOT_EVALUABLE"})
            line.append(f"{suite}=VOID"); continue
        v = [QA.run_qutest(QA.make_test(m["gates"], n, a, shots=N, seed=QA.SEED + i))[0]
             for i in range(R)]
        kills = sum(1 for x in v if x == "KILLED")
        out = "KILLED" if kills == R else "SURVIVED" if kills == 0 else "UNSTABLE"
        rows.append({"mutant_id": mid, "subject": sub, "suite": suite,
                     "guard_false_fails": 0, "kills": kills, "reps": R, "outcome": out})
        line.append(f"{suite}={out}")
    print(f"  [{k}/{len(CL3)}] {mid:16} {sub:10} " + "  ".join(line))

import collections
with open(f"{OUT}/B5_A1C_CL3_RECOVERED.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
print()
for suite in SUITES:
    g = [r for r in rows if r["suite"] == suite]
    ev = [r for r in g if r["outcome"] != "VOID_NOT_EVALUABLE"]
    k = sum(1 for r in ev if r["outcome"] == "KILLED")
    print(f"  {suite:9} evaluable {len(ev):2}/{len(g)}  killed {k}  "
          f"-> {k} of {len(ev)}" + ("  *** PREDICTION REFUTED ***" if k else ""))
json.dump({"cl3_cases": len(CL3), "suites": list(SUITES), "N": N, "R": R,
           "reference": "exact analytic",
           "by_suite": {s: {"evaluable": sum(1 for r in rows if r["suite"] == s
                                             and r["outcome"] != "VOID_NOT_EVALUABLE"),
                            "killed": sum(1 for r in rows if r["suite"] == s
                                          and r["outcome"] == "KILLED")} for s in SUITES}},
          open(f"{OUT}/B5_A1C_SUMMARY.json", "w"), indent=1)
print(f"elapsed {time.time()-t0:.0f}s")
