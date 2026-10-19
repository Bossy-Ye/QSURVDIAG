"""Recompute the results of the output-condition, combined-suite, all-pairs and QED-C experiments, and the
circuit-level view of the matched changes, from their per-run records and compare them with expected/experiments_expected.csv. No native execution.

Usage: python3 -I scripts/reproduce_experiments.py [--out DIR] [--analytic PY QUTEST_TREE QEDC_REF]

--analytic also reruns data/qedc/report.py and x_selection_check.py with the interpreter of environment/setup.sh.
Exits non-zero on any mismatch.
"""
import argparse, collections, csv, filecmp, json, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OC, CMP = ROOT / "data/output_condition", ROOT / "data/combined_suite"
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "output" / "experiments"))
ap.add_argument("--analytic", nargs=3, metavar=("PY", "TREE", "QEDC_REF")); a = ap.parse_args()
OUT = Path(a.out).resolve(); OUT.mkdir(parents=True, exist_ok=True)
if ROOT / "data" in OUT.parents:
    sys.exit("refusing to write inside data/")
rows = lambda p: list(csv.DictReader(open(p)))
got, notes = {}, []
def py(*args):
    r = subprocess.run([sys.executable, "-I", "-B", *map(str, args)], capture_output=True, text=True, cwd=ROOT)
    if r.returncode: sys.exit(f"failed: {' '.join(map(str, args))}\n{r.stdout}{r.stderr}")
    return r.stdout
def same_json(p, q): return json.load(open(p)) == json.load(open(q))
fmt_row = lambda t: f"{t['newly_killed']}/{t['lost_kills']}/{t['effect_pp']}/{t['cluster_ci95_pp']}/{t['loco_range_pp']}"

# ---------------------------------------------------------------- output-condition experiment
py(OC / "oc_analyze.py", ROOT, "-", OUT / "oc_recorded.json")
py(OC / "oc_analyze.py", ROOT, OC / "OC_RUNS.csv", OUT / "oc_corrected.json")
got["R-OC00"] = f"{same_json(OUT / 'oc_recorded.json', OC / 'OC_RECORDED_REPRODUCTION.json')}/{same_json(OUT / 'oc_corrected.json', OC / 'OC_RESULTS.json')}"
oc = json.load(open(OUT / "oc_corrected.json")); rec = json.load(open(OUT / "oc_recorded.json"))
c, r = oc["corrected"], rec["recorded"]
got["R-OC01"] = fmt_row(c["table5_row"])
got["R-OC02"] = f"{c['table5_row']['pairs']}/{c['table5_row']['clusters']}/{c['table5_row']['exact_mcnemar_p']:.1e}"
t = c["figure_4b_totals"]
got["R-OC03"] = f"{t['suite_omissions_killed']}/{t['suite_omissions']}; {t['observation_limitations_killed']}/{t['observation_limitations']}"
fc = c["figure_4b_cases"]
got["R-OC04"] = "/".join(str(fc.get(f"CL4|{f}|KILLED", 0)) for f in ("ghz", "simon", "qft"))
g = oc["guards"]; got["R-OC06"] = f"{len(g)} subjects, {sum(x['fails'] for x in g.values())} failures, {sum(x['unsupported'] for x in g.values())} errors in {sum(x['runs'] for x in g.values())} runs"
run = rows(OC / "OC_RUNS.csv"); kills = collections.Counter(); nrun = collections.Counter()
for x in run:
    if x["kind"] == "mutant": nrun[x["case"]] += 1; kills[x["case"]] += x["verdict"] == "KILLED"
native = {k: "KILLED" if kills[k] == nrun[k] else ("SURVIVED" if kills[k] == 0 else "SPLIT") for k in nrun}
cw = rows(OC / "OC_CASEWISE.csv")
got["R-OC07"] = f"{len(nrun)} pairs, {sum(nrun.values())} mutant runs; native {sum(native[x['mutant_id']] == x['native'] for x in cw)}/{len(cw)} recounted; agree {sum(x['agree'] == 'True' for x in cw)}/{len(cw)}"
got["R-OC08"] = ",".join(sorted(x["mutant_id"] for x in cw if x["subject"] == "simon_4" and x["baseline_report"] == "CL4" and native[x["mutant_id"]] == "SURVIVED"))

# ---------------------------------------------------------------- circuit-level view of the matched changes
got["R-CL00"] = str(py(ROOT / "data/checks/circuit_level.py", ROOT) == (ROOT / "data/checks/circuit_level.out").read_text())

