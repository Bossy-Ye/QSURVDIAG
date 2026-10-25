"""Analysis of the all-pairs comparison (plan: PLAN.md). Standard library only.
Usage: python3 -I allpairs_analyze.py <allpairs dir> <out json>
Reads ALLPAIRS_SEMANTIC.json, ALLPAIRS_NATIVE_RUNS.csv and ALLPAIRS_SUMMARY.json, and the cases whose repairs the v3
amendment issues (../certification/witness_order/IMPACT.csv). Applies the support rule and the
original-validity gate, checks execution consistency, histogram identity and containment, and derives the
adjacent-pair suite's verdicts from the per-assertion results of the native A executions (labeled as derived).
"""
import csv, json, sys, collections
from pathlib import Path

D_ = Path(sys.argv[1]); OUTP = sys.argv[2]; R = 12; THETA = 0.05
rows = json.load(open(D_ / "ALLPAIRS_SEMANTIC.json"))["rows"]
summ = json.load(open(D_ / "ALLPAIRS_SUMMARY.json"))
V3 = {(r["population"], k) for r in csv.DictReader(open(D_.parent / "certification/witness_order/IMPACT.csv")) for k in r["changed"].split(";") if k}
for r in rows: r["issued"] = r["issued"] or (r["arm"], r["case"]) in V3     # issued under the final rules
runs = collections.defaultdict(list)
for x in csv.DictReader(open(D_ / "ALLPAIRS_NATIVE_RUNS.csv")): runs[(x["key"], x["role"])].append(x)
for v in runs.values(): v.sort(key=lambda x: int(x["seed"]))

checks = collections.Counter()
for v in runs.values():
    for x in v:
        checks["executions"] += 1
        checks["cli_equals_inproc"] += x["verdict"] == x["inproc_verdict"]
        checks["assertions_cli_equal_inproc_equal_rescored"] += x["cli_assertions"] == x["inproc_assertions"] == x["rescored_assertions"]
        checks["values_agree"] += x["values_agree"] == "True"
        checks["verdict_consistent_with_assertions"] += x["verdict"] == ("UNSUPPORTED" if "E" in x["cli_assertions"] else ("KILLED" if "F" in x["cli_assertions"] else "SURVIVED"))
checks["histogram_identity_violations"] = len(summ["histogram_identity_violations"])

def pair_index(n):                    # position of every assertion in A: marginals 0..n-1, then pairs (i, j), i < j
    idx, k = {}, n
    for i in range(n):
        for j in range(i + 1, n): idx[(i, j)] = k; k += 1
    return idx
def s_positions(n): ix = pair_index(n); return list(range(n)) + [ix[(i, i + 1)] for i in range(n - 1)]
K = lambda v: sum(x["verdict"] == "KILLED" for x in v); U = lambda v: sum(x["verdict"] == "UNSUPPORTED" for x in v)
def derived_kills(v, pos): return sum(any(x["cli_assertions"][p] == "F" for p in pos) for x in v)

cases = []
contain = collections.Counter()
for r in rows:
    n = r["n"]; c = dict(r)
    for pol in ("D", "A"):
        mv = runs[(r["case"], f"{pol}_mut")]; ov = runs[(json.dumps([r["program"], pol, r[f"{pol}_suite_id"]]), f"{pol}_orig")]
        assert len(mv) == R and len(ov) == R, (r["case"], pol)
        c[f"{pol}_mut_kills"], c[f"{pol}_mut_unsupported"] = K(mv), U(mv)
        c[f"{pol}_orig_fails"], c[f"{pol}_orig_unsupported"] = K(ov), U(ov)
        c[f"{pol}_original_valid"] = K(ov) <= 1 and not U(ov)                       # the original-validity gate
        c[f"{pol}_supported"] = c[f"{pol}_original_valid"] and K(mv) == R and not U(mv)
        c[f"{pol}_reason"] = ("supported" if c[f"{pol}_supported"] else
                              "tool error" if U(mv) or U(ov) else
                              f"original fails {K(ov)} of 12" if K(ov) > 1 else f"mutant killed in {K(mv)} of 12")
    # adjacent-pair suite S, derived from the per-assertion results of the native A executions (not a native S run)
    am = runs[(r["case"], "A_mut")]; ao = runs[(json.dumps([r["program"], "A", r["A_suite_id"]]), "A_orig")]
    sp = s_positions(n); c["S8_mut_kills"] = derived_kills(am, sp); c["S8_orig_fails"] = derived_kills(ao, sp)
    c["S8_supported"] = c["S8_mut_kills"] == R and c["S8_orig_fails"] <= 1 and not U(am) and not U(ao)
    # containment: identical histograms, D's assertions are A's assertions -> per-run statuses must coincide
    dm = runs[(r["case"], "D_mut")]
    for x, y in zip(dm, am):
        contain["paired_runs"] += 1; contain["same_histogram"] += x["hist_id"] == y["hist_id"]
        contain["baseline_statuses_equal"] += x["cli_assertions"][:n] == y["cli_assertions"][:n]
        if r["witness_in_A"]:
            i, j = [q for q in range(n) if (r["w_key"] >> q) & 1]
            contain["witness_in_A_runs"] += 1
            contain["witness_status_equal"] += x["cli_assertions"][n] == y["cli_assertions"][pair_index(n)[(i, j)]]
            contain["D_kill_without_A_kill"] += x["verdict"] == "KILLED" and y["verdict"] != "KILLED"
    cases.append(c)

