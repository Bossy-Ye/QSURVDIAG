"""Recompute the checks of expected/experiments.csv from the per-run records of each experiment, by rerunning
the archived analysis scripts and recounting their inputs. Nothing is executed natively. Writes
<out>/experiments/.

--analytic also reruns the analyses that need the analytic environment (environment/setup.sh): the QED-C
report, the three analyses of data/analyses/ and the separating-setting searches. A mismatch gives a non-zero
exit status."""

import argparse, collections, csv, filecmp, gzip, itertools, json, math, os, re, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from paths import ROOT, output

DATA = ROOT / "data"
OUTPUT_CONDITION = DATA / "output_condition"
COMBINED = DATA / "combined_suite"
QEDC = DATA / "qedc"
ALL_PAIRS = DATA / "all_pairs"
OUTCOMES = DATA / "certification/outcomes"
WITNESS_ORDER = DATA / "certification/witness_order"
SETTINGS = DATA / "observation_change"
POSITION = DATA / "position"
SUITES = DATA / "developer_suites"
ANALYSES = DATA / "analyses"
CIRCUIT_LEVEL = DATA / "checks/circuit_level"
MQT_CASES = DATA / "prospective/mqt_bench/records/analysis/PASS3C_CASES.csv"

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--out", default=ROOT / "output", help="output directory (default: output/ in the package)")
ap.add_argument(
    "--analytic",
    nargs=3,
    metavar=("PYTHON", "INPUT_TREE", "QEDC_REFERENCE"),
    help="interpreter of the analytic environment, <out>/analytic/r2v_root as reproduce_analytic.py writes "
    "it, and precalculated_data.json of the QED-C benchmarks",
)
args = ap.parse_args()
for path in args.analytic or ():
    if not Path(path).exists():
        sys.exit(f"--analytic: {path} does not exist")
OUT = output(args.out) / "experiments"
OUT.mkdir(exist_ok=True)
os.environ["QSD_OUT"] = str(OUT)
got = {}


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def load(path):
    with open(path) as f:
        return json.load(f)


def same_json(p, q):
    return load(p) == load(q)


def same_file(p, q):
    return filecmp.cmp(p, q, shallow=False)


def rerun(*command):
    command = [sys.executable, "-I", "-B", *map(str, command)]
    r = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        sys.exit(f"failed: {' '.join(command[3:])}\n{r.stdout}{r.stderr}")
    return r.stdout


def spread(counts, key=None):
    return " ".join(f"{k}:{v}" for k, v in sorted(counts.items(), key=key))


for runs, name in (("-", "recorded"), (OUTPUT_CONDITION / "NATIVE_RUNS.csv", "corrected")):
    rerun(OUTPUT_CONDITION / "analyze.py", ROOT, runs, OUT / f"output_condition_{name}.json")
got["R-OC00"] = (
    f"{same_json(OUT / 'output_condition_recorded.json', OUTPUT_CONDITION / 'RECORDED_REPRODUCTION.json')}/"
    f"{same_json(OUT / 'output_condition_corrected.json', OUTPUT_CONDITION / 'RESULTS.json')}"
)
analysis = load(OUT / "output_condition_corrected.json")
row = analysis["corrected"]["table5_row"]
got["R-OC01"] = (
    f"{row['newly_killed']}/{row['lost_kills']}/{row['effect_pp']}/{row['cluster_ci95_pp']}/"
    f"{row['loco_range_pp']}"
)
got["R-OC02"] = f"{row['pairs']}/{row['clusters']}/{row['exact_mcnemar_p']:.1e}"
totals = analysis["corrected"]["figure_4b_totals"]
got["R-OC03"] = (
    f"{totals['suite_omissions_killed']}/{totals['suite_omissions']}; "
    f"{totals['observation_limitations_killed']}/{totals['observation_limitations']}"
)
by_family = analysis["corrected"]["figure_4b_cases"]
got["R-OC04"] = "/".join(str(by_family.get(f"CL4|{f}|KILLED", 0)) for f in ("ghz", "simon", "qft"))
guards = analysis["guards"].values()
got["R-OC06"] = (
    f"{len(guards)} subjects, {sum(g['fails'] for g in guards)} failures, "
    f"{sum(g['unsupported'] for g in guards)} errors in {sum(g['runs'] for g in guards)} runs"
)
kills, runs = collections.Counter(), collections.Counter()
for r in rows(OUTPUT_CONDITION / "NATIVE_RUNS.csv"):
    if r["kind"] == "mutant":
        runs[r["case"]] += 1
        kills[r["case"]] += r["verdict"] == "KILLED"
native = {k: "KILLED" if kills[k] == runs[k] else "SURVIVED" if kills[k] == 0 else "SPLIT" for k in runs}
cases = rows(OUTPUT_CONDITION / "CASES.csv")
got["R-OC07"] = (
    f"{len(runs)} pairs, {sum(runs.values())} mutant runs; "
    f"native {sum(native[r['mutant_id']] == r['native'] for r in cases)}/{len(cases)} recounted; "
    f"agree {sum(r['agree'] == 'True' for r in cases)}/{len(cases)}"
)
got["R-OC08"] = ",".join(
    sorted(
        r["mutant_id"]
        for r in cases
        if (r["subject"], r["baseline_report"], native[r["mutant_id"]]) == ("simon_4", "CL4", "SURVIVED")
    )
)

