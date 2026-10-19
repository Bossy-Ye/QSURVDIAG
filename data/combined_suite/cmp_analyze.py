"""Summaries of the matched repair comparison (plan: PLAN.md). Usage:
  python3 -I cmp_analyze.py <CMP_CASES.csv> <CMP_SUMMARY.json> <out json>"""
import csv, json, sys, collections

rows = list(csv.DictReader(open(sys.argv[1]))); summ = json.load(open(sys.argv[2]))
from pathlib import Path                     # cases whose repairs the v3 amendment issues (data/certification/witness_order)
V3 = {(r["population"], k) for r in csv.DictReader(open(Path(sys.argv[1]).resolve().parents[1] / "certification/witness_order/IMPACT.csv")) for k in r["changed"].split(";") if k}
for r in rows:
    if (r["arm"], r["case"]) in V3: r["certified_by_D"] = "True"
B = lambda x: x == "True"
def block(rs):
    n = len(rs)
    out = {"cases": n, "programs": len({r["program"] for r in rs}), "D_designs": len({r["D_suite_id"] for r in rs}),
           "S_designs": len({r["S_suite_id"] for r in rs}), "witness_in_S": sum(B(r["witness_in_S"]) for r in rs),
           "S_ideal_kills": sum(B(r["S_ideal_kills"]) for r in rs)}
    for p in ("D", "S"):
        out[f"{p}_mutant_12of12"] = sum(int(r[f"{p}_mut_kills"]) == 12 for r in rs)
        out[f"{p}_mutant_split"] = sum(0 < int(r[f"{p}_mut_kills"]) < 12 for r in rs)
        out[f"{p}_mutant_0"] = sum(int(r[f"{p}_mut_kills"]) == 0 for r in rs)
        out[f"{p}_linked_original_fail_gt1"] = sum(int(r[f"{p}_orig_fails"]) > 1 for r in rs)
        out[f"{p}_supported"] = sum(B(r[f"{p}_supported"]) for r in rs)
        out[f"{p}_unsupported_runs"] = sum(int(r[f"{p}_mut_unsupported"]) + int(r[f"{p}_orig_unsupported"]) for r in rs)
        out[f"{p}_assertions_total"] = sum(int(r[f"{p}_assertions"]) for r in rs)
    out["both_supported"] = sum(B(r["D_supported"]) and B(r["S_supported"]) for r in rs)
    out["only_D_supported"] = sum(B(r["D_supported"]) and not B(r["S_supported"]) for r in rs)
    out["only_S_supported"] = sum(B(r["S_supported"]) and not B(r["D_supported"]) for r in rs)
    out["neither_supported"] = sum(not B(r["D_supported"]) and not B(r["S_supported"]) for r in rs)
    return out
res = {"all": block(rows)}
for arm in ("corpus", "mqt"): res[arm] = block([r for r in rows if r["arm"] == arm])
for cert in ("True", "False"):
    res[f"issued_by_D={cert}"] = block([r for r in rows if r["certified_by_D"] == cert])
for inside in ("True", "False"):
    res[f"witness_in_S={inside}"] = block([r for r in rows if r["witness_in_S"] == inside])
res["witness_kinds_outside_S"] = dict(collections.Counter(f"{r['w_kind']} weight {bin(int(r['w_key'])).count('1') if r['w_key'] not in ('', 'None') else '-'}"
                                      for r in rows if r["witness_in_S"] == "False"))
orig = summ["original_validations"]
res["original_validations"] = {p: {"suites": sum(o["policy"] == p for o in orig), "fail_gt1": sum(o["policy"] == p and o["fails"] > 1 for o in orig),
                                   "fail_any": sum(o["policy"] == p and o["fails"] > 0 for o in orig), "seconds": round(sum(o["seconds"] for o in orig if o["policy"] == p), 1)}
                               for p in ("D", "S")}
res["cost"] = {"diagnosis_seconds_total": summ["diagnosis_seconds_total"], "reference_generation_seconds": summ["reference_generation_seconds"],
               "D_mutant_run_seconds": round(sum(float(r["D_mut_seconds"]) for r in rows), 1),
               "S_mutant_run_seconds": round(sum(float(r["S_mut_seconds"]) for r in rows), 1),
               "native_wall_seconds": summ["native_wall_seconds"], "executions": summ["executions"], "shots": summ["shots"]}
json.dump(res, open(sys.argv[3], "w"), indent=1)
print(json.dumps(res, indent=1))
