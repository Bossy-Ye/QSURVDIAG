"""Recompute the results of the output-condition, combined-suite, all-pairs, QED-C, separating-setting, later-position
and developer-suite experiments, and the circuit-level view of the matched changes, from their per-run records and
compare them with expected/experiments_expected.csv. No native execution.

Usage: python3 -I scripts/reproduce_experiments.py [--out DIR] [--analytic PY R2V_TREE QEDC_REF]

--analytic also reruns data/qedc/report.py, x_selection_check.py and the re-analyses with the interpreter of
environment/setup.sh.
Exits non-zero on any mismatch.
"""
import argparse, collections, csv, filecmp, gzip, json, os, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OC, CMP = ROOT / "data/output_condition", ROOT / "data/combined_suite"
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "output" / "experiments"))
ap.add_argument("--analytic", nargs=3, metavar=("PY", "R2V_TREE", "QEDC_REF")); a = ap.parse_args()
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

# ---------------------------------------------------------------- separating settings (observation change)
os.environ["QSD_OUT"] = str(OUT)
OB = ROOT / "data/observation_change"
py(OB / "x1_analyze.py")
got["R-X100"] = f"{same_json(OUT / 'observation_change/X1_SUMMARY.json', OB / 'X1_SUMMARY.json')}/{filecmp.cmp(OUT / 'observation_change/X1_NATIVE_RUNS.csv', OB / 'X1_NATIVE_RUNS.csv', shallow=False)}/{json.load(open(OUT / 'observation_change/X1_QEDC_BY_WIDTH.json')) == json.load(open(OB / 'X1_QEDC_SUMMARY.json'))['by_width']}"
x1 = json.load(open(OUT / "observation_change/X1_SUMMARY.json")); x1r = rows(OUT / "observation_change/X1_NATIVE_RUNS.csv")
got["R-X101"] = f"{x1['supported']}/{x1['pairs']}; original failures {x1['original_failures_total']} of {12 * x1['pairs']}; control kills {x1['control_kills_total']} of {12 * x1['pairs']}; {x1['executions']} executions"
got["R-X102"] = " ".join(f"{k}:{v}" for k, v in sorted(x1["by_rotated_qubits"].items(), key=lambda t: int(t[0]))) + "; " + \
                " ".join(f"{k}:{sum(r['witness_kind'] == k for r in x1r)}" for k in ("marginal", "zmask"))
nprog = {r["program"]: int(r["n"]) for r in x1r}
got["R-X103"] = f"{sum(x1['distinct_settings_per_program'].values())} settings over {len(nprog)} circuits; {sum(3 ** n - 1 for n in nprog.values())} other than all-Z; smallest witness difference {min(float(r['witness_d']) for r in x1r):.3f}"
qw = json.load(open(OUT / "observation_change/X1_QEDC_BY_WIDTH.json"))
xp = json.load(open(OUT / "observation_change/X1_POSITION_SUMMARY.json"))
got["R-X105"] = (f"{same_json(OUT / 'observation_change/X1_POSITION_SUMMARY.json', OB / 'X1_POSITION_SUMMARY.json')}/"
                 f"{filecmp.cmp(OUT / 'observation_change/X1_POSITION_NATIVE_RUNS.csv', OB / 'X1_POSITION_NATIVE_RUNS.csv', shallow=False)}; "
                 f"{xp['supported']}/{xp['pairs']} supported (" + " ".join(f"{k}:{v}" for k, v in xp["supported_by_population"].items()) +
                 f"); original failures {xp['original_failures_total']} of {12 * xp['pairs']}; control kills {xp['control_kills_total']}")
def _evaluated(s):                                     # position of a setting in the search order of x1_settings.py
    import itertools, math
    n = len(s); S = tuple(i for i, c in enumerate(s) if c != "Z"); k = len(S)
    return (sum(math.comb(n, j) * 2 ** j for j in range(1, k)) + list(itertools.combinations(range(n), k)).index(S) * 2 ** k
            + list(itertools.product("XY", repeat=k)).index(tuple(s[i] for i in S)) + 1)
ev20 = sorted(_evaluated(r["setting_q0_first"]) for r in x1r)
evp = sorted(int(r["settings_evaluated"]) for r in rows(OB / "X1_POSITION_SETTINGS.csv"))
assert all(_evaluated(r["setting_q0_first"]) == int(r["settings_evaluated"]) for r in rows(OB / "X1_POSITION_SETTINGS.csv"))
got["R-X106"] = (f"settings evaluated: 20 circuits median {ev20[len(ev20) // 2]}, max {ev20[-1]}; later positions median {evp[len(evp) // 2]}, "
                 f"max {evp[-1]}; rotated qubits " + " ".join(f"{k}:{v}" for k, v in xp["by_rotated_qubits"].items()))