got["R-CL00"] = str(rerun(f"{CIRCUIT_LEVEL}.py", ROOT) == Path(f"{CIRCUIT_LEVEL}.out").read_text())

# D is the witness suite and S the combined suite, as in the records.
rerun(
    COMBINED / "analyze.py", COMBINED / "CASES.csv", COMBINED / "SUMMARY.json", OUT / "combined_results.json"
)
got["R-CM00"] = str(same_json(OUT / "combined_results.json", COMBINED / "RESULTS.json"))
cases = rows(COMBINED / "CASES.csv")
suite_runs = rows(COMBINED / "NATIVE_RUNS.csv")
mutant_kills, original_fails = collections.Counter(), collections.Counter()
for r in suite_runs:
    count = mutant_kills if r["role"] in ("D_mut", "S_mut") else original_fails
    count[(r["key"], r["role"][0])] += r["verdict"] == "KILLED"
original_key = lambda r, suite: json.dumps([r["program"], suite, r[f"{suite}_suite_id"]])
got["R-CM01"] = (
    f"{len(cases)} cases; recounted from per-run records: mutant kills "
    f"{sum(int(r[f'{s}_mut_kills']) == mutant_kills[(r['case'], s)] for r in cases for s in 'DS')}/"
    f"{2 * len(cases)}, "
    f"original failures "
    f"{sum(int(r[f'{s}_orig_fails']) == original_fails[(original_key(r, s), s)] for r in cases for s in 'DS')}/{2 * len(cases)}"
)
combined = load(OUT / "combined_results.json")
overall = combined["all"]
got["R-CM02"] = f"{overall['D_supported']}/{overall['S_supported']}"
got["R-CM03"] = (
    f"{overall['both_supported']}/{overall['only_D_supported']}/{overall['only_S_supported']}/"
    f"{overall['neither_supported']}"
)
inside, outside = combined["witness_in_S=True"], combined["witness_in_S=False"]
got["R-CM04"] = f"{inside['cases']}/{outside['cases']}"
got["R-CM05"] = (
    f"{inside['D_mutant_12of12']}/{inside['S_mutant_12of12']}; "
    f"{inside['D_linked_original_fail_gt1']}/{inside['S_linked_original_fail_gt1']}; "
    f"{inside['D_supported']}/{inside['S_supported']}"
)
got["R-CM06"] = (
    f"{outside['D_mutant_12of12']}/{outside['S_mutant_12of12']}; S never {outside['S_mutant_0']}; "
    f"{outside['D_linked_original_fail_gt1']}/{outside['S_linked_original_fail_gt1']}; "
    f"{outside['D_supported']}/{outside['S_supported']}"
)
issued, withheld = combined["issued_by_D=True"], combined["issued_by_D=False"]
got["R-CM07"] = f"{issued['D_supported']}/{issued['cases']}; {withheld['D_supported']}/{withheld['cases']}"
unsupported = [r for r in cases if r["certified_by_D"] == "True" and r["D_supported"] != "True"]
got["R-CM08"] = (
    f"{sum(int(r['D_mut_kills']) < 12 for r in unsupported)} fewer than 12 kills; "
    f"{sum(int(r['D_orig_fails']) > 1 for r in unsupported)} original fails >1"
)
near = [r for r in cases if float(r["w_d"]) - 0.05 < 0.01]
got["R-CM09"] = (
    f"{len(near)}/{sum(r['D_supported'] == 'True' for r in near)}/"
    f"{sum(r['S_supported'] == 'True' for r in near)}"
)
only_combined = [r for r in cases if r["S_supported"] == "True" and r["D_supported"] != "True"]
got["R-CM10"] = f"{len(only_combined)}/{all(float(r['w_d']) - 0.05 < 0.05 for r in only_combined)}"
kinds = combined["witness_kinds_outside_S"]
got["R-CM11"] = (
    f"{sum(v for k, v in kinds.items() if k.startswith('zmask'))}/{kinds.get('entropy weight -', 0)}/"
    f"{kinds.get('hellinger weight -', 0)}"
)
validations = combined["original_validations"]
got["R-CM12"] = (
    f"{validations['D']['suites']}/{validations['S']['suites']}; "
    f"{overall['D_assertions_total']}/{overall['S_assertions_total']}; "
    f"{sum(r['role'] == 'D_mut' for r in suite_runs)}/{sum(r['role'] == 'S_mut' for r in suite_runs)}"
)
got["R-CM13"] = f"{combined['cost']['diagnosis_seconds_total']:.1f}"

# QED-C runs are keyed by pair, width, run and seed. T is the stored-reference rule, Tprime the Hellinger one.
run_key = lambda r: (r["pair"], r["n"], r["run"], r["seed"])
verdicts = {run_key(r): r["verdict"] for r in rows(QEDC / "NATIVE_RUNS.csv")}
x_runs = {run_key(r): r["verdict"] for r in rows(WITNESS_ORDER / "QEDC_X_RUNS.csv")}
if set(x_runs) & set(verdicts):
    sys.exit("QEDC_X_RUNS.csv repeats runs of data/qedc/NATIVE_RUNS.csv")
