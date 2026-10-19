"""Effect of the closed witness order (AMENDMENT.md) on every population, from the v2 final records and the v3
native runs. Standard library only.
Usage: python3 audit.py <package root> <out csv>     (archived output: IMPACT.csv)

A v2 selection is the first instance of the v2 order; appending instances leaves it first in the v3 order, so a
selection can change only where the v2 record has none. Reports change only where an unmet requirement is
met by a v3 native run.
"""
import csv, sys
from pathlib import Path
PKG, OUTP = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
R2, V3 = PKG / "data/certification/outcomes", PKG / "data/certification/witness_order"
MQT = PKG / "data/prospective/mqt_bench/records/analysis/PASS3C_CASES.csv"
rows = lambda p: list(csv.DictReader(open(p)))
nat = {r["job_id"]: r for r in rows(V3 / "NATIVE_RUNS.csv")}

def v3_report(arm, case, r):
    """Spec 4: the candidate is reported when every requirement holds; v3 supplies OB15 where v2 formed no control."""
    ob15 = nat.get(f"{arm}|{case}|OB15")
    if r["v2_report"] == "Unresolved" and r["unmet"] == "OB15" and r["final_OB13"] == "satisfied" and ob15:
        assert nat[f"{arm}|{case}|OB13"]["status"] == "satisfied"
        return r["v2_candidate"] if ob15["status"] == "satisfied" else "Unresolved"
    return r["v2_report"]

out = []
for arm, f, key in (("primary", "R2V_FINAL_PRIMARY.csv", "case_key"), ("width", "R2V_FINAL_WIDTH.csv", "case_key"),
                    ("corpus", "R2V_FINAL_CORPUS.csv", "case_key"), ("external", "R2V_FINAL_EXTERNAL.csv", "case_key"),
                    ("defect", "R2V_FINAL_DEFECT.csv", "defect_id")):
    cand = [r for r in rows(R2 / f) if r.get("v2_candidate") == "CL4"]
    v3 = [v3_report(arm, r[key], r) for r in cand]
    out.append({"population": arm, "candidates": len(cand), "v2_witnesses": sum(1 for r in cand if r["w_kind"]),
                "v2_controls": sum(1 for r in cand if r["c_kind"]),
                "v3_controls_formed": sum(1 for r in cand if not r["c_kind"] and f"{arm}|{r[key]}|OB15" in nat),
                "v2_reported": sum(1 for r in cand if r["v2_report"] == "CL4"), "v3_reported": v3.count("CL4"),
                "changed": ";".join(r[key] for r, x in zip(cand, v3) if x != r["v2_report"])})
mq = [r for r in rows(MQT) if r["v2_candidate"] == "CL4"]
out.append({"population": "mqt", "candidates": len(mq), "v2_witnesses": sum(1 for r in mq if r["witness_kind"]),
            "v2_controls": sum(1 for r in mq if r["OB15"] != "unknown" and r["ob15_kills_of_12"] != ""),
            "v3_controls_formed": 0, "v2_reported": sum(1 for r in mq if r["v2_report"] == "CL4"),
            "v3_reported": sum(1 for r in mq if r["v2_report"] == "CL4"), "changed": ""})
for r in out:
    assert r["v2_witnesses"] == r["candidates"] and r["v2_controls"] + r["v3_controls_formed"] == r["candidates"], r
with open(OUTP, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator="\n"); w.writeheader(); w.writerows(out)
for r in out: print(r)
