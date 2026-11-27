"""Values behind the article (checks M001 to M322 of expected/values.csv), recomputed from the archived
records."""

import csv, hashlib, json, math, re, sys
from collections import Counter, defaultdict
from importlib import metadata
from pathlib import Path
from statistics import median

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import witness_order
from paths import CATALOGUE, ROOT, archived, out_dir


def rows(path):
    with open(archived(path)) as f:
        return witness_order.final(path, list(csv.DictReader(f)))


def load(path):
    with open(archived(path)) as f:
        return json.load(f)


def records(path):
    with open(archived(path)) as f:
        return [json.loads(line) for line in f]


allocation = rows("data/primary/manifests/B1_PRIMARY_POPULATION.csv")
excluded = rows("data/primary/manifests/B1_UNRECOVERED_CONSTRUCTION_EXCLUSIONS.csv")
eligible_other = rows("data/primary/manifests/B1_PROSPECTIVE_ELIGIBLE.csv")
development = rows("data/primary/records/599_B1_FROZEN_CONSTRUCTION_MEMBERSHIP.csv")
sampled_ref = rows("data/primary/records/599_B1_REFERENCE_RERUN_FRESH.csv")
exact = rows("data/primary/records/599_B5_A1E_REFERENCE_EXACT.csv")
contract = rows("data/primary/records/599_B1_CONTRACT_RERUN.csv")
lattice = rows("data/primary/records/599_B1_OBSERVATION_RERUN.csv")
shot_cells = rows("data/primary/records/599_B2_SHOT_FRESH.csv")
tolerance_cells = rows("data/primary/records/599_B2_TOLERANCE_FRESH.csv")
bound_cells = rows("data/primary/records/599_B2_BOUND_FRESH.csv")
ablations = rows("data/primary/records/599_B2_EVIDENCE_ABLATION_FRESH.csv")
suite_runs = rows("data/primary/records/599_B5_A1G_POPULATION.csv")
suite_guards = rows("data/primary/decision/B5_A1G_GUARD.csv")
ghz_register = rows("data/primary/records/599_B5_A1K_GHZ_CONTRACT_AUDIT.csv")
qucheck_profile = rows("data/primary/decision/B5_A4_INTERFACE_CORRECTED.csv")
profiles = rows("data/primary/records/T1_4_INTERFACE_599.csv")
output_condition = load("data/primary/records/599_OUTPUT_CONDITION.json")
transpiler = load("data/primary/decision/B5_A3_SUMMARY.json")
state_groups = rows("data/primary/figures/EFFECT_CLASS_COMPRESSION.csv")
transfer = rows("data/interventions/transfer/B5_A4B_REPAIR_TRANSFER.csv")
width_manifest = rows("data/scalability/E4_SCALE_MANIFEST.csv")
width_cells = records("data/scalability/B2_SCALE_CELLS_FRESH.jsonl")
corpus_relations = load("data/scalability/B2_CORPUS_FRESH.json")
corpus_all = records("data/scalability/corpus/T2A_STRATIFIED_RAW.jsonl")
corpus_eligibility = rows("data/scalability/corpus/T2A_ELIGIBILITY.csv")
strata = load("data/scalability/corpus/T2A_STRATIFIED_SUMMARY.json")
stratum = load("data/scalability/corpus/T2A_STRATUM_MECHANISM.json")
btd_mechanism = load("data/scalability/corpus/T2A_CL5_MECHANISM.json")
timing = load("data/scalability/corpus/T2C_TIMING_SUMMARY.json")
entailment = load("data/scalability/corpus/T3_1_ENTAILED_VS_CONTINGENT.json")
defects = rows("data/external/defects/B3_REAL_DEFECTS_FRESH.csv")
defect_eligibility = rows("data/external/defects/B3_QUTEST_ELIGIBILITY_FRESH.csv")
exclusions = rows("data/prospective/cross_tool/cohort/S2_ELIGIBILITY_EXCLUSIONS.csv")
specification = archived("data/prospective/mqt_bench/frozen_deps/V2_SPECIFICATION.md").read_bytes()
environments = load("data/profiles/E5_ENVIRONMENT_LOCK.json")["reproduction_environments"]
muskit = load("data/profiles/E3_PROFILE_MATRIX.json")["interfaces"]["Muskit"]
rerun_primary = rows("data/certification/outcomes/R2_PRIMARY_PAIRS.csv")
rerun_corpus_width = rows("data/certification/outcomes/R2_CORPUS_WIDTH_PAIRS.csv")
rerun_external_ol = rows("data/certification/outcomes/R2_EXTERNAL_CL3.csv")
low_order = rows("data/certification/outcomes/R2_CHEAP_BASELINE.csv")
margins = rows("data/certification/outcomes/R2_MARGINS.csv")
margins_ext = rows("data/certification/outcomes/R2_MARGINS_EXT.csv")
excluded_kinds = rows("data/certification/outcomes/R2_CONDITIONAL_SEPARATIONS.csv")
numbers = load("data/certification/outcomes/R2V_NUMBERS.json")
matched = load("data/certification/outcomes/R2V_TABLE_X.json")
statistics = load("data/certification/outcomes/R2V_STATISTICS.json")
bound = load("data/certification/outcomes/R2V_BOUND.json")
relation_corpus = load("data/certification/outcomes/R2V_RELATION_CORPUS.json")
distance_ms = load("data/certification/outcomes/R2V_DISTANCE_TIMING.json")["median_ms_by_width"]
qiskit_16164 = load("data/certification/outcomes/R2V_RELEASED_CL3.json")
final_primary = rows("data/certification/outcomes/R2V_FINAL_PRIMARY.csv")
final_width = rows("data/certification/outcomes/R2V_FINAL_WIDTH.csv")
final_corpus = rows("data/certification/outcomes/R2V_FINAL_CORPUS.csv")
final_external = rows("data/certification/outcomes/R2V_FINAL_EXTERNAL.csv")
final_defect = rows("data/certification/outcomes/R2V_FINAL_DEFECT.csv")
rule_changes = rows("data/certification/outcomes/R2V_RULE_CHANGES.csv")
native = rows("data/certification/outcomes/R2V_NATIVE.csv") + rows(
    "data/certification/outcomes/R2V_NATIVE_DEFECTS.csv"
)
with open(ROOT / "data/certification/witness_order/IMPACT.csv") as f:
    impact = list(csv.DictReader(f))

OUTCOMES = ("CL1", "CL2", "CL3", "CL4", "CL5", "Unresolved")
THETAS = ("0.01", "0.025", "0.05", "0.1", "0.25", "0.5")
BAND_LO, BAND_HI, EQUAL_BELOW = 1e-10, 1e-8, 1e-9

# The baseline is the minimal suite with exact references. A survivor keeps the outcome of its
# sampled-reference record, unless the exact reference splits its native verdict: then it is unresolved.
exact_by_id = {r["mutant_id"]: r for r in exact}