verdicts.update(x_runs)
comparison = rows(QEDC / "BASELINE_COMPARISON_RUNS.csv")
stored = {run_key(r): r for r in comparison if r["predicate"] == "T"}
baseline = {run_key(r): r["verdict"] for r in comparison if r["predicate"] == "Tprime"}
hellinger = {run_key(r): float(r["hellinger"]) for r in comparison if r["predicate"] == "Tprime"}
got["R-QC00"] = (
    f"{len(stored)} histograms; re-run T verdicts differing from the archived: "
    f"{sum(verdicts[k] != r['verdict'] for k, r in stored.items())}"
)
got["R-QC01"] = (
    f"{sum(r['verdict'] == baseline[k] for k, r in stored.items())}/{len(stored)}; "
    f"max |dH| {max(abs(float(r['hellinger']) - hellinger[k]) for k, r in stored.items()):.1e}"
)
killed = lambda pair, n, run, source: sum(
    v == "KILLED" for k, v in source.items() if k[:3] == (pair, str(n), run)
)
WIDTHS = range(2, 9)
PAIRS = ("constructed", "natural")
got["R-QC02"] = (
    " ".join(str(killed("constructed", n, "A_orig_cert", baseline)) for n in WIDTHS)
    + " | "
    + " ".join(str(killed("constructed", n, "A_orig_val", baseline)) for n in WIDTHS)
)
got["R-QC03"] = ",".join(
    str(n) for n in WIDTHS if all(killed(pair, n, "A_orig_cert", baseline) <= 1 for pair in PAIRS)
)
got["R-QC04"] = " ".join(
    f"{killed('constructed', n, 'X_mut_val', verdicts)}/{killed('constructed', n, 'X_orig_val', verdicts)}"
    for n in WIDTHS
)
got["R-QC05"] = " ".join(
    f"{killed(pair, n, 'A_mut_cert', baseline)}/{killed(pair, n, 'A_mut_val', baseline)}"
    for pair in PAIRS
    for n in (2, 3, 4)
)
got["R-QC06"] = " ".join(str(killed(pair, n, "B_mut_val", verdicts)) for pair in PAIRS for n in (2, 3, 4))
ran = lambda n, run: any(k[:3] == ("natural", str(n), run) for k in verdicts)
natural = lambda n, run: str(killed("natural", n, run, verdicts)) if ran(n, run) else "-"
got["R-QC07"] = " ".join(
    f"{natural(n, 'X_mut_cert')}/{natural(n, 'X_mut_val')}/{natural(n, 'X_orig_val')}" for n in WIDTHS
)
got["R-QC08"] = " ".join(
    f"{r['pair'][0]}{r['n']}:{r['reported'].split(' (')[0]}" for r in rows(QEDC / "REPORT.csv")
)
got["R-QC09"] = ",".join(
    str(n) for n in WIDTHS if natural(n, "X_mut_val") == "12" and natural(n, "X_orig_val") in ("0", "1")
)
got["R-QC10"] = " ".join(str(killed("natural", n, "A_mut_cert", baseline)) for n in range(5, 9))

