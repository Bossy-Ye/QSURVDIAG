"""X4, section 4: outcomes of the later-position samples by population and position, next to the archived outcomes
of the first-rule samples (which are not changed)."""
import collections, csv, gzip, json, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]; D = PKG / "data"
OUT = Path(os.environ.get("QSD_OUT", PKG / "output")) / "position"; OUT.mkdir(parents=True, exist_ok=True)
NAMES = {"NA_KILLED": "killed", "CL1": "contract equivalence", "CL2": "executed-input equality", "CL3": "observation limitation",
         "CL4": "suite omission", "CL5": "below-tolerance difference", "Unresolved": "unresolved"}

rows = [json.loads(l) for l in gzip.open(HERE / "X4_NATIVE_RUNS.jsonl.gz", "rt")]
sel = {r["mutant_id"]: r for r in csv.DictReader(open(HERE / "X4_SELECTION.csv"))}
out = []
for r in rows:
    f = r.get("final", {}); d = r.get("diagnosis", {})
    out.append({"mutant_id": r["mutant_id"], "subject": r["subject"], "population": r["population"], "third": r["third"],
                "location": r["location"], "anchor_index": sel[r["mutant_id"]]["anchor_index"], "stratum": r["stratum"],
                "parse": r["parse"], "kills": d.get("kills", ""), "native_verdict": d.get("native_verdict", ""),
                "candidate": d.get("v2_candidate", ""), "report": f.get("v2_report", "not executed"), "unmet": f.get("unmet", ""),
                "w_kind": d.get("w_kind", ""), "w_key": d.get("w_key", ""), "w_d": d.get("w_d", "")})
with open(OUT / "X4_FINAL.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

# archived first-rule outcomes
first = collections.defaultdict(collections.Counter)
for r in csv.DictReader(open(D / "certification/outcomes/R2V_FINAL_PRIMARY.csv")):
    if r["population"] == "prospective": first["other"][r["v2_report"]] += 1
for r in csv.DictReader(open(D / "certification/outcomes/R2V_FINAL_EXTERNAL.csv")): first["external"][r["v2_report"]] += 1
for r in csv.DictReader(open(D / "prospective/mqt_bench/records/stage_c/C3_REPORTS.csv")): first["mqt"][r["v2_report"]] += 1

summ = {"pairs": len(out), "not_executed": [o["mutant_id"] for o in out if o["report"] == "not executed"], "by_population": {}}
for pop in ("other", "external", "mqt"):
    P = [o for o in out if o["population"] == pop]
    summ["by_population"][pop] = {
        "first_rule_archived": {NAMES.get(k, k): v for k, v in sorted(first[pop].items())},
        "middle": {NAMES.get(k, k): v for k, v in sorted(collections.Counter(o["report"] for o in P if o["third"] == "middle").items())},
        "last": {NAMES.get(k, k): v for k, v in sorted(collections.Counter(o["report"] for o in P if o["third"] == "last").items())},
        "observation_limitation_programs": sorted({o["subject"] for o in P if o["report"] == "CL3"}),
        "suite_omission_distinct_sites": len({(o["subject"], o["anchor_index"]) for o in P if o["report"] == "CL4"}),
        "suite_omission_distinct_witnesses": len({(o["subject"], o["w_kind"], o["w_key"]) for o in P if o["report"] == "CL4"})}
P = [o for o in out if o["population"] == "external" and o["subject"] != "qft_n4"]       # PLAN.md, section 0
summ["external_without_qft_n4"] = {t: {NAMES.get(k, k): v for k, v in sorted(collections.Counter(o["report"] for o in P if o["third"] == t).items())}
                                   for t in ("middle", "last")}
with open(OUT / "X4_NATIVE_RUNS.csv", "w", newline="") as fh:                            # one row per pair
    w = csv.writer(fh); w.writerow(["mutant_id", "subject", "population", "third", "location", "parse", "baseline_verdicts", "native_jobs (job:mutant kills/guard failures)"])
    for r in rows:
        w.writerow([r["mutant_id"], r["subject"], r["population"], r["third"], r["location"], r["parse"], r.get("baseline_verdicts", ""),
                    ";".join(f'{j["job_id"]}:{j["kills"]}/{j["guard_fails"]}' for j in r.get("native_jobs", []))])
json.dump(summ, open(OUT / "X4_SUMMARY.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