def baseline_outcome(r):
    e = exact_by_id[r["mutant_id"]]
    if e["verdict_changed"] == "True" and e["exact_ref_native_verdict"] == "SPLIT":
        return "Unresolved"
    return r["diagnostic_outcome"]


survivors = [
    dict(r, diagnostic_outcome=baseline_outcome(r))
    for r in sampled_ref
    if exact_by_id[r["mutant_id"]]["exact_ref_native_verdict"] != "KILLED"
]
reported = {r["mutant_id"] for r in survivors if r["diagnostic_outcome"] != "Unresolved"}
outcome = Counter(r["diagnostic_outcome"] for r in survivors)
outcome_in = lambda p: Counter(r["diagnostic_outcome"] for r in survivors if r["population"] == p)
uniform = Counter(r["report_uniform_arbitrary_unitary"] for r in contract if r["mutant_id"] in reported)
declared = Counter(r["report_declared"] for r in contract if r["mutant_id"] in reported)

killed_by = lambda suite: {
    r["mutant_id"] for r in suite_runs if r["suite"] == suite and r["outcome"] == "KILLED"
}
published = {r["mutant_id"]: r["published_report"] for r in exact}
suite_kills = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for r in suite_runs:
    if r["suite"] != "S_MIN" and published.get(r["mutant_id"]) in ("CL3", "CL4"):
        cell = suite_kills[r["suite"]][published[r["mutant_id"]]]
        cell[0] += r["outcome"] == "KILLED"
        cell[1] += 1
suite_run = defaultdict(dict)
for r in suite_runs:
    suite_run[r["mutant_id"]][r["suite"]] = r
kills = lambda m, suite: suite_run[m][suite]["outcome"] == "KILLED"


def axis(m):
    cover, family, both = kills(m, "S_COVER"), kills(m, "S_FAMILY"), kills(m, "S_BOTH")
    if cover != family:
        return "coverage" if cover else "family"
    return "both_axes" if cover else "both_jointly" if both else "neither"


ghz = {r["mutant_id"]: r for r in ghz_register}
so_ids = [r["mutant_id"] for r in exact if r["published_report"] == "CL4"]
partition_declared = Counter(axis(m) for m in so_ids)
so_whole_string = [m for m in so_ids if ghz[m]["corrected_report"] == "CL4"]
partition_whole_string = Counter()
for m in so_whole_string:
    if ghz[m]["subject"].startswith("ghz"):
        partition_whole_string["family" if kills(m, "S_BOTH") else "both_jointly"] += 1
    else:
        partition_whole_string[axis(m)] += 1
transfer_evaluable = [r for r in transfer if r["outcome"] != "NOT_EVALUABLE"]

stable_cells = [r for r in shot_cells if r["native_verdict"] in ("KILLED", "SURVIVED")]
covered_cells = [r for r in stable_cells if r["guaranteed"] == "True"]
relations_by_cell = defaultdict(set)
for r in shot_cells:
    relations = tuple(r[k] for k in ("R_C", "R_S", "R_O", "R_A", "R_T"))
    relations_by_cell[(r["mutant_id"], r["theta"])].add(relations)
universe_bound = [r for r in bound_cells if r["role"] == "universe_decisive"]
universe_bound_ref = [r for r in universe_bound if r["theta"] == "0.05" and r["N"] == "2000"]
supported = lambda g: sum(1 for r in g if r["bound_status"] == "SUPPORTED")
btd_at = lambda theta, k: sum(1 for r in tolerance_cells if float(r["theta"]) == theta and r[k] == "CL5")
thetas = sorted({float(r["theta"]) for r in tolerance_cells})

width_cells_at = {
    n: [r for r in width_cells if int(r["n"]) == n] for n in sorted({int(r["n"]) for r in width_cells})
}
universe_seconds = lambda r: r["timings"]["B_universe"] + r["timings"]["C_relations"]
median_universe_seconds = lambda n: median(map(universe_seconds, width_cells_at[n]))
width_outcome = Counter("KILLED" if r["native_verdict"] == "KILLED" else r["report"] for r in width_cells)
relations_at = sorted((int(k), v) for k, v in corpus_relations["by_width"].items())
pairs_where = lambda p: sum(sum(v.values()) for k, v in relations_at if p(k))
ol_relations_where = lambda p: sum(v.get("CL3_SUBSTRATE", 0) for k, v in relations_at if p(k))

diagonal = {(r["case_set"], r["pair_id"]): r["diagonal_stratum"] == "True" for r in corpus_eligibility}
for r in corpus_all:
    r["diag"] = diagonal[(r["case_set"], r["pair_id"])]
corpus = [r for r in corpus_all if r["status"] == "OK"]
corpus_nondiagonal = [r for r in corpus if not r["diag"]]
corpus_diagonal = [r for r in corpus if r["diag"]]
corpus_survivors = [r for r in corpus if r["native_verdict"] == "SURVIVED"]
survivors_nondiagonal = [r for r in corpus_survivors if not r["diag"]]
survivors_diagonal = [r for r in corpus_survivors if r["diag"]]
count_ol = lambda g: sum(1 for r in g if r["diagnostic_outcome"] == "CL3")
corpus_ol_relations = [r for r in corpus if not r["R_S"] and r["R_O"]]
corpus_ol_at = {
    w: sum(1 for r in corpus if r["n"] == w and r["diagnostic_outcome"] == "CL3") for w in range(2, 15)
}
btd_separations = [r["max_universe_separation"] for r in corpus if r["diagnostic_outcome"] == "CL5"]
so_separations = [r["max_universe_separation"] for r in corpus if r["diagnostic_outcome"] == "CL4"]


def wilson(k, n, z=1.959963984540054):
    p = k / n
    scale = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / scale
    half = z / scale * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5
    return round(max(0.0, centre - half) * 100, 1), round(min(1.0, centre + half) * 100, 1)


witness_separated = lambda g: sum(1 for r in g if int(r["witness_separating_cuts"] or 0) > 0)
ol_primary = [r for r in rerun_primary if r["report"] == "CL3"]
ol_corpus = [r for r in rerun_corpus_width if r["arm"] == "corpus" and r["report"] == "CL3"]
ol_width = [r for r in rerun_corpus_width if r["arm"] == "width" and r["report"] == "CL3"]
rerun_primary_by_id = {r["mutant_id"]: r for r in rerun_primary}
under = lambda theta, universe, decision: sum(
    1 for r in rerun_primary if r[f"base_{theta}"] == "True" and r[f"{universe}_{theta}"] == decision
)
btd_under = lambda theta, universe: under(theta, universe, "false")
undecided_under = lambda theta, universe: under(theta, universe, "undecided")
rerun_btd = lambda arm: [r for r in rerun_corpus_width if r["arm"] == arm and r["report"] == "CL5"]
low_order_primary = [r for r in low_order if r["arm"] == "primary"]
low_order_width = [r for r in low_order if r["arm"] == "width" and r.get("t_full_s")]
low_order_corpus = [r for r in low_order if r["arm"] == "corpus"]
median_of = lambda g, k: median([float(r[k]) for r in g if r.get(k)])