# D is the witness suite and A the all-pairs suite, as in the records.
rerun(ALL_PAIRS / "allpairs_analyze.py", ALL_PAIRS, OUT / "ALLPAIRS_RESULTS.json")
got["R-AP00"] = str(same_json(OUT / "ALLPAIRS_RESULTS.json", ALL_PAIRS / "ALLPAIRS_RESULTS.json"))
all_pairs = load(OUT / "ALLPAIRS_RESULTS.json")
groups, checks, containment, cost = (all_pairs[k] for k in ("groups", "checks", "containment", "cost"))
overall = groups["all"]
got["R-AP01"] = (
    f"{checks['executions']}/{checks['cli_equals_inproc']}/"
    f"{checks['assertions_cli_equal_inproc_equal_rescored']}/"
    f"{checks['values_agree']}/{checks['histogram_identity_violations']}"
)
got["R-AP02"] = (
    f"{containment['same_histogram']}/{containment['paired_runs']}; "
    f"{containment['witness_status_equal']}/{containment['witness_in_A_runs']}; "
    f"D kill without A kill {containment['D_kill_without_A_kill']}"
)
got["R-AP03"] = f"{overall['D_supported']}/{overall['A_supported']}"
got["R-AP04"] = (
    f"{overall['both_supported']}/{overall['only_D_supported']}/{overall['only_A_supported']}/"
    f"{overall['neither_supported']}"
)
supported = lambda group: f"{groups[group]['D_supported']}/{groups[group]['A_supported']}"
got["R-AP05"] = (
    f"{groups['witness_in_A']['cases']}/{groups['witness_outside_A']['cases']}; in A "
    f"{supported('witness_in_A')}; "
    f"outside {supported('witness_outside_A')}, A never kills {groups['witness_outside_A']['A_mutant_0']}"
)
got["R-AP06"] = (
    f"{supported('issued')} of {groups['issued']['cases']}; {supported('withheld')} of "
    f"{groups['withheld']['cases']}"
)
got["R-AP07"] = (
    f"{overall['D_mutant_12of12']}/{overall['A_mutant_12of12']}; "
    f"original fails >1 {overall['D_original_fail_gt1']}/{overall['A_original_fail_gt1']}; "
    f"tool errors {overall['D_unsupported_runs'] + overall['A_unsupported_runs']}"
)
got["R-AP08"] = f"{groups['near_threshold']['cases']}/{supported('near_threshold')}"
got["R-AP09"] = f"{overall['S8_derived_supported']}"
got["R-AP10"] = (
    f"{supported('corpus')} of {groups['corpus']['cases']}; {supported('mqt')} of {groups['mqt']['cases']}"
)
semantic = load(ALL_PAIRS / "ALLPAIRS_SEMANTIC.json")["rows"]
got["R-AP11"] = (
    f"{sum(r['n'] + 1 for r in semantic)}/{sum(r['n'] + r['n'] * (r['n'] - 1) // 2 for r in semantic)}; "
    f"max {max(r['A_assertions'] for r in semantic)}"
)
got["R-AP12"] = (
    f"{cost['distinct_mutant_histograms']}+{cost['distinct_original_histograms']}; "
    f"executions {cost['native_executions']['D']}/{cost['native_executions']['A']}; "
    f"eval {cost['assertion_evaluation_seconds']['D']:.0f}/{cost['assertion_evaluation_seconds']['A']:.0f} s"
)
with gzip.open(ALL_PAIRS / "ALLPAIRS_HISTOGRAMS.jsonl.gz", "rt") as f:
    shots = {h["hist_id"]: sum(h["counts"].values()) for h in map(json.loads, f)}
used = {r["hist_id"] for r in rows(ALL_PAIRS / "ALLPAIRS_NATIVE_RUNS.csv")}
got["R-AP13"] = (
    f"{len(used - set(shots))} missing; {sum(n != 8000 for n in shots.values())} not 8000 shots; "
    f"{len(shots)} archived"
)
# The closed witness order reports these cases, which the outcome records list as withdrawn.
closed = {
    (r["population"], case)
    for r in rows(WITNESS_ORDER / "IMPACT.csv")
    for case in r["changed"].split(";")
    if case
}
repairs = collections.defaultdict(list)
for r in rows(ALL_PAIRS / "ALLPAIRS_CASES.csv"):
    if r["issued"] == "True" or (r["arm"], r["case"]) in closed:
        repairs[(r["arm"], r["program"])].append(r["D_supported"] == "True")
got["R-AP14"] = f"{len(repairs)}/{sum(map(all, repairs.values()))}"


def witnesses(population):
    return [
        (r["w_kind"], r["w_key"])
        for r in rows(OUTCOMES / f"R2V_FINAL_{population.upper()}.csv")
        if r["v2_report"] == "CL4" or (population, r["case_key"]) in closed
    ]


# Width-set records repeat corpus pairs: their witnesses are checked and not counted.
reported = [w for population in ("primary", "corpus", "external", "defect") for w in witnesses(population)]
reported += [(r["w_kind"], r["w_key"]) for r in rows(POSITION / "outcomes.csv") if r["report"] == "CL4"]
reported += [(r["witness_kind"], r["witness_key"]) for r in rows(MQT_CASES) if r["v2_report"] == "CL4"]
single_qubit = sum(
    kind == "zmask" and bin(int(key.split()[-1])).count("1") == 1
    for kind, key in reported + witnesses("width")
)
got["R-WI01"] = f"{len(reported)}/{single_qubit}"

rerun(WITNESS_ORDER / "audit.py", ROOT, OUT / "IMPACT.csv")
got["R-WO01"] = str(same_file(OUT / "IMPACT.csv", WITNESS_ORDER / "IMPACT.csv"))
got["R-WO02"] = " ".join(
    f"{r['job_id']}:{r['guard_fails']}/{r['kills']}/{r['status']}" for r in rows(WITNESS_ORDER / "NATIVE_RUNS.csv")
)
got["R-WO03"] = " ".join(
    f"{run}:{sum(v == 'KILLED' for k, v in x_runs.items() if k[2] == run)}/{sum(k[2] == run for k in x_runs)}"
    for run in ("X_mut_cert", "X_orig_guard", "X_orig_val", "X_mut_val")
)

