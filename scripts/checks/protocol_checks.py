"""Record-level recomputation of 13 values, including git and file-time facts read from
provenance/git_commit_records.csv and provenance/source_manifest.csv. The two transpilation-based values are read
from the structural records; scripts/reproduce_analytic.py recomputes them with Qiskit.
"""
import collections, csv, json, re, sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import orig, out_dir, ROOT
import witness_order as wo

rd = lambda p: wo.final(p, list(csv.DictReader(open(orig(p)))))
OUT = []
def chk(cid, label, value, level):
    OUT.append({"check_id": cid, "label": label, "recomputed": value, "evidence_level": level})

# V06 historical gate-list comparison and registered fixed-basis audit (archived structural records)
SD = rd("data/structural/records/STRUCTURAL_DEFINITIONS.csv")
cnt = lambda pop, key: sum(r[key] == "True" for r in SD if r["population"] == pop)
chk("V06", "gate-list difference and fixed-basis gate-set difference: construction / prospective",
    f"{cnt('construction', 'HIST_gatelist')}/{cnt('construction', 'P5_gateset')}/{cnt('prospective', 'HIST_gatelist')}/{cnt('prospective', 'P5_gateset')}",
    "archived structural records (recomputed in analytic tier)")
# V07 registered audit, recorded per case
ADM = rd("data/prospective/cross_tool/s3/S3_QUTEST_ADMISSIBILITY.csv")
ce = [r for r in ADM if r["contract_equivalent"] == "True"]; oth = [r for r in ADM if r["contract_equivalent"] != "True"]
chk("V07", "registered audit: CE controls / gate set / depth / other mutants / gate set among them",
    f"{len(ce)}/{sum(r['gateset_separates'] == 'True' for r in ce)}/{sum(r['depth_separates'] == 'True' for r in ce)}/{len(oth)}/{sum(r['gateset_separates'] == 'True' for r in oth)}",
    "per-case records")
# V08-V09 QUTest gate-set check trials and guard-aware split
V = {t: {r["mutant_id"]: r for r in rd(f"data/structural/records/QUTEST_GATESET_VARIABILITY{t}.csv")} for t in ("", "_T40")}
cat = lambda r: "a" if r["separated_trials"] == r["trials"] else ("n" if r["separated_trials"] == "0" else "s")
c20 = collections.Counter((r["population"], cat(r)) for r in V[""].values())
same = all(cat(V[""][x]) == cat(V["_T40"][x]) for x in V[""])
chk("V08", "QUTest check flags: prospective every/some trials; construction every/none/some; categories equal at 20 and 40 trials",
    f"{c20[('prospective', 'a')]}/{c20[('prospective', 's')]}/{c20[('construction', 'a')]}/{c20[('construction', 'n')]}/{c20[('construction', 's')]}/{same}",
    "per-case trial records")
summ = json.load(open(orig("data/structural/records/QUTEST_GATESET_VARIABILITY_SUMMARY.json")))
allowed = collections.defaultdict(set)
for r in SD: allowed[(r["population"], r["mutant_id"].split("#")[0])].add(r["QT_allowed"])
unst = {p for (pop, p), v in allowed.items() if len(v) > 1 and pop == "construction"} | {r["program"] for r in V[""].values() if r["population"] == "construction" and cat(r) == "s"}
cons = [r for r in V[""].values() if r["population"] == "construction"]
valid = [r for r in cons if cat(r) == "a" and r["program"] not in unst]
ok_sets = len(unst) == summ["construction"]["originals_with_varying_gate_set"] == summ["construction"]["originals_failing_own_assertion_some_trial"]
chk("V09", "consistently guard-valid construction flags / stable programs / unstable always / unstable some / unstable programs / prospective self-failing originals",
    f"{len(valid)}/{len({r['program'] for r in cons}) - len(unst)}/{sum(1 for r in cons if cat(r) == 'a' and r['program'] in unst)}/"
    f"{sum(1 for r in cons if cat(r) == 's')}/{len(unst) if ok_sets else 'inconsistent'}/{summ['prospective']['originals_failing_own_assertion_some_trial']}",
    "per-case trial records + per-program summary")