margin_of = {(r["arm"], r["pair"]): r for r in margins if r["arm"] != "corpus"}
corpus_margins = list(zip((r for r in margins if r["arm"] == "corpus"), corpus_all))
in_band = lambda m: any(BAND_LO <= float(m[k]) <= BAND_HI for k in ("state_margin", "obs_margin"))
near_band = lambda m: any(1e-12 <= float(m[k]) <= 1e-6 for k in ("state_margin", "obs_margin"))
corpus_in_band = sorted(t["pair_id"] for m, t in corpus_margins if in_band(m))
corpus_near_band = sorted(t["pair_id"] for m, t in corpus_margins if near_band(m) and not in_band(m))
band_pairs = set(corpus_in_band) | {r["pair"] for r in margins if r["arm"] == "width" and in_band(r)}
equal_margins, different_margins = [], []
for table, columns in (
    (margins, ("state_margin", "obs_margin")),
    (margins_ext, ("unitary_margin", "qucheck_all_margin", "state_margin", "obs_margin")),
):
    for r in table:
        for k in columns:
            if r.get(k):
                decided = equal_margins if float(r[k]) < EQUAL_BELOW else different_margins
                decided.append((r["arm"], float(r[k])))
smallest_difference_small = min(v for a, v in different_margins if a in ("primary", "external"))
smallest_difference_large = min(v for a, v in different_margins if a in ("corpus", "width"))
dj_margin = next(r for r in margins if r["arm"] == "primary" and r["pair"] == "dj_3#e19")
dj_bound = next(
    r
    for r in bound_cells
    if (r["mutant_id"], r["N"], r["theta"], r["role"]) == ("dj_3#e19", "2000", "0.05", "suite_decisive")
)
dj_reference = next(r for r in sampled_ref if r["mutant_id"] == "dj_3#e19")
qra_174 = next(r for r in excluded_kinds if r["pair_id"] == "QRA_174")