rerun(SETTINGS / "analyze.py")
RERUN = OUT / "observation_change"
got["R-SS00"] = (
    f"{same_json(RERUN / 'summary.json', SETTINGS / 'summary.json')}/"
    f"{same_file(RERUN / 'native_runs.csv', SETTINGS / 'native_runs.csv')}/"
    f"{load(RERUN / 'qedc_by_width.json') == load(SETTINGS / 'qedc_summary.json')['by_width']}"
)
settings = load(RERUN / "summary.json")
setting_runs = rows(RERUN / "native_runs.csv")
qedc_widths = load(RERUN / "qedc_by_width.json")
got["R-SS01"] = (
    f"{settings['supported']}/{settings['pairs']}; "
    f"original failures {settings['original_failures_total']} of {12 * settings['pairs']}; "
    f"control kills {settings['control_kills_total']} of {12 * settings['pairs']}; {settings['executions']} "
    f"executions"
)
got["R-SS02"] = (
    spread(settings["by_rotated_qubits"], key=lambda t: int(t[0]))
    + "; "
    + " ".join(f"{k}:{sum(r['witness_kind'] == k for r in setting_runs)}" for k in ("marginal", "zmask"))
)
qubits = {r["program"]: int(r["n"]) for r in setting_runs}
got["R-SS03"] = (
    f"{sum(settings['distinct_settings_per_program'].values())} settings over {len(qubits)} circuits; "
    f"{sum(3 ** n - 1 for n in qubits.values())} other than all-Z; "
    f"smallest witness difference {min(float(r['witness_d']) for r in setting_runs):.3f}"
)
later = load(RERUN / "later_positions_summary.json")
later_settings = rows(SETTINGS / "later_positions_settings.csv")
got["R-SS05"] = (
    f"{same_json(RERUN / 'later_positions_summary.json', SETTINGS / 'later_positions_summary.json')}/"
    f"{same_file(RERUN / 'later_positions_native_runs.csv', SETTINGS / 'later_positions_native_runs.csv')}; "
    f"{later['supported']}/{later['pairs']} supported ("
    + " ".join(f"{k}:{v}" for k, v in later["supported_by_population"].items())
    + f"); original failures {later['original_failures_total']} of {12 * later['pairs']}; "
    f"control kills {later['control_kills_total']}"
)


def search_position(setting):
    """Number of settings that find_settings.py evaluates up to this one: fewest rotated qubits first."""
    n = len(setting)
    rotated = tuple(i for i, basis in enumerate(setting) if basis != "Z")
    k = len(rotated)
    return (
        sum(math.comb(n, j) * 2**j for j in range(1, k))
        + list(itertools.combinations(range(n), k)).index(rotated) * 2**k
        + list(itertools.product("XY", repeat=k)).index(tuple(setting[i] for i in rotated))
        + 1
    )


evaluated = sorted(search_position(r["setting_q0_first"]) for r in setting_runs)
evaluated_later = sorted(int(r["settings_evaluated"]) for r in later_settings)
if any(search_position(r["setting_q0_first"]) != int(r["settings_evaluated"]) for r in later_settings):
    sys.exit("later_positions_settings.csv: settings_evaluated differs from the search order")
got["R-SS06"] = (
    f"settings evaluated: 20 circuits median {evaluated[len(evaluated) // 2]}, max {evaluated[-1]}; "
    f"later positions median {evaluated_later[len(evaluated_later) // 2]}, max {evaluated_later[-1]}; "
    f"rotated qubits " + " ".join(f"{k}:{v}" for k, v in later["by_rotated_qubits"].items())
)
two_state = rows(SETTINGS / "two_basis_states.csv")
named = {r["pair"]: r["setting_q0_first"] for r in setting_runs + later_settings}
if len(two_state) != 100 or any(named[r["pair"]] != r["named_setting"] for r in two_state):
    sys.exit("two_basis_states.csv does not list the named settings of the 100 observation limitations")
two = [r for r in two_state if r["basis_states"] == "2"]
more = [r for r in two_state if r["basis_states"] != "2"]
simon = [r for r in two_state if r["program"] == "simon_4"]
simon_more = [r for r in more if r["program"] == "simon_4"]
other_more = [r for r in more if r["program"] != "simon_4"]
multiplier = [r for r in two if r["program"] == "rg_mult_12"]
rotated = lambda setting: {i for i, basis in enumerate(setting) if basis != "Z"}
separating = lambda rs: sum(r["separates"] == "True" for r in rs)
sizes = lambda rs, column: sorted({len(rotated(r[column])) for r in rs})
got["R-SS08"] = (
    f"two basis states: {sum(r['is_named'] == 'True' for r in two)}/{len(two)} named X, same qubits "
    f"{sum(rotated(r['named_setting']) == rotated(r['x_on_superposed']) for r in two)}/{len(two)}, at most "
    f"one Y "
    f"{sum(r['named_setting'].count('Y') <= 1 for r in two)}/{len(two)}, multiplier pairs "
    f"{len(multiplier)} with {sizes(multiplier, 'x_on_superposed')} qubits, "
    f"{sorted({int(r['settings_evaluated']) for r in later_settings if r['program'] == 'rg_mult_12'})} "
    f"evaluated; "
    f"X on superposed separates {separating(two_state)}/{len(two_state)}: "
    f"{' '.join(sorted({r['program'].split('_')[0] for r in other_more}))} "
    f"{separating(other_more)}/{len(other_more)}, Simon {separating(simon_more)}/{len(simon)} "
    f"(named rotate {sizes(simon, 'named_setting')} of {sizes(simon, 'x_on_superposed')})"
)


def inverse_test_shots(fidelity, runs=12):
    """Fewest shots at which every one of the runs holds a failed shot with probability at least 0.95."""
    shots = 1
    while (1 - fidelity**shots) ** runs < 0.95:
        shots += 1
    return shots