py(OB / "x1_transition.py", "analyze")
xt = json.load(open(OUT / "observation_change/X1_TRANSITION_SUMMARY.json"))
got["R-X107"] = (f"{same_json(OUT / 'observation_change/X1_TRANSITION_SUMMARY.json', OB / 'X1_TRANSITION_SUMMARY.json')}/"
                 f"{filecmp.cmp(OUT / 'observation_change/X1_TRANSITION.csv', OB / 'X1_TRANSITION.csv', shallow=False)}; "
                 f"candidates " + " ".join(f"{k}:{v}" for k, v in sorted(xt["candidates"].items())) +
                 f"; named witness {xt['witness_is_named']}; undecided {xt['undecided_instances_total']}; control kills "
                 f"{xt['control_kills_total']} of {12 * xt['pairs']}; guard failures {xt['guard_failures_total']}; "
                 f"certified {xt['certified']}/{xt['pairs']}")
got["R-X104"] = " ".join(f"{n}:{v['mutant_kills']}/{v['original_failures']}/{v['control_kills']}" for n, v in sorted(qw.items(), key=lambda t: int(t[0])))

# ---------------------------------------------------------------- later positions
PO = ROOT / "data/position"
py(PO / "x4_analyze.py")
got["R-X400"] = f"{filecmp.cmp(OUT / 'position/X4_FINAL.csv', PO / 'X4_FINAL.csv', shallow=False)}/{filecmp.cmp(OUT / 'position/X4_NATIVE_RUNS.csv', PO / 'X4_NATIVE_RUNS.csv', shallow=False)}/{same_json(OUT / 'position/X4_SUMMARY.json', PO / 'X4_SUMMARY.json')}"
x4 = rows(OUT / "position/X4_FINAL.csv")
cnt = lambda P, rep: sum(r["report"] == rep for r in P)
surv = [r for r in x4 if r["native_verdict"] != "KILLED"]
got["R-X401"] = f"{len(x4)} pairs, {len(surv)} survivors; OL {cnt(x4, 'CL3')}, SO {cnt(x4, 'CL4')}, unresolved {cnt(x4, 'Unresolved')}; OL sites {len({(r['subject'], r['anchor_index']) for r in x4 if r['report'] == 'CL3'})}, SO sites {len({(r['subject'], r['anchor_index']) for r in x4 if r['report'] == 'CL4'})}"
oth = [r for r in x4 if r["population"] == "other"]
got["R-X402"] = f"OL {cnt(oth, 'CL3')} in {','.join(sorted({r['subject'] for r in oth if r['report'] == 'CL3'}))} ({sum(r['report'] == 'CL3' and r['third'] == 'middle' for r in oth)} middle, {sum(r['report'] == 'CL3' and r['third'] == 'last' for r in oth)} last); SO {cnt(oth, 'CL4')} at {len({(r['subject'], r['anchor_index']) for r in oth if r['report'] == 'CL4'})} sites"
ext = [r for r in x4 if r["population"] == "external"]; mq = [r for r in x4 if r["population"] == "mqt"]
got["R-X403"] = f"external OL {cnt(ext, 'CL3')} in {len({r['subject'] for r in ext if r['report'] == 'CL3'})} programs, qft_n4 {sum(r['report'] == 'CL3' and r['subject'] == 'qft_n4' for r in ext)}; MQT OL {cnt(mq, 'CL3')} in {','.join(sorted({r['subject'] for r in mq if r['report'] == 'CL3'}))}"
gd = json.load(open(PO / "X4_GUARDS.json"))
got["R-X404"] = f"{len(gd)} programs; guards clean {sum(g['guard_ok'] for g in gd.values())}; original failures {sum(g['fails'] for g in gd.values())} in {sum(len(g['verdicts']) for g in gd.values())} runs"

# ---------------------------------------------------------------- developer-written suites (QuCheck case studies)
DS = ROOT / "data/developer_suites"
py(DS / "x2_analyze.py"); py(DS / "x2_q3_analyze.py")
got["R-X200"] = "/".join(str(filecmp.cmp(OUT / "developer_suites" / f, DS / f, shallow=False)) for f in ("X2_DIAGNOSIS.csv", "X2_NATIVE_RUNS.csv", "X2_QUCHECK_20.csv")) + \
                "/" + "/".join(str(same_json(OUT / "developer_suites" / f, DS / f)) for f in ("X2_SUMMARY.json", "X2_Q3_SUMMARY.json"))