native_job = {r["job_id"]: r for r in native}
outcome_counts = lambda rs: "/".join(str(sum(1 for r in rs if r["v2_report"] == c)) for c in OUTCOMES)
diagnosed = lambda rs: [r for r in rs if r["v2_report"] != "NA_KILLED"]
pct = lambda x: f"{100 * x:.1f}"
pct_interval = lambda a: f"[{100 * a[0]:.1f}, {100 * a[1]:.1f}]"
matched_row = (
    lambda s: (
        f"{s['pos']}/{s['neg']}/{pct(s['effect'])}/{pct_interval(s['cluster_ci95'])}/"
        f"{pct_interval(s['loco_range'])}"
    )
)
by_observation = {s["edge"]: s for s in matched["observation"]}
by_suite = {s["contrast"]: s for s in matched["suite"]}
by_profile = {s["contrast"]: s for s in matched["interface"]}
so_candidates = lambda rs: [r for r in rs if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"]
corpus_candidates = so_candidates(final_corpus)
corpus_withdrawn = [r for r in corpus_candidates if r["v2_report"] != "CL4" and r["c_kind"]]
corpus_split = [r for r in corpus_withdrawn if r["final_OB02"] != "failed" and r["final_OB13"] == "failed"]
corpus_guard_failed = [r for r in corpus_withdrawn if r["final_OB02"] == "failed"]
guard_fails = lambda r, requirement: int(native_job[f"corpus|{r['case_key']}|{requirement}"]["guard_fails"])
control_only_failures = sum(
    1 for r in corpus_guard_failed if guard_fails(r, "OB13") == 0 and guard_fails(r, "OB15") > 0
)
split_kills = sorted(int(native_job[f"corpus|{r['case_key']}|OB13"]["kills"]) for r in corpus_split)
corpus_case = {r["case_key"]: r for r in final_corpus}
corpus_diagnosed = diagnosed(final_corpus)
width_case = {r["case_key"]: r for r in final_width}
closed_order_corpus = len(witness_order.CHANGED["corpus"])
defect_candidates = lambda report: sum(
    1 for r in final_defect if r.get("v2_candidate") == "CL4" and r["v2_report"] == report
)
revised = [r for r in rule_changes if r["case"] not in witness_order.CHANGED.get(r["arm"], ())]
primary_witness_d = sorted(float(r["w_d"]) for r in final_primary if r["v2_report"] == "CL4")
smallest_witness = min((r for r in final_primary if r["v2_report"] == "CL4"), key=lambda r: float(r["w_d"]))
candidates_total = sum(
    len(so_candidates(rs)) for rs in (final_primary, final_width, final_corpus, final_external)
) + sum(1 for r in final_defect if r.get("v2_candidate") == "CL4")
near_band_outcomes = [
    b
    for b in relation_corpus["decided_different_below_1e-6"]
    if not any(x["pair"] == b["pair"] and x["set"] == b["set"] for x in relation_corpus["band_pairs"])
]

# QUTest is not redistributed: its documentation is read from an installed copy, as in the analytic tier.
try:
    qutest_readme = metadata.distribution("qutest").read_text("METADATA") or ""
except metadata.PackageNotFoundError:
    qutest_readme = None
NOT_INSTALLED = "SKIPPED: qutest 0.1.0 not installed"


def example_tests(readme):
    tests = []
    for block in re.findall(r"```qasm\n(.*?)```", readme, re.S):
        for m in re.finditer(r"def (test\w*)\(\)\s*\{(.*?)\n\}", block, re.S):
            body = [l.strip() for l in m.group(2).split("\n") if l.strip() and not l.strip().startswith("//")]
            if body:
                tests.append(body)
    return tests


def measures_directly(body):
    # A test calls the program as a helper or writes the circuit inline; in both, no gate may stand between
    # the program and the measurement.
    if not any("measure" in l for l in body):
        return False
    statements = [t.strip() for l in body for t in l.split(";") if t.strip()]
    calls = [i for i, t in enumerate(statements) if re.match(r"^\w+\(q\)$", t)]
    return all(i + 1 < len(statements) and "measure" in statements[i + 1] for i in calls)


examples = None if qutest_readme is None else example_tests(qutest_readme)

VALUES = {
    "M001": len(killed_by("S_MIN")),
    "M002": len(exact) - len(killed_by("S_MIN")),
    "M003": sum(1 for r in exact if r["exact_ref_native_verdict"] == "KILLED"),
    "M004": sum(1 for r in suite_guards if r["cell"] == "CLEAN"),
    "M005": len(killed_by("S_MIN") - killed_by("S_BOTH")),
    "M006": len(killed_by("S_FAMILY") - killed_by("S_MIN")),
    "M007": len(killed_by("S_COVER") - killed_by("S_MIN")),
    "M008": len(killed_by("S_BOTH") - killed_by("S_MIN")),
    "M009": sum(1 for r in ghz_register if r["moved"] == "True"),
    "M010": sum(1 for r in ghz_register if r["corrected_report"] == "CL4"),
    "M011": sum(1 for r in ghz_register if r["corrected_report"] == "CL3"),
    "M014": (
        sum(
            1
            for r in qucheck_profile
            if r["reference_report"] == "CL3" and r["R_O_QuCheck_all_qubits"] == "true"
        )
    ),
    "M015": sum(1 for r in transfer_evaluable if r["qutest_witness_expressible"] == "True"),
    "M016": sum(1 for r in transfer_evaluable if r["outcome"] == "WITNESS_EXISTS"),
    "M017": sum(1 for r in transfer_evaluable if r["outcome"] == "NO_WITNESS_ABOVE_THETA"),
    "M018": len(allocation) // 20,
    "M019": 20 * 30,
    "M020": len(allocation),
    "M021": len(development) + 149,
    "M022": len(development),
    "M023": len(excluded),
    "M024": sum(1 for r in eligible_other if r.get("eligible", "true").lower() in ("true", "1", "yes")),
    "M025": len(development) + 149,
    "M026": len(survivors),
    "M027": sum(outcome_in("construction").values()),
    "M028": sum(outcome_in("prospective").values()),
    "M029": outcome["CL1"],
    "M030": outcome["CL2"],
    "M031": outcome["CL3"],
    "M032": outcome["CL4"],
    "M033": outcome["CL5"],
    "M034": outcome["Unresolved"],
    "M035": len(reported),
    "M036": uniform["CL1"],
    "M037": uniform["CL2"],
    "M038": len(reported) - uniform["CL1"] - uniform["CL2"],
    "M039": declared["CL1"],
    "M040": sum(
        1
        for r in contract
        if r["mutant_id"] in reported
        and r["report_declared"] == "CL1"
        and r["report_uniform_arbitrary_unitary"] == "CL2"
    ),
    "M041": f"{100*declared['CL1']/len(reported):.1f}",
    "M042": f"{100*uniform['CL1']/len(reported):.1f}",
    "M043": sum(1 for r in lattice if r["CL3_Z_output"] == "True"),
    "M044": sum(1 for r in lattice if r["CL3_Z_all"] == "True"),
    "M045": sum(1 for r in lattice if r["CL3_XYZ_output"] == "True"),
    "M046": sum(1 for r in lattice if r["CL3_XYZ_all"] == "True"),
    "M047": len(lattice),
    "M048": "/".join(
        str(a - b)
        for a, b in [
            (
                sum(1 for r in lattice if r["CL3_Z_output"] == "True"),
                sum(1 for r in lattice if r["CL3_Z_all"] == "True"),
            ),
            (
                sum(1 for r in lattice if r["CL3_Z_output"] == "True"),
                sum(1 for r in lattice if r["CL3_XYZ_output"] == "True"),
            ),
            (
                sum(1 for r in lattice if r["CL3_Z_all"] == "True"),
                sum(1 for r in lattice if r["CL3_XYZ_all"] == "True"),
            ),
            (
                sum(1 for r in lattice if r["CL3_XYZ_output"] == "True"),
                sum(1 for r in lattice if r["CL3_XYZ_all"] == "True"),
            ),
        ]
    ),
    "M049": f"{suite_kills['S_FAMILY']['CL3'][0]}/{suite_kills['S_FAMILY']['CL3'][1]}",
    "M050": f"{suite_kills['S_FAMILY']['CL4'][0]}/{suite_kills['S_FAMILY']['CL4'][1]}",
    "M051": f"{suite_kills['S_COVER']['CL3'][0]}/{suite_kills['S_COVER']['CL3'][1]}",
    "M052": f"{suite_kills['S_COVER']['CL4'][0]}/{suite_kills['S_COVER']['CL4'][1]}",
    "M053": (
        f"{partition_declared['coverage']}/{partition_declared['family']}/"
        f"{partition_declared['both_jointly']}"
    ),
    "M054": sum(partition_declared.values()),
    "M055": (
        f"{partition_whole_string['coverage']}/{partition_whole_string['family']}/"
        f"{partition_whole_string['both_jointly']}"
    ),
    "M056": sum(partition_whole_string.values()),
    "M057": len(corpus_all),
    "M058": len(corpus_all) - len(corpus),
    "M059": all(r["U_v_agree"] for r in corpus),
    "M060": all(r["guard_false_fails"] == 0 for r in corpus),
    "M061": corpus[0]["reference_condition"],
    "M062": sum(1 for r in corpus if r["native_verdict"] == "KILLED"),
    "M063": len(corpus_survivors),
    "M064": (
        f'{sum(1 for r in corpus if r["native_verdict"]=="SPLIT")}/'
        f'{sum(1 for r in corpus if r["native_verdict"]=="SPLIT" and r["diagnostic_outcome"]=="Unresolved")}'
    ),
    "M065": "/".join(
        str(sum(1 for r in corpus if r["diagnostic_outcome"] == c)) for c in ("CL1", "CL3", "CL4", "CL5")
    ),
    "M066": sum(1 for r in corpus if r["diagnostic_outcome"] == "CL2"),
    "M067": f"{len(corpus_ol_relations)}/{count_ol(corpus)}",
    "M068": f"{len(corpus_nondiagonal)}/{len(corpus_diagonal)}",
    "M069": f"{count_ol(corpus_nondiagonal)}/{len(corpus_nondiagonal)}",
    "M070": f"{count_ol(corpus_diagonal)}/{len(corpus_diagonal)}",
    "M071": (
        f'{count_ol([r for r in corpus_survivors if not r["diag"]])}/'
        f'{sum(1 for r in corpus_survivors if not r["diag"])}'
    ),
    "M072": "/".join(str(corpus_ol_at[w]) for w in range(2, 15)),
    "M073": sum(corpus_ol_at.values()) + 1,
    "M074": f'{btd_mechanism["construction_set"]["exactly_one"]}/{btd_mechanism["construction_set"]["n"]}',
    "M075": btd_mechanism["construction_set"]["minimum"],
    "M076": btd_mechanism["construction_set"]["share_at_or_below_theta"],
    "M077": f'{btd_mechanism["corpus_frame"]["exactly_one"]}/{btd_mechanism["corpus_frame"]["n"]}',
    "M078": btd_mechanism["corpus_frame"]["share_at_or_below_theta"],
    "M079": f'{stratum["diagonal_stratum_cl3"]}/{stratum["diagonal_stratum_size"]}',
    "M080": stratum["cl3_rate_by_mutation_kind"]["insertion"]["rate"],
    "M081": stratum["cl3_rate_by_mutation_kind"]["other"]["cl3"],
    "M082": str(wilson(count_ol(corpus_nondiagonal), len(corpus_nondiagonal))),
    "M083": str(wilson(count_ol(corpus_diagonal), len(corpus_diagonal))),
    "M084": (
        str(wilson(count_ol(survivors_nondiagonal), len(survivors_nondiagonal)))
    ),
    "M085": (
        str(wilson(count_ol(survivors_diagonal), len(survivors_diagonal)))
    ),
    "M086": (
        wilson(count_ol(corpus_nondiagonal), len(corpus_nondiagonal))[1]
        < wilson(count_ol(corpus_diagonal), len(corpus_diagonal))[0]
    ),
    "M087": output_condition["at_599"]["pool"],
    "M088": output_condition["at_599"]["movers"],
    "M089": output_condition["at_599"]["out"],
    "M090": (
        f'{output_condition["at_599"]["movers_by_report"]["CL3"]}/{output_condition["at_599"]["total_cl3"]}'
    ),
    "M091": output_condition["validation"]["reproduces_published"],
    "M092": entailment["entailed"]["n"],
    "M093": f'{entailment["entailed"]["R_O_holds"]}/{entailment["entailed"]["n"]}',
    "M094": f'{entailment["entailed"]["cl3"]}/{entailment["entailed"]["n"]}',
    "M095": entailment["not_entailed"]["cl3"],
    "M096": entailment["entailed"]["cl3"] + entailment["not_entailed"]["cl3"],
    "M097": entailment["stratum_vs_entailment"]["entailed_in_diagonal_stratum"],
    "M098": entailment["stratum_vs_entailment"]["contingent_cl3_in_diagonal_stratum"],
    "M099": entailment["stratum_vs_entailment"]["entailed_in_non_diagonal_stratum"],
    "M100": entailment["stratum_vs_entailment"]["non_entailed_in_diagonal_stratum"],
    "M101": (
        round(timing["median_phase_seconds"]["A_evidence_acquisition"] / timing["median_total_seconds"], 3)
    ),
    "M102": round(timing["by_width"]["14"]["median_B"] / timing["by_width"]["14"]["median_total_seconds"], 3),
    "M103": timing["by_width"]["10"]["median_B"] / timing["by_width"]["10"]["median_total_seconds"] < 0.002,
    "M104": round(timing["by_width"]["14"]["median_B"] / timing["by_width"]["13"]["median_B"], 2),
    "M105": timing["extrapolation"]["crossover_n_where_enumeration_overtakes_suite_execution"],
    "M106": (
        timing["extrapolation"]["projected_total_seconds_holding_A_at_its_median"]["18"]
        < 600
        < timing["extrapolation"]["projected_total_seconds_holding_A_at_its_median"]["19"]
    ),
    "M107": round(max(btd_separations), 4),
    "M108": round(min(so_separations), 4),
    "M109": max(btd_separations) < 0.05 < min(so_separations),
    "M110": (
        f'{count_ol([r for r in corpus_survivors if r["diag"]])}/'
        f'{sum(1 for r in corpus_survivors if r["diag"])}'
    ),
    "M111": sum(1 for m in so_whole_string if ghz[m]["subject"].startswith("ghz")),
    "M112": (
        sum(1 for m in so_whole_string if ghz[m]["subject"].startswith("ghz") and axis(m) == "both_jointly")
    ),
    "M113": f"{suite_kills['S_BOTH']['CL4'][0]}/{suite_kills['S_BOTH']['CL4'][1]}",
    "M119": sum(
        1
        for r in qucheck_profile
        if r["reference_report"] == "CL3" and r["R_O_QuCheck_declared_register"] == "true"
    ),
    "M120": len(shot_cells),
    "M121": sum(1 for v in relations_by_cell.values() if len(v) > 1),
    "M122": f"{len(covered_cells)}/{len(stable_cells)}",
    "M123": sum(1 for r in covered_cells if r["agree"] == "False"),
    "M124": (
        f"{sum(1 for r in stable_cells if r['guaranteed']=='False' and r['agree']=='False')}/"
        f"{len(stable_cells)-len(covered_cells)}"
    ),
    "M125": f"{supported(universe_bound_ref)}/{len(universe_bound_ref)}",
    "M126": f"{supported(universe_bound)}/{len(universe_bound)}",
    "M127": f"{100*supported(universe_bound)/len(universe_bound):.1f}",
    "M128": len(ablations),
    "M129": len({(r["mutant_id"], r["suite"], r["report"]) for r in ablations}),
    "M130": len(ablations) // 2,
    "M131": f"{len(ablations)/2/len({(r['mutant_id'],r['suite'],r['report']) for r in ablations}):.2f}",
    "M132": len(tolerance_cells),
    "M133": ",".join(str(btd_at(t, "analytic_candidate")) for t in thetas),
    "M134": ",".join(str(btd_at(t, "supported_report")) for t in thetas),
    "M135": len(width_manifest),
    "M136": len(width_cells),
    "M137": width_outcome["KILLED"],
    "M138": width_outcome["CL1"],
    "M139": width_outcome["CL3"],
    "M140": width_outcome["CL4"],
    "M141": width_outcome["CL5"],
    "M142": width_outcome["Unresolved"],
    "M143": int(width_cells_at[8][0]["U_v_implementation"]),
    "M144": int(width_cells_at[14][0]["U_v_implementation"]),
    "M145": (
        round(median_universe_seconds(14) / median_universe_seconds(8))
    ),
    "M146": f"{median_universe_seconds(8) * 1000:.1f}",
    "M147": f"{median_universe_seconds(14):.2f}",
    "M148": (
        f"{min(median([float(x['total_seconds']) for x in g]) for g in width_cells_at.values()):.1f}/"
        f"{max(median([float(x['total_seconds']) for x in g]) for g in width_cells_at.values()):.1f}"
    ),
    "M149": f"{max(float(r['total_seconds']) for r in width_cells):.1f}",
    "M150": f"{max(float(r['peak_rss_gib']) for r in width_cells):.3f}",
    "M151": (
        sum(1 for r in width_cells if r.get("memory_censored") == "True" or r.get("within_budget") is False)
    ),
    "M152": corpus_relations["distinct_pairs"],
    "M153": f"{100*ol_relations_where(lambda k:k<=7)/pairs_where(lambda k:k<=7):.1f}",
    "M154": f"{100*ol_relations_where(lambda k:k>=8)/pairs_where(lambda k:k>=8):.1f}",
    "M155": len(defects),
    "M156": sum(1 for r in defects if r["evidence_depth"] == "NOT_REPRODUCIBLE"),
    "M157": sum(1 for r in defects if r["evidence_depth"] == "NATIVE_REPRODUCTION_ONLY"),
    "M158": sum(1 for r in defects if r["evidence_depth"] == "PROFILE_ONLY"),
    "M159": sum(1 for r in defects if r["evidence_depth"] == "RELATION_LEVEL"),
    "M160": sum(1 for r in defects if r["evidence_depth"] == "FULL_CERTIFICATION"),
    "M161": sum(1 for r in defect_eligibility if r["qutest_eligibility"] == "ELIGIBLE"),
    "M169": sum(1 for r in profiles if r["R_O_QUTest"] == "True" and r["R_O_QuCheck"] == "False"),
    "M170": sum(1 for r in profiles if r["R_O_QUTest"] == "False" and r["R_O_QuCheck"] == "True"),
    "M171": f"{witness_separated(ol_primary)}/{len(ol_primary)}",
    "M172": (
        sum(
            1
            for r in ol_primary
            if int(r["witness_separating_cuts"] or 0) > 0 and r["subject"].startswith("qft")
        )
    ),
    "M173": f"{witness_separated(ol_corpus)}/{len(ol_corpus)}",
    "M174": f"{witness_separated(ol_width)}/{len(ol_width)}",
    "M175": f"{witness_separated(rerun_external_ol)}/{len(rerun_external_ol)}",
    "M176": (
        f"{sum(1 for r in rerun_external_ol if r['R_O_recomputed'].lower() in r['R_O_frozen'].lower())}/"
        f"{len(rerun_external_ol)}"
    ),
    "M177": (
        f"{sum(1 for r in low_order_primary if r['report']=='CL4' and r['cheap_witness']=='True')}/"
        f"{sum(1 for r in low_order_primary if r['report']=='CL4')}"
    ),
    "M178": (
        sum(
            1
            for r in low_order_primary
            if float(r["full_max"]) > EQUAL_BELOW and r["cheap_witness"] != "True"
        )
    ),
    "M179": sum(1 for r in low_order_corpus if r["report"] == "CL4" and r["cheap_witness"] != "True"),
    "M180": sum(1 for r in low_order_corpus if r["report"] == "CL4"),
    "M181": f"{median_of(low_order_primary,'t_cheap_s')*1000:.2f}",
    "M182": f"{median_of(low_order_primary,'t_full_s')*1000:.2f}",
    "M183": f"{median_of(low_order_width,'t_cheap_s')*1000:.1f}",
    "M184": f"{median_of(low_order_width,'t_full_s')*1000:.0f}",
    "M185": ",".join(str(btd_under(t, "RAcert")) for t in THETAS),
    "M186": btd_under("0.5", "RAcert"),
    "M187": sum(1 for r in tolerance_cells if r["theta"] == "0.5" and r["analytic_candidate"] == "CL5"),
    "M188": ",".join(str(btd_under(t, "RA5")) for t in THETAS),
    "M189": sum(
        1
        for r in rerun_primary
        if r["base_0.5"] == "True" and r["RA5_0.5"] == "false" and r["RAcert_0.5"] == "true"
    ),
    "M190": sum(
        1
        for r in rerun_primary
        if r["base_0.5"] == "True" and r["RA5_0.5"] == "undecided" and r["RAcert_0.5"] == "true"
    ),
    "M191": undecided_under("0.5", "RAcert"),
    "M192": undecided_under("0.5", "RA5"),
    "M193": btd_under("0.5", "RAcond"),
    "M194": ",".join(str(btd_under(t, "RAcond")) for t in THETAS[:5]),
    "M195": ",".join(
        str(
            sum(
                1
                for r in tolerance_cells
                if r["theta"] == t
                and r["supported_report"] == "CL5"
                and rerun_primary_by_id[r["mutant_id"]][f"RAcert_{t}"] == "false"
            )
        )
        for t in THETAS
    ),
    "M196": btd_under("0.05", "RAcond"),
    "M202": sum(1 for r in rerun_btd("width") if r["RAcert"] == "true" or r["pair_id"] in band_pairs),
    "M203": f"{float(margin_of[('width','SBS_055')]['obs_margin'])*1e9:.1f}",
    "M204": (
        f"{sum(1 for r in rerun_btd('corpus') if r['RAcert']=='true' or r['pair_id'] in band_pairs)}/"
        f"{len(rerun_btd('corpus'))}"
    ),
    "M205": sum(1 for r in rerun_btd("corpus") if r["RAcert"] == "false" and r["pair_id"] not in band_pairs),
    "M206": (
        sum(
            1 for r in rerun_btd("corpus") if r["RAcert"] == "true" and r["pair_id"] in ("QRA_513", "SBS_081")
        )
    ),
    "M207": len(corpus_in_band),
    "M208": (
        f"{sum(1 for r in excluded_kinds if r['arm']=='corpus' and r['separated_by_excluded_kinds']=='True')}/{sum(1 for r in excluded_kinds if r['arm']=='corpus')}"
    ),
    "M209": (
        sum(1 for r in excluded_kinds if r["arm"] == "corpus" and r["only_rare_bit_separations"] == "True")
    ),
    "M210": sum(1 for r in excluded_kinds if r["arm"] == "corpus" and r["most_frequent_separates"] == "True"),
    "M211": f"{float(qra_174['max_corr_bit_p1_original'].split(';')[0])*1e8:.1f}",
    "M212": f"{float(qra_174['max_corr_change']):.2f}",
    "M213": f"{float(qra_174['max_U5'])*1e7:.1f}",
    "M214": math.ceil(max(v for a, v in equal_margins) * 1e12),
    "M215": math.floor(smallest_difference_small * 1e3),
    "M216": f"{smallest_difference_large*1e9:.1f}",
    "M217": len(corpus_near_band),
    "M218": f"{float(dj_margin['state_margin']):.3f}",
    "M219": int(float(dj_margin["obs_margin"]) * 1e12),
    "M220": f"{float(dj_bound['single_repetition_bound'])*1e5:.1f}",
    "M221": f"{float(dj_bound['unanimity_failure_bound'])*1e3:.1f}",
    "M222": f"{dj_reference['kills_recorded']}/{dj_reference['reps']}",
    "M223": hashlib.sha256(specification).hexdigest()[:8],
    "M224": f"{numbers['native_jobs_total']}/{numbers['native_qutest_runs']}",
    "M225": len(revised),
    "M226": sum(1 for r in revised if r["v2_report"] == "Unresolved"),
    "M227": sum(1 for r in rule_changes if r["arm"] in ("primary", "external")),
    "M228": sum(1 for r in rule_changes if "CL3" in (r["v1_report"], r["v2_report"])),
    "M229": (
        f"{candidates_total}/{numbers['primary_ob13_recorded_reuse']}/"
        f"{sum(1 for r in native if r['purpose']=='OB13')}/{sum(1 for r in native if r['purpose']=='OB15')}"
    ),
    "M230": "/".join(
        str(
            sum(numbers[f"{a}_cl4_breakdown"].get(k, 0) for a in ("primary", "width", "corpus", "external"))
            + {
                "supported": closed_order_corpus + defect_candidates("CL4"),
                "no_control": defect_candidates("Unresolved") - closed_order_corpus,
            }.get(k, 0)
        )
        for k in ("supported", "witness_split", "guard_false_failure", "no_control")
    ),
    "M231": outcome_counts(diagnosed(final_primary)),
    "M232": outcome_counts([r for r in diagnosed(final_primary) if r["population"] == "construction"]),
    "M233": outcome_counts([r for r in diagnosed(final_primary) if r["population"] == "prospective"]),
    "M234": f"{numbers['primary_cl4_breakdown'].get('supported', 0)}/{numbers['primary_cl4_candidates']}",
    "M235": numbers["primary_ob13_recorded_reuse"],
    "M236": f"{numbers['effects_cl3']['groups']}/{numbers['effects_cl3']['cases']}",
    "M237": f"{numbers['effects_cl2_construction']['groups']}/{numbers['effects_cl2_construction']['cases']}",
    "M238": f"{primary_witness_d[0]:.3f}/{primary_witness_d[1]:.3f}",
    "M239": (
        "/".join(r["state"] for r in state_groups if r["claim"] != "ALL")
        + "/"
        + next(r["state"] for r in state_groups if r["claim"] == "ALL")
    ),
    "M240": int(next(r["obs"] for r in state_groups if r["claim"] == "ALL")),
    "M241": matched_row(by_observation["Z: output -> all qubits"]),
    "M242": matched_row(by_observation["output: Z -> XYZ"]),
    "M243": matched_row(by_observation["all qubits: Z -> XYZ"]),
    "M244": matched_row(by_observation["XYZ: output -> all qubits"]),
    "M245": matched_row(by_suite["S_MIN -> S_FAMILY"]),
    "M246": matched_row(by_suite["S_MIN -> S_COVER"]),
    "M247": matched_row(by_suite["S_MIN -> S_BOTH"]),
    "M250": matched_row(by_profile["QUTest -> QuCheck"]),
    "M251": f"{by_profile['QUTest -> QuCheck']['exact_mcnemar_p']:.3f}",
    "M252": matched_row(by_profile["QUTest -> pytest"]),
    "M253": f"{statistics['v2']['resolved']}/{statistics['v2']['created']}/{pct(statistics['v2']['effect'])}",
    "M254": (
        f"{statistics['v2']['exact_mcnemar_p']:.1e}/{pct_interval(statistics['v2']['cluster_ci95'])}/"
        f"{pct_interval(statistics['v2']['loco_range'])}"
    ),
    "M255": all(s["matches_record"] for k in ("observation", "suite", "interface") for s in matched[k]),
    "M256": (
        len(matched["checks"]["observation_band_decisions"])
        + len(matched["checks"]["interface_band_decisions"])
    ),
    "M257": "/".join(str(numbers["decision_grid_by_N"][n]["killed"]) for n in ("500", "2000", "8000")),
    "M258": (
        "/".join(str(numbers["decision_grid_by_N"][n]["decision_supported"]) for n in ("500", "2000", "8000"))
    ),
    "M259": "/".join(str(numbers["decision_grid_by_N"][n]["unresolved"]) for n in ("500", "2000", "8000")),
    "M260": numbers["decision_grid_R_T_unchanged"],
    "M261": ",".join(map(str, numbers["tolerance_cl5_candidates"])),
    "M262": ",".join(map(str, numbers["tolerance_cl5_decision_supported"])),
    "M263": numbers["tolerance_cl5_resolution_limited"][-1],
    "M264": "/".join(
        str(numbers["tolerance_theta_invariant_relations"][k]) for k in ("R_C_true", "R_S_true", "R_O_true")
    ),
    "M265": f"{numbers['ablation']['certificates']}/{numbers['ablation']['ablations']}",
    "M266": f"{numbers['ablation']['ablations'] / 2 / numbers['ablation']['certificates']:.2f}",
    "M267": (
        numbers["ablation"]["all_withdrawn"]
        and numbers["ablation"]["all_named"]
        and numbers["ablation"]["all_candidate_unchanged"]
    ),
    "M268": (
        f"{numbers['decision_grid_by_gate_8000']['phase']['unresolved']}/"
        f"{numbers['decision_grid_by_gate_8000']['phase']['not_killed']}/"
        f"{numbers['decision_grid_by_gate_8000']['other']['unresolved']}/"
        f"{numbers['decision_grid_by_gate_8000']['other']['not_killed']}"
    ),
    "M269": (
        f"{numbers['decision_grid_by_gate_8000']['phase']['reference_cl3']}/"
        f"{numbers['decision_grid_by_gate_8000']['phase']['mutants']}/"
        f"{numbers['decision_grid_by_gate_8000']['other']['reference_cl3']}/"
        f"{numbers['decision_grid_by_gate_8000']['other']['mutants']}"
    ),
    "M273": outcome_counts(diagnosed(final_external)),
    "M274": f"{numbers['external_cl4_breakdown'].get('supported', 0)}/{numbers['external_cl4_candidates']}",
    "M275": outcome_counts(diagnosed(final_width)),
    "M276": (
        f"{min(int(r['universe_size']) for r in final_width)}/"
        f"{max(int(r['universe_size']) for r in final_width)}"
    ),
    "M277": (
        all(
            int(r["universe_size"]) == 2 ** (int(r["n"]) + 1) + int(r["n"]) + 3
            for r in final_width + final_corpus
        )
    ),
    "M278": f"{float(width_case['SBS_061']['w_d']) - 0.05:.3f}/{native_job['width|SBS_061|OB13']['kills']}",
    "M279": (
        f"{native_job['width|SBS_081|OB13']['guard_fails']}/"
        f"{len(native_job['width|SBS_081|OB13']['guard_verdicts'].split(';'))}"
    ),
    "M280": (
        f"{float(width_case['SBS_055']['margin_obs']) * 1e9:.1f}/"
        f"{width_case['SBS_055']['undecided_relation']}"
    ),
    "M281": (
        f"{distance_ms['8']['hellinger'] + distance_ms['8']['kl']:.3f}/"
        f"{distance_ms['14']['hellinger'] + distance_ms['14']['kl']:.2f}"
    ),
    "M282": outcome_counts(diagnosed(final_corpus)),
    "M283": len(corpus_candidates),
    "M284": (
        f"{numbers['corpus_cl4_breakdown']['witness_split']}/"
        f"{numbers['corpus_cl4_breakdown']['guard_false_failure']}/"
        f"{sum(1 for r in corpus_candidates if r['v2_report'] != 'CL4' and not r['c_kind'])}"
    ),
    "M285": f"{sum(1 for r in corpus_split if float(r['w_d']) - 0.05 < 0.05)}/{len(corpus_split)}",
    "M286": f"{split_kills[0]}/{split_kills[-1]}",
    "M287": control_only_failures,
    "M288": (
        f"{corpus_case['qra_cases_v1_1/QRA_360']['n']}/"
        f"{'no_control' if not corpus_case['qra_cases_v1_1/QRA_360']['c_kind'] else 'control'}"
    ),
    "M289": (
        f"{sum(1 for r in corpus_candidates if r['v2_report'] != 'CL4' and r['v1_report'] == 'CL4')}/"
        f"{sum(1 for r in corpus_candidates if r['v2_report'] != 'CL4')}"
    ),
    "M290": (
        f"{corpus_case['qra_cases/QRA_513']['v2_report']}/{corpus_case['sbs_cases/SBS_081']['v2_report']}"
    ),
    "M291": (
        f"{numbers['sep_primary']['at_least_one']}/{numbers['sep_primary']['cases']}/"
        f"{numbers['sep_corpus']['at_least_one']}/{numbers['sep_corpus']['cases']}"
    ),
    "M292": f"{numbers['sep_corpus']['min'] * 1e7:.1f}",
    "M293": f"{numbers['sep_corpus']['largest_cl5_u5']:.4f}/{numbers['sep_corpus']['smallest_cl4_u5']:.4f}",
    "M294": (
        f"{numbers['corpus_v2_cl5_excluded_separate']}/{numbers['corpus_v2_cl5']}/"
        f"{numbers['corpus_v2_cl5_rare_bit_only']}/{numbers['corpus_v2_cl5_most_frequent']}"
    ),
    "M295": (
        f"{float(corpus_case['qra_cases/QRA_174']['margin_obs']) * 1e9:.1f}/"
        f"{corpus_case['qra_cases/QRA_174']['v2_report']}"
    ),
    "M296": (
        f"{numbers['corpus_v2_cl4_higher_order']}/"
        f"{numbers['corpus_v2_cl4_low_order'] + numbers['corpus_v2_cl4_higher_order'] + closed_order_corpus}"
    ),
    "M297": relation_corpus["cl3_substrate"]["v2"],
    "M298": (
        f"{relation_corpus['shares_v2']['n<=7'][0]}/{relation_corpus['shares_v2']['n<=7'][1]}/"
        f"{relation_corpus['shares_v2']['n>=8'][0]}/{relation_corpus['shares_v2']['n>=8'][1]}"
    ),
    "M299": relation_corpus["undecided_v2"],
    "M300": (
        "/".join(next((r["v2_report"], r["unmet"]) for r in final_defect if r.get("v2_candidate") == "CL4"))
    ),
    "M301": next(f"{r['v2_report']}/{r['universe_v2']}" for r in final_defect if r["v2_report"] == "CL2"),
    "M302": (
        f"{bound['kill_decision']['stable_cells']}/{bound['kill_decision']['disagreements_outside_c1']}/"
        f"{bound['kill_decision']['disagreements_inside_c_ref']}"
    ),
    "M303": (
        f"{bound['kill_decision']['covered_c1']}/{bound['kill_decision']['covered_c_ref']}/"
        f"{bound['kill_decision']['covered_c2']}/"
        f"{bound['kill_decision']['gained_at_500_c_ref_vs_c2']}/"
        f"{bound['kill_decision']['lost_at_8000_c_ref_vs_c2']}"
    ),
    "M304": (
        f"{bound['witness_surface_v2']['covered_c1']}/{bound['witness_surface_v2']['decisions']}/"
        f"{bound['witness_surface_v2']['reference_schedule_c1']}"
    ),
    "M305": (
        f"{bound['witness_surface_v2']['covered_c2']}/{bound['witness_surface_v2']['reference_schedule_c2']}"
    ),
    "M306": bound["v1_universe_rows_reproduced_mismatches"],
    "M307": relation_corpus["max_margin_decided_equal"] < 7e-12,
    "M308": "/".join(sorted(corpus_case[f"{b['set']}/{b['pair']}"]["v2_report"] for b in near_band_outcomes)),
    "M309": NOT_INSTALLED if examples is None else len(examples),
    "M310": NOT_INSTALLED if examples is None else all(measures_directly(body) for body in examples),
    "M311": "appends .measure(q[i], c[i]) for every qubit" in muskit["alpha_v"],
    "M312": (
        "/".join(exclusions[0][k] for k in ("mutant_id", "location", "exclusion_class"))
        if len(exclusions) == 1
        else len(exclusions)
    ),
    "M313": "/".join(environments[k]["qiskit"] for k in ("Q045", "Q11", "Q25")),
    "M314": f"{qiskit_16164['state_margin']:.3f}/{qiskit_16164['obs_margin'] * 1e17:.1f}",
    "M315": f"{sum(1 for r in corpus_diagnosed if r['native_verdict'] != 'SPLIT')}/{len(corpus_diagnosed)}",
    "M316": (
        f"{strata['eligible']['non_diagonal']['cl3']}/{strata['eligible']['non_diagonal']['n']}/"
        f"{strata['entering_diagnosis']['non_diagonal']['cl3']}/"
        f"{strata['entering_diagnosis']['non_diagonal']['n']}"
    ),
    "M317": (
        f"{strata['eligible']['diagonal']['cl3']}/{strata['eligible']['diagonal']['n']}/"
        f"{100*strata['eligible']['diagonal']['rate']:.1f}/"
        f"{strata['entering_diagnosis']['diagonal']['cl3']}/{strata['entering_diagnosis']['diagonal']['n']}/"
        f"{100*strata['entering_diagnosis']['diagonal']['rate']:.1f}"
    ),
    "M318": (
        f"{len(corpus)}={len(corpus_nondiagonal)}+{len(corpus_diagonal)}/{len(corpus_survivors)}="
        f"{sum(1 for r in corpus_survivors if not r['diag'])}+{sum(1 for r in corpus_survivors if r['diag'])}"
    ),
    "M319": (
        f"{transpiler['certified_min']}/{transpiler['certified_max']}/{transpiler['pairs']}/"
        f"{transpiler['configurations']}"
    ),
    "M320": f"{float(smallest_witness['w_d']):.3f}/{smallest_witness['w_kind']}",
    "M321": (
        f"{len(revised)}/"
        f"{len({r['case'] if r['arm'] == 'corpus' else 'sbs_cases/' + r['case'] for r in revised})}/"
        f"{sum(r['arm'] == 'corpus' for r in revised)}/{sum(r['arm'] == 'width' for r in revised)}"
    ),
    "M322": (
        f"{sum(int(r['candidates']) for r in impact)}/"
        f"{sum(int(r['v2_controls']) + int(r['v3_controls_formed']) for r in impact)}/"
        f"{sum(int(r['v3_controls_formed']) for r in impact)}"
    ),
}

skipped = [k for k, v in VALUES.items() if str(v).startswith("SKIPPED")]
mismatches = []
for cid, value in VALUES.items():
    label, expected = CATALOGUE[cid]["label"], CATALOGUE[cid]["expected"]
    tag = "SKIP" if cid in skipped else "OK  " if str(value) == expected else "FAIL"
    if tag == "FAIL":
        mismatches.append(f"   MISMATCH  {label}: expected {expected}  recomputed {value}")
    print(f"  {tag}  {label:<48} expected {expected:<14} recomputed {value}")
print(
    f"\n{len(VALUES) - len(mismatches) - len(skipped)} of {len(VALUES) - len(skipped)} checks recomputed "
    f"from the "
    f"packaged records; {len(skipped)} left to the analytic tier"
)
for line in mismatches:
    print(line)
with open(out_dir() / "article_checks.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["check_id", "label", "expected", "recomputed", "match"])
    for cid, value in VALUES.items():
        expected = CATALOGUE[cid]["expected"]
        match = "skipped" if cid in skipped else str(value) == expected
        w.writerow([cid, CATALOGUE[cid]["label"], expected, value, match])
