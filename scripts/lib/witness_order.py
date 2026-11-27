"""Outcome records under the closed witness order (data/certification/witness_order/RULE.md).

A case that the closed order changes takes the control of its native run and is reported as its candidate."""

import csv
from pathlib import Path

WO = Path(__file__).resolve().parents[2] / "data/certification/witness_order"
with open(WO / "IMPACT.csv", newline="") as f:
    CHANGED = {r["population"]: set(filter(None, r["changed"].split(";"))) for r in csv.DictReader(f)}
with open(WO / "NATIVE_RUNS.csv", newline="") as f:
    NATIVE = {r["job_id"]: r for r in csv.DictReader(f)}
KEY = {"R2V_FINAL_CORPUS.csv": ("corpus", "case_key"), "R2V_FINAL_DEFECT.csv": ("defect", "defect_id")}


def final(path, rows):
    if Path(path).name not in KEY:
        return rows
    population, key = KEY[Path(path).name]
    out = []
    for r in rows:
        if r[key] in CHANGED.get(population, ()):
            control = NATIVE[f"{population}|{r[key]}|OB15"]
            r = dict(
                r,
                v2_report=r["v2_candidate"],
                unmet="",
                OB15="satisfied",
                final_OB15="satisfied",
                c_kind=control["inst_kind"],
                c_key=control["inst_key"],
                c_d=control["inst_d"],
                evidence_note="",
            )
        out.append(r)
    return out