led52 = [r for r in rd("data/structural/CANONICAL_RESULT_LEDGER.csv") if r["final_semantic_status"] == "EQUIVALENT"]
chk("V10", "contract-equivalent among the 546: construction + prospective", f"{len(led52)}+{len(ce)}={len(led52) + len(ce)}", "per-case records")
# V11 registered predictions, committed before the cohort (recorded git history)
base = open(orig("data/prospective/registration/CLAIM_DECISION_BASELINE.md")).read()
ids = sorted(set(re.findall(r"^\| (P\d+) \|", base, re.M)), key=lambda x: int(x[1:]))
GC = list(csv.DictReader(open(ROOT / "provenance/git_commit_records.csv")))
tb = max(r["committer_date"] for r in GC if r["package_path"] == "data/prospective/registration/CLAIM_DECISION_BASELINE.md")
ts = min(r["committer_date"] for r in GC if r["package_path"] == "data/prospective/cross_tool/s2/S2_COHORT_HASH.txt")
chk("V11", "registered predictions / last registry commit precedes cohort commit", f"{len(ids)}/{tb < ts}", "recorded git history")
# V12 registered shares and counts (revised analysis, prospective set)
FIN = rd("data/certification/outcomes/R2V_FINAL_PRIMARY.csv"); pro = collections.Counter(r["v2_report"] for r in FIN if r["population"] == "prospective")
surv = sum(v for kk, v in pro.items() if kk != "NA_KILLED")
chk("V12", "prospective survivors / CL1 / % / CL4 / % / Unresolved / below-tolerance / OL",
    f"{surv}/{pro['CL1']}/{100 * pro['CL1'] / surv:.1f}/{pro['CL4']}/{100 * pro['CL4'] / surv:.1f}/{pro['Unresolved']}/{pro['CL5']}/{pro['CL3']}", "per-case records")
est = {r["estimand"]: r for r in rd("data/prospective/cross_tool/s4/S4_VALIDATION_ESTIMANDS.csv")}
chk("V13", "frozen statuses of V08 (P10) and V07 (P8)", f"{est['V08']['status']}/{est['V07']['status']}", "frozen decision record")
XT = rd("data/prospective/cross_tool/s3/S3_CROSS_TOOL_RESULTS.csv")
chk("V14", "P7: survivors whose permitted report differs / survivors", f"{sum(r['claim_level_consequence'] == 'True' for r in XT)}/{len(XT)}", "per-case records")
cand = conf = 0; corp = (0, 0)
for a in ("PRIMARY", "WIDTH", "CORPUS", "EXTERNAL", "DEFECT"):
    v = [r for r in rd(f"data/certification/outcomes/R2V_FINAL_{a}.csv") if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"]
    cand += len(v); conf += sum(r["v2_report"] == "CL4" for r in v)
    if a == "CORPUS": corp = (len(v), len(v) - sum(r["v2_report"] == "CL4" for r in v))
chk("V15", "SO candidates / withdrawn / corpus candidates / corpus withdrawn", f"{cand}/{cand - conf}/{corp[0]}/{corp[1]}", "per-case records")
GE = rd("data/primary/suite_guards/B5_A1B_GUARD_EXACT.csv")
e = [int(r["exact_ref_false_fails"]) for r in GE if int(r["exact_ref_false_fails"]) > 0]
chk("V16", "suite-cell guards: sampled any / sampled >1 of 12 / analytic any / max analytic failures",
    f"{sum(int(r['sampled_ref_false_fails']) > 0 for r in GE)}/{sum(int(r['sampled_ref_false_fails']) > 1 for r in GE)}/{len(e)}/{max(e)}", "per-case records")
MT = {r["package_path"]: r["original_mtime_utc"] for r in csv.DictReader(open(ROOT / "provenance/source_manifest.csv"))}
t = lambda f: MT["data/primary/suite_guards/" + f]
plan = open(orig("data/primary/suite_guards/SUITE_GUARD_PLAN.md")).read()
chk("V17", "registered N / guard-only extension before mutant run (recorded file times) / mutant-run N",
    f"{'2000' if 'exact references, N = 2000, R = 12' in plan else 'not found'}/"
    f"{t('a1b.log') < t('a1b_ext.log') <= t('b5_a1c_cl3.py') < t('a1c.log')}/"
    f"{'8000' if 'N = 8000' in open(orig('data/primary/suite_guards/a1c.log')).readline() else 'not found'}", "protocol record + recorded file times")
v3 = json.load(open(orig("data/external/protocol/EXTERNAL_COHORT_FREEZE_v3.json")))
v4 = json.load(open(orig("data/external/protocol/EXTERNAL_COHORT_FREEZE_v4.json")))
ox = v4["outcome_exposure_at_amendment_time"]
chk("V18", "external v3 input change before execution / v4 adapter after aggregate statuses / no comparison computed",
    f"{'single basis state' in v3['defect_corrected']['why_wrong'] and 'no external mutant had been natively executed' in v3['precedence_attestation']}/"
    f"{ox['aggregate_native_statuses_observed']}/{not ox['stage2_relations_computed']}", "protocol record")

with open(out_dir() / "protocol_checks.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["check_id", "label", "recomputed", "evidence_level"]); w.writeheader(); w.writerows(OUT)
for r in OUT: print(f"{r['check_id']}  {r['recomputed']:<28} {r['label']}")