# ---------------------------------------------------------------- repair comparison
py(CMP / "cmp_analyze.py", CMP / "CMP_CASES.csv", CMP / "CMP_SUMMARY.json", OUT / "cmp_results.json")
got["R-CM00"] = str(same_json(OUT / "cmp_results.json", CMP / "CMP_RESULTS.json"))
cases = rows(CMP / "CMP_CASES.csv"); nr = rows(CMP / "CMP_NATIVE_RUNS.csv")
mk, ok = collections.Counter(), collections.Counter()
for x in nr:
    if x["role"] in ("D_mut", "S_mut"): mk[(x["key"], x["role"][0])] += x["verdict"] == "KILLED"
    else: ok[(x["key"], x["role"][0])] += x["verdict"] == "KILLED"
okey = lambda r, p: json.dumps([r["program"], p, r[f"{p}_suite_id"]])
got["R-CM01"] = (f"{len(cases)} cases; recounted from per-run records: mutant kills {sum(int(r[f'{p}_mut_kills']) == mk[(r['case'], p)] for r in cases for p in 'DS')}/{2 * len(cases)}, "
                 f"original failures {sum(int(r[f'{p}_orig_fails']) == ok[(okey(r, p), p)] for r in cases for p in 'DS')}/{2 * len(cases)}")
res = json.load(open(OUT / "cmp_results.json")); al = res["all"]
got["R-CM02"] = f"{al['D_supported']}/{al['S_supported']}"
got["R-CM03"] = f"{al['both_supported']}/{al['only_D_supported']}/{al['only_S_supported']}/{al['neither_supported']}"
wi, wo = res["witness_in_S=True"], res["witness_in_S=False"]
got["R-CM04"] = f"{wi['cases']}/{wo['cases']}"
got["R-CM05"] = f"{wi['D_mutant_12of12']}/{wi['S_mutant_12of12']}; {wi['D_linked_original_fail_gt1']}/{wi['S_linked_original_fail_gt1']}; {wi['D_supported']}/{wi['S_supported']}"
got["R-CM06"] = f"{wo['D_mutant_12of12']}/{wo['S_mutant_12of12']}; S never {wo['S_mutant_0']}; {wo['D_linked_original_fail_gt1']}/{wo['S_linked_original_fail_gt1']}; {wo['D_supported']}/{wo['S_supported']}"
iss, wh = res["issued_by_D=True"], res["issued_by_D=False"]
got["R-CM07"] = f"{iss['D_supported']}/{iss['cases']}; {wh['D_supported']}/{wh['cases']}"
uns = [r for r in cases if r["certified_by_D"] == "True" and r["D_supported"] != "True"]
got["R-CM08"] = f"{sum(int(r['D_mut_kills']) < 12 for r in uns)} fewer than 12 kills; {sum(int(r['D_orig_fails']) > 1 for r in uns)} original fails >1"
near = [r for r in cases if float(r["w_d"]) - 0.05 < 0.01]
got["R-CM09"] = f"{len(near)}/{sum(r['D_supported'] == 'True' for r in near)}/{sum(r['S_supported'] == 'True' for r in near)}"
so = [r for r in cases if r["S_supported"] == "True" and r["D_supported"] != "True"]
got["R-CM10"] = f"{len(so)}/{all(float(r['w_d']) - 0.05 < 0.05 for r in so)}"
k = res["witness_kinds_outside_S"]
got["R-CM11"] = f"{sum(v for x, v in k.items() if x.startswith('zmask'))}/{k.get('entropy weight -', 0)}/{k.get('hellinger weight -', 0)}"
ov = res["original_validations"]
got["R-CM12"] = f"{ov['D']['suites']}/{ov['S']['suites']}; {al['D_assertions_total']}/{al['S_assertions_total']}; {sum(x['role'] == 'D_mut' for x in nr)}/{sum(x['role'] == 'S_mut' for x in nr)}"
got["R-CM13"] = f"{res['cost']['diagnosis_seconds_total']:.1f}"

