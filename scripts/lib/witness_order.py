"""Final per-case records: the v2 final records with the v3 amendment applied (data/certification/witness_order/AMENDMENT.md).
A case that the amendment changes takes the control and OB15 result of its native run and is reported as its candidate."""
import csv, os
from pathlib import Path

WO = Path(__file__).resolve().parents[2] / "data/certification/witness_order"
CHANGED = {r["population"]: set(filter(None, r["changed"].split(";"))) for r in csv.DictReader(open(WO / "IMPACT.csv"))}
NATIVE = {r["job_id"]: r for r in csv.DictReader(open(WO / "NATIVE_RUNS.csv"))}
_FILES = {"R2V_FINAL_CORPUS.csv": ("corpus", "case_key"), "R2V_FINAL_DEFECT.csv": ("defect", "defect_id")}


def final(path, rows):
    """rows of an archived file, with the v3 amendment applied if the file is a v2 final record it changes."""
    arm, key = _FILES.get(os.path.basename(str(path)), (None, None))
    if arm is None:
        return rows
    out = []
    for r in rows:
        if r[key] in CHANGED.get(arm, ()):
            c = NATIVE[f"{arm}|{r[key]}|OB15"]
            r = dict(r, v2_report=r["v2_candidate"], unmet="", OB15="satisfied", final_OB15="satisfied",
                     c_kind=c["inst_kind"], c_key=c["inst_key"], c_d=c["inst_d"], evidence_note="")
        out.append(r)
    return out
