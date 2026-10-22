"""PLAN.md, section 5 (Q3): native QuCheck detections on pairs of the 20 circuits against the predictions of the
simulated profile comparison; control false detections; step-down Holm as a sensitivity analysis."""
import collections, csv, gzip, json, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", HERE.parents[1] / "output")) / "developer_suites"; OUT.mkdir(parents=True, exist_ok=True)
ALPHA = 0.05
d = json.load(gzip.open(HERE / "X2_QUCHECK_20_RUNS.json.gz", "rt"))
runs = collections.defaultdict(list)
for r in d["runs"]:
    runs[(r["pair"], r["role"])].append(r)


def holm_step_down(p):
    """Detected when the smallest p-value is at most alpha/m (a step-down procedure rejects nothing otherwise)."""
    return bool(p) and min(p) <= ALPHA / len(p)


PRED = {"only_qucheck": True, "only_qutest": False, "transfer_WITNESS_EXISTS": True, "transfer_NO_WITNESS_ABOVE_THETA": False}
rows = []
for pair, labels in sorted(d["labels"].items()):
    m, c = runs[(pair, "mutant")], runs[(pair, "control")]
    assert len(m) == len(c) == 12, pair
    rows.append({"pair": pair, "labels": ";".join(labels), "detected": sum(x["detected"] for x in m),
                 "detected_holm": sum(holm_step_down(x["p_values"]) for x in m),
                 "control_detected": sum(x["detected"] for x in c), "control_detected_holm": sum(holm_step_down(x["p_values"]) for x in c)})
with open(OUT / "X2_QUCHECK_20.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

summ = {}
for lab, pred in PRED.items():
    R = [r for r in rows if lab in r["labels"].split(";")]
    summ[lab] = {"pairs": len(R), "predicted_detected": pred,
                 "detected_12_of_12": sum(r["detected"] == 12 for r in R), "detected_0_of_12": sum(r["detected"] == 0 for r in R),
                 "split": sum(0 < r["detected"] < 12 for r in R),
                 "as_predicted": sum((r["detected"] == 12) if pred else (r["detected"] == 0) for r in R),
                 "holm_detected_12_of_12": sum(r["detected_holm"] == 12 for r in R), "holm_detected_0_of_12": sum(r["detected_holm"] == 0 for r in R)}
ctrl = sum(r["control_detected"] for r in rows); ctrl_h = sum(r["control_detected_holm"] for r in rows)
summ["controls"] = {"runs": 12 * len(rows), "false_detections": ctrl, "false_detections_holm": ctrl_h}
neg = [r for r in rows if any(l in ("only_qutest", "transfer_NO_WITNESS_ABOVE_THETA") for l in r["labels"].split(";"))]
summ["not_distinguished_runs"] = {"pairs": len(neg), "runs": 12 * len(neg), "detections": sum(r["detected"] for r in neg),
                                  "detections_holm": sum(r["detected_holm"] for r in neg)}
json.dump(summ, open(OUT / "X2_Q3_SUMMARY.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