def block(cs):
    out = {"cases": len(cs), "programs": len({c["program"] for c in cs}), "D_designs": len({c["D_suite_id"] for c in cs})}
    for p in ("D", "A"):
        out[f"{p}_mutant_12of12"] = sum(c[f"{p}_mut_kills"] == R for c in cs)
        out[f"{p}_mutant_0"] = sum(c[f"{p}_mut_kills"] == 0 for c in cs)
        out[f"{p}_original_fail_gt1"] = sum(c[f"{p}_orig_fails"] > 1 for c in cs)
        out[f"{p}_unsupported_runs"] = sum(c[f"{p}_mut_unsupported"] + c[f"{p}_orig_unsupported"] for c in cs)
        out[f"{p}_supported"] = sum(c[f"{p}_supported"] for c in cs)
    out["both_supported"] = sum(c["D_supported"] and c["A_supported"] for c in cs)
    out["only_D_supported"] = sum(c["D_supported"] and not c["A_supported"] for c in cs)
    out["only_A_supported"] = sum(c["A_supported"] and not c["D_supported"] for c in cs)
    out["neither_supported"] = sum(not c["D_supported"] and not c["A_supported"] for c in cs)
    out["S8_derived_supported"] = sum(c["S8_supported"] for c in cs)
    out["S8_derived_mutant_12of12"] = sum(c["S8_mut_kills"] == R for c in cs)
    out["S8_derived_original_fail_gt1"] = sum(c["S8_orig_fails"] > 1 for c in cs)
    return out
G = {"all": cases, "corpus": [c for c in cases if c["arm"] == "corpus"], "mqt": [c for c in cases if c["arm"] == "mqt"],
     "issued": [c for c in cases if c["issued"]], "withheld": [c for c in cases if not c["issued"]],
     "witness_in_A": [c for c in cases if c["witness_in_A"]], "witness_outside_A": [c for c in cases if not c["witness_in_A"]],
     "near_threshold": [c for c in cases if c["w_d"] - THETA < 0.01]}
res = {"checks": dict(checks), "containment": dict(contain), "groups": {k: block(v) for k, v in G.items()}}
res["reasons"] = {p: dict(collections.Counter(c[f"{p}_reason"].split(" of")[0] if "of" in c[f"{p}_reason"] else c[f"{p}_reason"] for c in cases)) for p in ("D", "A")}
res["outside_A_witness_kinds"] = dict(collections.Counter(f"{c['w_kind']} weight {bin(c['w_key']).count('1')}" if c["w_kind"] == "zmask" else c["w_kind"] for c in G["witness_outside_A"]))
res["A_only_cases"] = [{k: c[k] for k in ("case", "arm", "n", "w_kind", "w_key", "w_d", "D_mut_kills", "D_orig_fails", "A_mut_kills", "A_orig_fails")} for c in cases if c["A_supported"] and not c["D_supported"]]
res["D_only_cases"] = [{k: c[k] for k in ("case", "arm", "n", "w_kind", "w_key", "w_d", "witness_in_A", "D_mut_kills", "D_orig_fails", "A_mut_kills", "A_orig_fails")} for c in cases if c["D_supported"] and not c["A_supported"]]
# cost, under one reuse policy: every assertion of a run reads that run's histogram
ev = collections.defaultdict(float); ex = collections.Counter(); cli = collections.defaultdict(float)
for (k, role), v in runs.items():
    p = role[0]; ex[p] += len(v); ev[p] += sum(float(x["eval_seconds"]) for x in v); cli[p] += sum(float(x["cli_seconds"]) for x in v)
orig_hist = {(json.loads(k)[0], x["seed"]) for (k, role), v in runs.items() if role.endswith("_orig") for x in v}
res["cost"] = {"diagnosis_seconds_total": summ["diagnosis_seconds_total"], "reference_generation_seconds": summ["reference_generation_seconds"],
               "native_executions": dict(ex), "shots_per_execution": summ["settings"]["N"], "total_shots": summ["shots"],
               "assertion_evaluation_seconds": {p: round(ev[p], 2) for p in ev}, "native_run_seconds_summed": {p: round(cli[p], 1) for p in cli},
               "distinct_logical_suites": {"D": len({c["D_suite_id"] for c in cases}), "A": len({c["A_suite_id"] for c in cases})},
               "native_original_validation_executions": {p: sum(len(v) for (k, role), v in runs.items() if role == f"{p}_orig") for p in "DA"},
               "distinct_original_histograms": len(orig_hist),
               "distinct_mutant_histograms": len({(k, x["seed"]) for (k, role), v in runs.items() if role.endswith("_mut") for x in v}),
               "native_wall_seconds": summ["native_wall_seconds"]}
json.dump(res, open(OUTP, "w"), indent=1)
with open(Path(OUTP).with_name("ALLPAIRS_CASES.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(cases[0]), lineterminator="\n"); w.writeheader(); w.writerows(cases)
print(json.dumps({"checks": res["checks"], "containment": res["containment"], "all": res["groups"]["all"]}, indent=1))
