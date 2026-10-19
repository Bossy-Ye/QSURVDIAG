"""Pass 3C analysis: pre-registered tables (PROTOCOL.md section 7). Descriptive, per subject,
per family and overall; no pooled mutant-level inference. Reads records/stage_c and
records/stage_d; writes records/analysis/ANALYSIS.json.
"""
import csv, collections, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def rd(*p):
    f = os.path.join(ROOT, "records", *p)
    return list(csv.DictReader(open(f))) if os.path.exists(f) else []

def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [round((c - h) / d, 4), round((c + h) / d, 4)]

def main(src_c="stage_c", src_d="stage_d", outdir="analysis"):
    base = rd(src_c, "C1_BASELINE.csv"); rep = rd(src_c, "C3_REPORTS.csv"); bb = rd(src_c, "B_BPRIME.csv")
    d1 = {r["case"]: r for r in rd(src_d, "D1_REPAIR.csv")}; d2 = rd(src_d, "D2_OBSERVATION.csv")
    sub = lambda c: c.split("#")[0]
    fam = {r["case"]: r["family"] for r in rep}
    A = {"P1_diagnosis": {}, "P2_certification": {}, "P3_B_Bprime_C": {}, "P4_observation": {}, "R5_disagreements": {}, "flags": {}}
    for level, key in (("subject", lambda c: sub(c)), ("family", lambda c: fam.get(c, "?")), ("overall", lambda c: "all")):
        t = collections.defaultdict(collections.Counter)
        for b in base:
            k = key(b["mutant_id"]) if level != "family" else fam.get(b["mutant_id"], "excluded/killed")
            t[k]["mutants"] += 1
            t[k]["excluded_parse"] += b["excluded"] == "True"
        for r in rep:
            t[key(r["case"])][r["v2_report"]] += 1
            if r["v2_report"] == "Unresolved": t[key(r["case"])]["unresolved:" + (r.get("unmet") or "")] += 1
        A["P1_diagnosis"][level] = {k: dict(v) for k, v in t.items()}
    cand = [r for r in rep if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"]
    A["P2_certification"] = {"cl4_candidates": len(cand),
                             "certified": sum(r["v2_report"] == "CL4" for r in cand),
                             "withheld_by_unmet": dict(collections.Counter(r.get("unmet", "") for r in cand if r["v2_report"] != "CL4"))}
    for name, issue in (("B", "B_issue"), ("Bprime_repair", "Bp_repair_issue"), ("Bprime_full", "Bp_full_issue"), ("C", "C_issue")):
        c = collections.Counter()
        for r in bb:
            o = d1.get(r["case"], {}).get("outcome", "not_run"); iss = r[issue] == "True"
            c[("issued" if iss else "abstained") + ":" + o] += 1
        A["P3_B_Bprime_C"][name] = dict(c)
    A["P3_B_Bprime_C"]["bound_contradictions"] = [r["case"] for r in bb if r["b13"] == "True"
                                                 and d1.get(r["case"], {}).get("outcome") == "kill_failure"]
    A["D1_by_C_report"] = {f"{a}|{b}": v for (a, b), v in collections.Counter((r["C_report"], d1.get(r["case"], {}).get("outcome", "not_run")) for r in bb).items()}
    A["P4_observation"] = dict(collections.Counter(r["outcome"] for r in d2))
    A["R5_disagreements"] = {
        "certified_not_supported": [(r["case"], d1.get(r["case"], {}).get("outcome")) for r in bb
                                    if r["C_issue"] == "True" and d1.get(r["case"], {}).get("outcome") != "supported_repair"],
        "conservative_C_abstentions": [r["case"] for r in bb if r["C_issue"] != "True"
                                       and d1.get(r["case"], {}).get("outcome") == "supported_repair"]}
    bad1 = sum(r["outcome"] in ("void", "original_false_failure") for r in d1.values())
    bad2 = sum(r["outcome"] in ("void", "suite_invalid_on_fresh_seeds") for r in d2)
    A["flags"] = {"actionability_inconclusive": len(cand) < 10,
                  "observation_validation_absent": len(d2) == 0,
                  "d1_stability_insufficient": bool(d1) and bad1 / len(d1) > 0.25,
                  "d2_stability_insufficient": bool(d2) and bad2 / len(d2) > 0.25,
                  "unresolved_share_over_half": None}
    surv = [r for r in rep if r["v2_report"] != "NA_KILLED"]
    if surv:
        u = sum(r["v2_report"] == "Unresolved" for r in surv)
        A["flags"]["unresolved_share_over_half"] = u / len(surv) > 0.5
        A["flags"]["unresolved_share"] = [u, len(surv), wilson(u, len(surv))]
    os.makedirs(os.path.join(ROOT, "records", outdir), exist_ok=True)
    json.dump(A, open(os.path.join(ROOT, "records", outdir, "ANALYSIS.json"), "w"), indent=1)
    print(json.dumps(A, indent=1)[:3000])

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main("dry_run_stage_c" if dry else "stage_c", "dry_run_stage_d" if dry else "stage_d", "dry_run_analysis" if dry else "analysis")