primary = rows(OUTCOMES / "R2V_FINAL_PRIMARY.csv")
needed = {
    report: [
        inverse_test_shots((1 - float(r["margin_state"])) ** 2) for r in primary if r["v2_report"] == report
    ]
    for report in ("CL3", "CL4")
}
equivalent = [r for r in primary if r["v2_report"] == "CL1"]
got["R-SS09"] = (
    " ".join(f"{k}:{len(v)} max {max(v)} median {sorted(v)[len(v) // 2]}" for k, v in needed.items())
    + f"; contract equivalences with a different state {sum(float(r['margin_state']) > 1e-9 for r in equivalent)}"
    f"/{len(equivalent)}"
)
rerun(SETTINGS / "rotated_profile.py", "analyze")
refinement = load(RERUN / "rotated_profile_summary.json")
got["R-SS07"] = (
    f"{same_json(RERUN / 'rotated_profile_summary.json', SETTINGS / 'rotated_profile_summary.json')}/"
    f"{same_file(RERUN / 'rotated_profile.csv', SETTINGS / 'rotated_profile.csv')}; "
    f"candidates {spread(refinement['candidates'])}; separating-setting witness "
    f"{refinement['witness_is_named']}; "
    f"undecided {refinement['undecided_instances_total']}; control kills "
    f"{refinement['control_kills_total']} of {12 * refinement['pairs']}; "
    f"guard failures {refinement['guard_failures_total']}; certified {refinement['certified']}/"
    f"{refinement['pairs']}"
)
got["R-SS04"] = " ".join(
    f"{n}:{v['mutant_kills']}/{v['original_failures']}/{v['control_kills']}"
    for n, v in sorted(qedc_widths.items(), key=lambda t: int(t[0]))
)

rerun(POSITION / "analyze.py")
RERUN = OUT / "position"
got["R-LP00"] = (
    f"{same_file(RERUN / 'outcomes.csv', POSITION / 'outcomes.csv')}/"
    f"{same_file(RERUN / 'native_runs.csv', POSITION / 'native_runs.csv')}/"
    f"{same_json(RERUN / 'summary.json', POSITION / 'summary.json')}"
)
positions = rows(RERUN / "outcomes.csv")
count = lambda rs, report: sum(r["report"] == report for r in rs)
with_report = lambda rs, report: [r for r in rs if r["report"] == report]
sites = lambda rs, report: len({(r["subject"], r["anchor_index"]) for r in with_report(rs, report)})
subjects = lambda rs, report: sorted({r["subject"] for r in with_report(rs, report)})
got["R-LP01"] = (
    f"{len(positions)} pairs, {sum(r['native_verdict'] != 'KILLED' for r in positions)} survivors; "
    f"OL {count(positions, 'CL3')}, SO {count(positions, 'CL4')}, unresolved "
    f"{count(positions, 'Unresolved')}; "
    f"OL sites {sites(positions, 'CL3')}, SO sites {sites(positions, 'CL4')}"
)
other, external, mqt = ([r for r in positions if r["population"] == p] for p in ("other", "external", "mqt"))
got["R-LP02"] = (
    f"OL {count(other, 'CL3')} in {','.join(subjects(other, 'CL3'))} "
    f"({sum(r['third'] == 'middle' for r in with_report(other, 'CL3'))} middle, "
    f"{sum(r['third'] == 'last' for r in with_report(other, 'CL3'))} last); "
    f"SO {count(other, 'CL4')} at {sites(other, 'CL4')} sites"
)
got["R-LP03"] = (
    f"external OL {count(external, 'CL3')} in {len(subjects(external, 'CL3'))} programs, "
    f"qft_n4 {sum(r['subject'] == 'qft_n4' for r in with_report(external, 'CL3'))}; "
    f"MQT OL {count(mqt, 'CL3')} in {','.join(subjects(mqt, 'CL3'))}"
)
guards = load(POSITION / "guard_runs.json").values()
got["R-LP04"] = (
    f"{len(guards)} programs; guards clean {sum(g['guard_ok'] for g in guards)}; "
    f"original failures {sum(g['fails'] for g in guards)} in {sum(len(g['verdicts']) for g in guards)} runs"
)

# In the case studies, suite A holds the unit tests and suite B the property tests. The label em marks a
# mutant that its authors call semantics-preserving.
rerun(SUITES / "analyze.py")
rerun(SUITES / "compare_with_predictions.py")
RERUN = OUT / "developer_suites"
TABLES = ("diagnosis.csv", "native_runs.csv", "qucheck_on_20_circuits.csv")
got["R-DS00"] = "/".join(
    [str(same_file(RERUN / f, SUITES / f)) for f in TABLES]
    + [str(same_json(RERUN / f, SUITES / f)) for f in ("summary.json", "qucheck_vs_predictions.json")]
)
diagnoses = rows(RERUN / "diagnosis.csv")
outcome = lambda r, name: r["outcome"] == name


