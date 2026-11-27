"""Registered predictions, gate-set and depth trials, protocol records, commits and file times (checks V06 to
V18 of expected/values.csv), recomputed from the archived records."""

import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

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


def text(path):
    return archived(path).read_text(encoding="utf-8")


def table(path):
    with open(ROOT / path) as f:
        return list(csv.DictReader(f))


structural = rows("data/structural/records/STRUCTURAL_DEFINITIONS.csv")
canonical = rows("data/structural/CANONICAL_RESULT_LEDGER.csv")
trials = {r["mutant_id"]: r for r in rows("data/structural/records/QUTEST_GATESET_VARIABILITY.csv")}
trials_40 = {r["mutant_id"]: r for r in rows("data/structural/records/QUTEST_GATESET_VARIABILITY_T40.csv")}
trial_summary = load("data/structural/records/QUTEST_GATESET_VARIABILITY_SUMMARY.json")
admissibility = rows("data/prospective/cross_tool/results/S3_QUTEST_ADMISSIBILITY.csv")
cross_tool = rows("data/prospective/cross_tool/results/S3_CROSS_TOOL_RESULTS.csv")
estimands = {r["estimand"]: r for r in rows("data/prospective/cross_tool/estimands/S4_VALIDATION_ESTIMANDS.csv")}
REGISTRY = "data/prospective/registration/CLAIM_DECISION_BASELINE.md"
COHORT = "data/prospective/cross_tool/cohort/S2_COHORT_HASH.txt"
predictions = set(re.findall(r"^\| (P\d+) \|", text(REGISTRY), re.M))
commits = table("provenance/git_commit_records.csv")
FINAL = [f"data/certification/outcomes/R2V_FINAL_{p}.csv" for p in ("PRIMARY", "WIDTH", "CORPUS", "EXTERNAL", "DEFECT")]
GUARDS = "data/primary/suite_guards/"
guards = rows(GUARDS + "B5_A1B_GUARD_EXACT.csv")
guard_plan = text(GUARDS + "SUITE_GUARD_PLAN.md")
with open(archived(GUARDS + "a1c.log"), encoding="utf-8") as f:
    mutant_run_header = f.readline()
modified = {r["package_path"]: r["original_mtime_utc"] for r in table("provenance/source_manifest.csv")}
input_change = load("data/external/protocol/EXTERNAL_COHORT_FREEZE_v3.json")
adapter_change = load("data/external/protocol/EXTERNAL_COHORT_FREEZE_v4.json")

flagged = lambda population, column: sum(
    r[column] == "True" for r in structural if r["population"] == population
)


def category(r):
    if r["separated_trials"] == r["trials"]:
        return "all"
    return "none" if r["separated_trials"] == "0" else "some"


equivalent_other = [r for r in admissibility if r["contract_equivalent"] == "True"]
other = [r for r in admissibility if r["contract_equivalent"] != "True"]
separates = lambda rs, kind: sum(r[f"{kind}_separates"] == "True" for r in rs)
by_category = Counter((r["population"], category(r)) for r in trials.values())
gate_sets = defaultdict(set)
for r in structural:
    gate_sets[(r["population"], r["mutant_id"].split("#")[0])].add(r["QT_allowed"])