x2 = rows(OUT / "developer_suites/X2_DIAGNOSIS.csv")
def x2_suite(s):
    R = [r for r in x2 if r["suite"] == s]; sv = [r for r in R if r["outcome"] != "killed"]
    n = lambda o: sum(r["outcome"] == o for r in R)
    return (f"{len(R)} mutants, {len(sv)} survivors; CE {n('contract equivalence')}, EIE {n('executed-input equality')}, "
            f"OL {n('observation limitation')}, SO {n('suite omission')}, unresolved {sum(r['outcome'].startswith('unresolved') for r in R)}")
got["R-X201"] = x2_suite("A") + "; OL in " + ",".join(sorted({r["program"] for r in x2 if r["outcome"] == "observation limitation"}))
got["R-X202"] = x2_suite("B")
xs = json.load(open(OUT / "developer_suites/X2_SUMMARY.json"))
un = [r for r in x2 if r["outcome"].startswith("unresolved")]
emsplit = {(r["suite"], r["program"]) for r in un if r["label"] == "em" and r["outcome"] == "unresolved: split verdict"}
got["R-X203"] = (f"unresolved {len(un)}, split {sum(r['outcome'] == 'unresolved: split verdict' for r in un)}, em {sum(r['label'] == 'em' for r in un)}; "
                 f"suites with em splits {len(emsplit)}, of which failing the original in guard runs {sum(xs['guard_failures'][f'{s}:{p}'] > 0 for s, p in emsplit)}")
ol = {(r["program"], r["mutant"]) for r in x2 if r["outcome"] == "observation limitation"}
killed_b = sum(r["suite"] == "B" and (r["program"], r["mutant"]) in ol and r["outcome"] == "killed" for r in x2)
ce = collections.Counter((r["program"], r["mutant"], r["label"], r["contract_equivalent_F"]) for r in x2)
lab = {(p, m): (l, e) for p, m, l, e in ce}
got["R-X204"] = (f"property tests kill {killed_b} of {len(ol)} observation limitations; labels agree "
                 f"{sum((l == 'em') == (e == 'True') for l, e in lab.values())}/{len(lab)}; exception "
                 + ",".join(f"{p}:{m}" for (p, m), (l, e) in sorted(lab.items()) if (l == 'em') != (e == 'True')))
got["R-X205"] = f"{sum(r['outcome'] == 'executed-input equality' for r in x2)} executed-input equalities"
q3 = json.load(open(OUT / "developer_suites/X2_Q3_SUMMARY.json"))
qc, qt, ct = q3["only_qucheck"], q3["only_qutest"], q3["controls"]
got["R-X206"] = (f"only QuCheck {qc['detected_12_of_12']}/{qc['pairs']} detected in 12 of 12 (Holm {qc['holm_detected_12_of_12']}); "
                 f"only QUTest {qt['detected_12_of_12']}/{qt['pairs']} (never {qt['detected_0_of_12']}); "
                 f"controls {ct['false_detections']} and {ct['false_detections_holm']} with Holm of {ct['runs']}")
tw, tn = q3["transfer_WITNESS_EXISTS"], q3["transfer_NO_WITNESS_ABOVE_THETA"]
xc = json.load(open(DS / "X2_CONTROL.json"))
got["R-X208"] = " ".join(f"{k}: control {v['control']['kind']}:{v['control']['key']}@{v['control']['context']}, mutant kills {v['mutant_kills']}, "
                         f"original failures {v['original_failures']}" for k, v in sorted(xc.items()))
got["R-X207"] = f"transfer with witness {tw['detected_12_of_12']}/{tw['pairs']}; without {tn['detected_0_of_12']} never, {tn['split']} split of {tn['pairs']}"

# ---------------------------------------------------------------- re-analyses (archived outputs; rerun in the analytic tier)
RA = ROOT / "data/reanalysis"
r156 = json.load(open(RA / "R156_SUMMARY.json")); r1, r5, r6 = r156["R1"], r156["R5"]["corpus"], r156["R6"]
got["R-X500"] = (f"{r1['candidates']} candidates, {r1['issued']} issued, precision {r1['precision']}, recall {r1['recall']}, withheld {r1['withheld']}, "
                 f"unsupported withheld {r1['candidates'] - r1['witness_suite_reliable'] - (r1['issued'] - r1['issued_and_reliable'])} of {r1['candidates'] - r1['witness_suite_reliable']}")
got["R-X501"] = "corpus score " + " ".join(f"{100 * r5[k][2]:.1f}" for k in ("raw", "without_equivalents", "without_equivalents_and_observation_limitations")) + \
                "; " + " ".join(f"{k}:{r6[k]['distinct_final_states']}/{r6[k]['distinct_sites']}" for k in ("CL3", "CL4"))