def suite_line(suite):
    rs = [r for r in diagnoses if r["suite"] == suite]
    n = lambda name: sum(outcome(r, name) for r in rs)
    return (
        f"{len(rs)} mutants, {len(rs) - n('killed')} survivors; CE {n('contract equivalence')}, "
        f"EIE {n('executed-input equality')}, OL {n('observation limitation')}, SO {n('suite omission')}, "
        f"unresolved {sum(r['outcome'].startswith('unresolved') for r in rs)}"
    )


ol = {(r["program"], r["mutant"]) for r in diagnoses if outcome(r, "observation limitation")}
got["R-DS01"] = suite_line("A") + "; OL in " + ",".join(sorted({program for program, _ in ol}))
got["R-DS02"] = suite_line("B")
guard_failures = load(RERUN / "summary.json")["guard_failures"]
unresolved = [r for r in diagnoses if r["outcome"].startswith("unresolved")]
split = [r for r in unresolved if outcome(r, "unresolved: split verdict")]
split_suites = {(r["suite"], r["program"]) for r in split if r["label"] == "em"}
got["R-DS03"] = (
    f"unresolved {len(unresolved)}, split {len(split)}, em {sum(r['label'] == 'em' for r in unresolved)}; "
    f"suites with em splits {len(split_suites)}, of which failing the original in guard runs "
    f"{sum(guard_failures[f'{suite}:{program}'] > 0 for suite, program in split_suites)}"
)
labels = {
    (program, mutant): (label == "em", equivalent == "True")
    for program, mutant, label, equivalent in dict.fromkeys(
        (r["program"], r["mutant"], r["label"], r["contract_equivalent_F"]) for r in diagnoses
    )
}
got["R-DS04"] = (
    f"property tests kill "
    f"{sum(r['suite'] == 'B' and (r['program'], r['mutant']) in ol and outcome(r, 'killed') for r in diagnoses)} "
    f"of {len(ol)} observation limitations; labels agree "
    f"{sum(label == equivalent for label, equivalent in labels.values())}/{len(labels)}; exception "
    + ",".join(f"{p}:{m}" for (p, m), (label, equivalent) in sorted(labels.items()) if label != equivalent)
)
got["R-DS05"] = f"{sum(outcome(r, 'executed-input equality') for r in diagnoses)} executed-input equalities"
qucheck = load(RERUN / "qucheck_vs_predictions.json")
only_qucheck, only_qutest, controls = qucheck["only_qucheck"], qucheck["only_qutest"], qucheck["controls"]
got["R-DS06"] = (
    f"only QuCheck {only_qucheck['detected_12_of_12']}/{only_qucheck['pairs']} detected in 12 of 12 "
    f"(Holm {only_qucheck['holm_detected_12_of_12']}); "
    f"only QUTest {only_qutest['detected_12_of_12']}/{only_qutest['pairs']} (never "
    f"{only_qutest['detected_0_of_12']}); "
    f"controls {controls['false_detections']} and {controls['false_detections_holm']} with Holm of "
    f"{controls['runs']}"
)
with_witness, without = qucheck["transfer_WITNESS_EXISTS"], qucheck["transfer_NO_WITNESS_ABOVE_THETA"]
got["R-DS08"] = " ".join(
    f"{k}: control {v['control']['kind']}:{v['control']['key']}@{v['control']['context']}, "
    f"mutant kills {v['mutant_kills']}, original failures {v['original_failures']}"
    for k, v in sorted(load(SUITES / "negative_controls.json").items())
)
got["R-DS07"] = (
    f"transfer with witness {with_witness['detected_12_of_12']}/{with_witness['pairs']}; "
    f"without {without['detected_0_of_12']} never, {without['split']} split of {without['pairs']}"
)

# Keys of requirements_scores_states.json: R1 requirements as a classifier, R5 mutation scores, R6 states.
scores = load(ANALYSES / "requirements_scores_states.json")
classifier, corpus_score, states = scores["R1"], scores["R5"]["corpus"], scores["R6"]
unreliable = classifier["candidates"] - classifier["witness_suite_reliable"]
got["R-AN00"] = (
    f"{classifier['candidates']} candidates, {classifier['issued']} issued, precision "
    f"{classifier['precision']}, "
    f"recall {classifier['recall']}, withheld {classifier['withheld']}, unsupported withheld "
    f"{unreliable - (classifier['issued'] - classifier['issued_and_reliable'])} of {unreliable}"
)
got["R-AN01"] = (
    "corpus score "
    + " ".join(
        f"{100 * corpus_score[k][2]:.1f}"
        for k in ("raw", "without_equivalents", "without_equivalents_and_observation_limitations")
    )
    + "; "
    + " ".join(f"{k}:{states[k]['distinct_final_states']}/{states[k]['distinct_sites']}" for k in ("CL3", "CL4"))
)
register = load(ANALYSES / "register_contracts.json")["summary"]["by_report"]
noise = load(ANALYSES / "noise.json")["summary"]
noisy_so, noisy_ol = noise["suite_omissions"], noise["observation_limitations"]
got["R-AN02"] = (
    f"register contract: CL3 {register['CL3']['equivalent_on_register']}/35, "
    f"CL4 {register['CL4']['equivalent_on_register']}/79; noise: SO witness above theta "
    f"{noisy_so['witness_still_above_theta']}/{noisy_so['pairs']} (median ratio "
    f"{noisy_so['witness_ratio_median']:.2f}), "
    f"OL below {noisy_ol['pairs'] - noisy_ol['separated_under_noise']}/{noisy_ol['pairs']}, "
    f"largest OL difference {noisy_ol['largest_noisy_difference']:.4f}"
)