# ---------------------------------------------------------------- QED-C workflow case
E = ROOT / "data/qedc"
nat = {(x["pair"], x["n"], x["run"], x["seed"]): x["verdict"] for x in rows(E / "NATIVE_RUNS.csv")}
xv3 = {(x["pair"], x["n"], x["run"], x["seed"]): x["verdict"] for x in rows(ROOT / "data/certification/witness_order/QEDC_X_RUNS.csv")}
assert not set(xv3) & set(nat); nat.update(xv3)                     # the n = 2 statistic of the closed witness order
ra = rows(E / "REANALYSIS_RUNS.csv")
T = {(x["pair"], x["n"], x["run"], x["seed"]): x for x in ra if x["predicate"] == "T"}
Tp = {(x["pair"], x["n"], x["run"], x["seed"]): x for x in ra if x["predicate"] == "Tprime"}
got["R-E200"] = f"{len(T)} histograms; re-run T verdicts differing from the archived: {sum(nat[k] != v['verdict'] for k, v in T.items())}"
got["R-E201"] = f"{sum(T[k]['verdict'] == Tp[k]['verdict'] for k in T)}/{len(T)}; max |dH| {max(abs(float(T[k]['hellinger']) - float(Tp[k]['hellinger'])) for k in T):.1e}"
K = lambda pair, n, run, src: sum(v["verdict"] == "KILLED" if isinstance(v, dict) else v == "KILLED" for kk, v in src.items() if kk[:3] == (pair, str(n), run))
W = range(2, 9)
got["R-E202"] = " ".join(str(K("constructed", n, "A_orig_cert", Tp)) for n in W) + " | " + " ".join(str(K("constructed", n, "A_orig_val", Tp)) for n in W)
got["R-E203"] = ",".join(str(n) for n in W if K("constructed", n, "A_orig_cert", Tp) <= 1 and K("natural", n, "A_orig_cert", Tp) <= 1)
got["R-E204"] = " ".join(f"{K('constructed', n, 'X_mut_val', nat)}/{K('constructed', n, 'X_orig_val', nat)}" for n in W)
got["R-E205"] = " ".join(f"{K(p, n, 'A_mut_cert', Tp)}/{K(p, n, 'A_mut_val', Tp)}" for p in ("constructed", "natural") for n in (2, 3, 4))
got["R-E206"] = " ".join(str(K(p, n, "B_mut_val", nat)) for p in ("constructed", "natural") for n in (2, 3, 4))
xs = lambda n, run: str(K("natural", n, run, nat)) if any(kk[:3] == ("natural", str(n), run) for kk in nat) else "-"
got["R-E207"] = " ".join(f"{xs(n, 'X_mut_cert')}/{xs(n, 'X_mut_val')}/{xs(n, 'X_orig_val')}" for n in W)
rep = rows(E / "REPORT.csv")
got["R-E208"] = " ".join(f"{x['pair'][0]}{x['n']}:{x['reported'].split(' (')[0]}" for x in rep)
got["R-E209"] = ",".join(str(n) for n in W if xs(n, "X_mut_val") == "12" and xs(n, "X_orig_val") in ("0", "1"))
got["R-E210"] = " ".join(str(K("natural", n, "A_mut_cert", Tp)) for n in range(5, 9))

# ---------------------------------------------------------------- all-pairs comparison
import gzip
AP = ROOT / "data/all_pairs"
py(AP / "allpairs_analyze.py", AP, OUT / "ALLPAIRS_RESULTS.json")
got["R-AP00"] = str(same_json(OUT / "ALLPAIRS_RESULTS.json", AP / "ALLPAIRS_RESULTS.json"))
ap = json.load(open(OUT / "ALLPAIRS_RESULTS.json")); g_ = ap["groups"]; a_ = g_["all"]
ck = ap["checks"]; ct = ap["containment"]
got["R-AP01"] = f"{ck['executions']}/{ck['cli_equals_inproc']}/{ck['assertions_cli_equal_inproc_equal_rescored']}/{ck['values_agree']}/{ck['histogram_identity_violations']}"
got["R-AP02"] = f"{ct['same_histogram']}/{ct['paired_runs']}; {ct['witness_status_equal']}/{ct['witness_in_A_runs']}; D kill without A kill {ct['D_kill_without_A_kill']}"
got["R-AP03"] = f"{a_['D_supported']}/{a_['A_supported']}"
got["R-AP04"] = f"{a_['both_supported']}/{a_['only_D_supported']}/{a_['only_A_supported']}/{a_['neither_supported']}"
got["R-AP05"] = f"{g_['witness_in_A']['cases']}/{g_['witness_outside_A']['cases']}; in A {g_['witness_in_A']['D_supported']}/{g_['witness_in_A']['A_supported']}; outside {g_['witness_outside_A']['D_supported']}/{g_['witness_outside_A']['A_supported']}, A never kills {g_['witness_outside_A']['A_mutant_0']}"
got["R-AP06"] = f"{g_['issued']['D_supported']}/{g_['issued']['A_supported']} of {g_['issued']['cases']}; {g_['withheld']['D_supported']}/{g_['withheld']['A_supported']} of {g_['withheld']['cases']}"
got["R-AP07"] = f"{a_['D_mutant_12of12']}/{a_['A_mutant_12of12']}; original fails >1 {a_['D_original_fail_gt1']}/{a_['A_original_fail_gt1']}; tool errors {a_['D_unsupported_runs'] + a_['A_unsupported_runs']}"
got["R-AP08"] = f"{g_['near_threshold']['cases']}/{g_['near_threshold']['D_supported']}/{g_['near_threshold']['A_supported']}"
got["R-AP09"] = f"{a_['S8_derived_supported']}"
got["R-AP10"] = f"{g_['corpus']['D_supported']}/{g_['corpus']['A_supported']} of {g_['corpus']['cases']}; {g_['mqt']['D_supported']}/{g_['mqt']['A_supported']} of {g_['mqt']['cases']}"
sem = json.load(open(AP / "ALLPAIRS_SEMANTIC.json"))["rows"]
got["R-AP11"] = f"{sum(r['n'] + 1 for r in sem)}/{sum(r['n'] + r['n'] * (r['n'] - 1) // 2 for r in sem)}; max {max(r['A_assertions'] for r in sem)}"
co = ap["cost"]
got["R-AP12"] = f"{co['distinct_mutant_histograms']}+{co['distinct_original_histograms']}; executions {co['native_executions']['D']}/{co['native_executions']['A']}; eval {co['assertion_evaluation_seconds']['D']:.0f}/{co['assertion_evaluation_seconds']['A']:.0f} s"
hist = {}
with gzip.open(AP / "ALLPAIRS_HISTOGRAMS.jsonl.gz", "rt") as f:
    for line in f: x = json.loads(line); hist[x["hist_id"]] = sum(x["counts"].values())