r3 = json.load(open(RA / "R3_REGISTER_CONTRACT.json"))["summary"]["by_report"]
r4 = json.load(open(RA / "R4_NOISE.json"))["summary"]
got["R-X502"] = (f"register contract: CL3 {r3['CL3']['equivalent_on_register']}/35, CL4 {r3['CL4']['equivalent_on_register']}/79; noise: SO witness above theta "
                 f"{r4['suite_omissions']['witness_still_above_theta']}/{r4['suite_omissions']['pairs']} (median ratio {r4['suite_omissions']['witness_ratio_median']:.2f}), "
                 f"OL below {r4['observation_limitations']['pairs'] - r4['observation_limitations']['separated_under_noise']}/{r4['observation_limitations']['pairs']}, "
                 f"largest OL difference {r4['observation_limitations']['largest_noisy_difference']:.4f}")

# ---------------------------------------------------------------- negative controls of the reported suite omissions
CO = ROOT / "data/certification/outcomes"
cd = [float(r["c_d"]) for p in ("PRIMARY", "EXTERNAL", "CORPUS", "WIDTH", "DEFECT")
      for r in rows(CO / f"R2V_FINAL_{p}.csv") if r["v2_report"] == "CL4"]
cd += [float(r["v3_d"]) for r in rows(ROOT / "data/certification/witness_order/CHANGES.csv")
       if r["selection"] == "control" and r["population"] in ("corpus", "defect")]
pos = [d for d in cd if d >= 1e-9]
got["R-NC01"] = f"{len(cd) - len(pos)}/{len(cd)} controls with difference 0; {len(pos)} positive, largest {max(pos):.4f}"

# ---------------------------------------------------------------- analytic tier (optional)
if a.analytic:
    PY, TREE, REFP = a.analytic
    tmp = OUT / "qedc_rerun"; tmp.mkdir(exist_ok=True)
    for f in ("CASE_RESULTS.json", "NATIVE_RUNS.csv", "REANALYSIS_RUNS.csv"): shutil.copy(E / f, tmp / f)
    r1 = subprocess.run([PY, "-I", "-B", str(E / "report.py"), str(ROOT), TREE, REFP, str(tmp)], capture_output=True, text=True)
    got["R-A01"] = str(r1.returncode == 0 and filecmp.cmp(tmp / "REPORT.csv", E / "REPORT.csv", shallow=False))
    r2 = subprocess.run([PY, "-I", "-B", str(E / "x_selection_check.py"), str(ROOT), TREE, REFP, str(tmp)], capture_output=True, text=True)
    got["R-A02"] = str(r2.returncode == 0 and r2.stdout == (E / "x_selection_check.out").read_text())
    env = {**os.environ, "QSD_OUT": str(OUT / "analytic")}
    for k, f, j in (("R-A10", "r156.py", "R156_SUMMARY.json"), ("R-A11", "r3_register_contract.py", "R3_REGISTER_CONTRACT.json"), ("R-A12", "r4_noise.py", "R4_NOISE.json")):
        r = subprocess.run([PY, "-I", "-B", str(RA / f)], capture_output=True, text=True, env=env)
        got[k] = str(r.returncode == 0 and same_json(OUT / "analytic/reanalysis" / j, RA / j))
    OB = ROOT / "data/observation_change"
    r = subprocess.run([PY, "-I", "-B", str(OB / "x1_settings.py")], capture_output=True, text=True, env=env)
    got["R-A13"] = str(r.returncode == 0 and filecmp.cmp(OUT / "analytic/observation_change/X1_SETTINGS.csv", OB / "X1_SETTINGS.csv", shallow=False))
    r = subprocess.run([PY, "-I", "-B", str(OB / "x1_transition.py"), "stage2", "primary"], capture_output=True, text=True, env=env)
    nos = lambda P: [{k: v for k, v in x.items() if k != "search_seconds"} for x in P]
    got["R-A15"] = str(r.returncode == 0 and nos(rows(OUT / "analytic/observation_change/X1_TRANSITION_STAGE2.csv"))
                       == nos(x for x in rows(OB / "X1_TRANSITION_STAGE2.csv") if x["arm"] == "primary"))
    r = subprocess.run([PY, "-I", "-B", str(OB / "x1_qedc_setting.py")], capture_output=True, text=True, env=env)
    got["R-A14"] = " ".join(f"{l.split()[0]}:{l.split()[1]}/{l.split()[3]} {l.split()[4]}/{l.split()[5]}" for l in r.stdout.splitlines() if l[:1].isdigit())

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