control_d = [
    float(r["c_d"])
    for population in ("PRIMARY", "EXTERNAL", "CORPUS", "WIDTH", "DEFECT")
    for r in rows(OUTCOMES / f"R2V_FINAL_{population}.csv")
    if r["v2_report"] == "CL4"
]
control_d += [
    float(r["v3_d"])
    for r in rows(WITNESS_ORDER / "CHANGES.csv")
    if r["selection"] == "control" and r["population"] in ("corpus", "defect")
]
positive = [d for d in control_d if d >= 1e-9]
got["R-NC01"] = (
    f"{len(control_d) - len(positive)}/{len(control_d)} controls with difference 0; "
    f"{len(positive)} positive, largest {max(positive):.4f}"
)

if args.analytic:
    python, tree, reference = args.analytic
    environment = {**os.environ, "QSD_OUT": str(OUT / "analytic")}

    def analytic(script, *arguments, env=None):
        command = [python, "-I", "-B", str(script), *arguments]
        return subprocess.run(command, capture_output=True, text=True, env=env)

    qedc_rerun = OUT / "qedc_rerun"
    qedc_rerun.mkdir(exist_ok=True)
    for f in ("CASE_RESULTS.json", "NATIVE_RUNS.csv", "BASELINE_COMPARISON_RUNS.csv"):
        shutil.copy(QEDC / f, qedc_rerun / f)
    r = analytic(QEDC / "report.py", str(ROOT), tree, reference, str(qedc_rerun))
    got["R-A01"] = str(r.returncode == 0 and same_file(qedc_rerun / "REPORT.csv", QEDC / "REPORT.csv"))
    r = analytic(QEDC / "x_selection_check.py", str(ROOT), tree, reference, str(qedc_rerun))
    got["R-A02"] = str(r.returncode == 0 and r.stdout == (QEDC / "x_selection_check.out").read_text())
    for cid, name in (
        ("R-A10", "requirements_scores_states"),
        ("R-A11", "register_contracts"),
        ("R-A12", "noise"),
    ):
        r = analytic(ANALYSES / f"{name}.py", env=environment)
        got[cid] = str(
            r.returncode == 0 and same_json(OUT / "analytic/analyses" / f"{name}.json", ANALYSES / f"{name}.json")
        )
    RERUN = OUT / "analytic/observation_change"
    r = analytic(SETTINGS / "find_settings.py", env=environment)
    name = "separating_settings.csv"
    got["R-A13"] = str(r.returncode == 0 and same_file(RERUN / name, SETTINGS / name))
    r = analytic(SETTINGS / "rotated_profile.py", "stage2", "primary", env=environment)
    untimed = lambda rs: [{k: v for k, v in r.items() if k != "search_seconds"} for r in rs]
    got["R-A15"] = str(
        r.returncode == 0
        and untimed(rows(RERUN / "rotated_profile_stage2.csv"))
        == untimed(r for r in rows(SETTINGS / "rotated_profile_stage2.csv") if r["arm"] == "primary")
    )
    r = analytic(SETTINGS / "two_basis_states.py", env=environment)
    got["R-A16"] = str(
        r.returncode == 0
        and rows(RERUN / "two_basis_states.csv") == [r for r in two_state if r["population"] == "primary"]
    )
    r = analytic(SETTINGS / "qedc_setting.py", env=environment)
    got["R-A14"] = " ".join(
        "{0}:{1}/{3} {4}/{5}".format(*line.split()) for line in r.stdout.splitlines() if line[:1].isdigit()
    )


def status(check):
    value = got.get(check["check_id"])
    if value is None:
        analytic_only = re.fullmatch(r"R-A\d+", check["check_id"])
        return "ANALYTIC TIER" if analytic_only and not args.analytic else "NO VALUE"
    if value != check["expected"]:
        return "MISMATCH"
    return "PARTIAL" if check["evidence_level"].startswith("archived") else "MATCH"


table = [
    {**c, "reproduced": got.get(c["check_id"]), "status": status(c)}
    for c in rows(ROOT / "expected/experiments.csv")
]
with open(OUT / "experiments_verification.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(table[0]))
    w.writeheader()
    w.writerows(table)
failed = [r for r in table if r["status"] in ("MISMATCH", "NO VALUE")]
for r in failed:
    print(f"{r['check_id']}: expected {r['expected']!r}, got {r['reproduced']!r}")
tally = collections.Counter(r["status"] for r in table)
print(f"experiment checks: {len(table)}  " + "  ".join(f"{k}: {n}" for k, n in sorted(tally.items())))
print(f"Full table: {OUT / 'experiments_verification.csv'}")
sys.exit(1 if failed else 0)