development_trials = [r for r in trials.values() if r["population"] == "construction"]
unstable = {
    program
    for (population, program), sets in gate_sets.items()
    if len(sets) > 1 and population == "construction"
} | {r["program"] for r in development_trials if category(r) == "some"}
summary_agrees = (
    len(unstable)
    == trial_summary["construction"]["originals_with_varying_gate_set"]
    == trial_summary["construction"]["originals_failing_own_assertion_some_trial"]
)
equivalent_development = [r for r in canonical if r["final_semantic_status"] == "EQUIVALENT"]
commit_dates = lambda path: [r["committer_date"] for r in commits if r["package_path"] == path]
other_outcome = Counter(r["v2_report"] for r in rows(FINAL[0]) if r["population"] == "prospective")
other_survivors = sum(n for k, n in other_outcome.items() if k != "NA_KILLED")
share = lambda k: f"{other_outcome[k]}/{100 * other_outcome[k] / other_survivors:.1f}"
candidates = {
    p: [r for r in rows(p) if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"] for p in FINAL
}
withdrawn = {p: sum(r["v2_report"] != "CL4" for r in rs) for p, rs in candidates.items()}
exact_fails = [int(r["exact_ref_false_fails"]) for r in guards if int(r["exact_ref_false_fails"]) > 0]
sampled_fails = lambda more_than: sum(int(r["sampled_ref_false_fails"]) > more_than for r in guards)
time_of = lambda name: modified[GUARDS + name]
exposure = adapter_change["outcome_exposure_at_amendment_time"]

VALUES = {
    "V06": "/".join(
        str(flagged(p, c)) for p in ("construction", "prospective") for c in ("HIST_gatelist", "P5_gateset")
    ),
    "V07": (
        f"{len(equivalent_other)}/{separates(equivalent_other, 'gateset')}/"
        f"{separates(equivalent_other, 'depth')}/"
        f"{len(other)}/{separates(other, 'gateset')}"
    ),
    "V08": (
        f"{by_category[('prospective', 'all')]}/{by_category[('prospective', 'some')]}/"
        f"{by_category[('construction', 'all')]}/{by_category[('construction', 'none')]}/"
        f"{by_category[('construction', 'some')]}/"
        f"{all(category(trials[m]) == category(trials_40[m]) for m in trials)}"
    ),
    "V09": (
        f"{sum(1 for r in development_trials if category(r) == 'all' and r['program'] not in unstable)}/"
        f"{len({r['program'] for r in development_trials}) - len(unstable)}/"
        f"{sum(1 for r in development_trials if category(r) == 'all' and r['program'] in unstable)}/"
        f"{sum(1 for r in development_trials if category(r) == 'some')}/"
        f"{len(unstable) if summary_agrees else 'inconsistent'}/"
        f"{trial_summary['prospective']['originals_failing_own_assertion_some_trial']}"
    ),
    "V10": (
        f"{len(equivalent_development)}+{len(equivalent_other)}="
        f"{len(equivalent_development) + len(equivalent_other)}"
    ),
    "V11": f"{len(predictions)}/{max(commit_dates(REGISTRY)) < min(commit_dates(COHORT))}",
    "V12": (
        f"{other_survivors}/{share('CL1')}/{share('CL4')}/"
        f"{other_outcome['Unresolved']}/{other_outcome['CL5']}/{other_outcome['CL3']}"
    ),
    "V13": f"{estimands['V08']['status']}/{estimands['V07']['status']}",
    "V14": f"{sum(r['claim_level_consequence'] == 'True' for r in cross_tool)}/{len(cross_tool)}",
    "V15": (
        f"{sum(map(len, candidates.values()))}/{sum(withdrawn.values())}/"
        f"{len(candidates[FINAL[2]])}/{withdrawn[FINAL[2]]}"
    ),
    "V16": f"{sampled_fails(0)}/{sampled_fails(1)}/{len(exact_fails)}/{max(exact_fails)}",
    "V17": (
        f"{'2000' if 'exact references, N = 2000, R = 12' in guard_plan else 'not found'}/"
        f"{time_of('a1b.log') < time_of('a1b_ext.log') <= time_of('b5_a1c_cl3.py') < time_of('a1c.log')}/"
        f"{'8000' if 'N = 8000' in mutant_run_header else 'not found'}"
    ),
    "V18": (
        f"{'single basis state' in input_change['defect_corrected']['why_wrong'] and 'no external mutant had been natively executed' in input_change['precedence_attestation']}/"
        f"{exposure['aggregate_native_statuses_observed']}/{not exposure['stage2_relations_computed']}"
    ),
}

with open(out_dir() / "protocol_checks.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["check_id", "label", "recomputed", "evidence_level"])
    for cid, value in VALUES.items():
        w.writerow([cid, CATALOGUE[cid]["label"], value, CATALOGUE[cid]["evidence_level"]])
        print(f"{cid}  {value:<28} {CATALOGUE[cid]['label']}")