ref_ids = {x["hist_id"] for x in rows(AP / "ALLPAIRS_NATIVE_RUNS.csv")}
got["R-AP13"] = f"{len(ref_ids - set(hist))} missing; {sum(v != 8000 for v in hist.values())} not 8000 shots; {len(hist)} archived"

# ---------------------------------------------------------------- closed witness order (v3)
WO = ROOT / "data/certification/witness_order"
py(WO / "audit.py", ROOT, OUT / "IMPACT.csv")
got["R-V301"] = str(filecmp.cmp(OUT / "IMPACT.csv", WO / "IMPACT.csv", shallow=False))
n3 = rows(WO / "NATIVE_RUNS.csv")
got["R-V302"] = " ".join(f"{x['job_id']}:{x['guard_fails']}/{x['kills']}/{x['status']}" for x in n3)
got["R-V303"] = " ".join(f"{t}:{sum(v == 'KILLED' for k, v in xv3.items() if k[2] == t)}/{sum(1 for k in xv3 if k[2] == t)}"
                         for t in ("X_mut_cert", "X_orig_guard", "X_orig_val", "X_mut_val"))

# ---------------------------------------------------------------- analytic tier (optional)
if a.analytic:
    PY, TREE, REFP = a.analytic
    tmp = OUT / "qedc_rerun"; tmp.mkdir(exist_ok=True)
    for f in ("CASE_RESULTS.json", "NATIVE_RUNS.csv", "REANALYSIS_RUNS.csv"): shutil.copy(E / f, tmp / f)
    r1 = subprocess.run([PY, "-I", "-B", str(E / "report.py"), str(ROOT), TREE, REFP, str(tmp)], capture_output=True, text=True)
    got["R-A01"] = str(r1.returncode == 0 and filecmp.cmp(tmp / "REPORT.csv", E / "REPORT.csv", shallow=False))
    r2 = subprocess.run([PY, "-I", "-B", str(E / "x_selection_check.py"), str(ROOT), TREE, REFP, str(tmp)], capture_output=True, text=True)
    got["R-A02"] = str(r2.returncode == 0 and r2.stdout == (E / "x_selection_check.out").read_text())

# ---------------------------------------------------------------- compare
out, cnt = [], collections.Counter()
for e in rows(ROOT / "expected/experiments_expected.csv"):
    v = got.get(e["check_id"])
    st = ("NOT RUN (analytic tier)" if e["check_id"].startswith("R-A") and not a.analytic else "NOT REPRODUCIBLE") if v is None else \
         ("MISMATCH" if v != e["expected"] else ("PARTIAL" if e["evidence_level"].startswith("archived") else "MATCH"))
    cnt[st] += 1; out.append({**e, "reproduced": v, "status": st})
with open(OUT / "experiments_verification.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for o in out:
    if o["status"] in ("MISMATCH", "NOT REPRODUCIBLE"): print(f"{o['check_id']}: expected {o['expected']!r}, got {o['reproduced']!r}")
print(f"experiment checks: {len(out)}  " + "  ".join(f"{k}: {v}" for k, v in sorted(cnt.items())))
print("Full table: " + str(OUT / "experiments_verification.csv"))
sys.exit(1 if cnt["MISMATCH"] or cnt["NOT REPRODUCIBLE"] else 0)
