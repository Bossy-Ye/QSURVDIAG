"""v2 finalization (V2_SPECIFICATION.md sections 4, 6-8, 11).

Merges the native evidence into the per-arm records, issues every v2 report with the frozen
certify(), and derives: the report distributions, the tolerance and decision grids, the RQ4
invariance checks, the evidence ablation, the secondary-arm recounts and the v1-v2
reprocessing table. Every output is a record in revision2/; figure and table inputs are
generated from these records by r2v_figure_data.py.
"""
import csv, json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T, F, U, THETA
from qsurvdiag_confirmatory import certify, empirical, requirements

H = V.HERE; G = V.PA + "github/results/"
TRI = {"true": T, "false": F, "undecided": U}
OBS = [f"OB{i:02d}" for i in range(1, 20)]

def rd(name): return list(csv.DictReader(open(os.path.join(H, name))))

def native_index():
    idx = {r["job_id"]: r for r in rd("R2V_NATIVE.csv")} if os.path.exists(os.path.join(H, "R2V_NATIVE.csv")) else {}
    if os.path.exists(os.path.join(H, "R2V_NATIVE_DEFECTS.csv")):
        idx.update({r["job_id"]: r for r in rd("R2V_NATIVE_DEFECTS.csv")})
    for r in idx.values():
        for k in ("guard_fails", "guard_unsupported", "kills", "unsupported"): r[k] = int(r[k])
    return idx

def finalize_row(arm, case, row, nat):
    """Spec 4 and 6: the v2 report of one pair."""
    if row.get("v2_report") == "NA_KILLED" or row["native_verdict"] == "KILLED":
        return {"v2_report": "NA_KILLED", "unmet": "", "evidence_note": "stops at the native verdict"}
    cand = row.get("v2_candidate", "")
    if not cand:
        und = row.get("undecided_relation", "")
        return {"v2_report": "Unresolved", "unmet": f"relation {und}", "evidence_note": "no candidate"}
    ev = {k: row.get(k, "unknown") for k in OBS}
    note = ""
    if cand == "CL4":
        r13 = nat.get(f"{arm}|{case}|OB13"); r15 = nat.get(f"{arm}|{case}|OB15")
        if ev["OB13"] != "satisfied":           # not reused from a qualifying recorded run
            ev["OB13"] = V.ob13_status(r13) if r13 is not None else ("pending" if row["OB03"] == "satisfied" else "unknown")
        if not row.get("c_kind"):
            ev["OB15"] = "unknown"; note = "no admissible non-witness assertion outside the suite: control cannot be formed"
        else:
            ev["OB15"] = V.ob15_status(r15) if r15 is not None else ("pending" if row["OB03"] == "satisfied" else "unknown")
        if any(r is not None and r["guard_fails"] for r in (r13, r15)):
            ev["OB02"] = "failed"
    rel = {k: TRI[row[k]] for k in ("R_C", "R_S", "R_O", "R_A", "R_T")}
    res = certify(rel, dict(ev), empirical_verdict=empirical(int(row["kills"]), int(row["reps"])))
    out = {"v2_report": res["report"], "unmet": ";".join(res["failed"] + res["unknown"]) if res["report"] == "Unresolved" else "",
           "evidence_note": note, "required": ";".join(res["required"]),
           **{f"final_{k}": ev[k] for k in ("OB02", "OB13", "OB15")}}
    return out

def arm_rows():
    nat = native_index()
    arms = {"primary": ("R2V_REPORTS_PRIMARY.csv", "mutant_id"), "width": ("R2V_REPORTS_WIDTH.csv", "case"),
            "corpus": ("R2V_REPORTS_CORPUS.csv", "case"), "external": ("R2V_REPORTS_EXTERNAL.csv", "case"),
            "defect": ("R2V_REPORTS_DEFECTS.csv", "defect_id")}
    final = {}
    for arm, (f, key) in arms.items():
        rows = rd(f); out = []
        for r in rows:
            case = r[key]
            if arm == "defect":
                r = dict(r)
                if r.get("v2_candidate") == "CL4" or r["v1_report"] not in ("NA_KILLED",):
                    r.setdefault("kills", r["kills"]); r.setdefault("reps", r["reps"])
                    for k in OBS:
                        r.setdefault(k, "satisfied")
                    r["OB19"] = "satisfied" if V.spec_unchanged() else "failed"
            fin = finalize_row(arm, case, r, nat)
            out.append({**r, **fin, "arm": arm, "case_key": case})
        final[arm] = out
    return final, nat

def main():
    assert V.spec_unchanged()
    final, nat = arm_rows()
    pending = [(a, r["case_key"]) for a, rows in final.items() for r in rows
               if r.get("v2_candidate") == "CL4" and (r.get("final_OB13") == "pending" or r.get("final_OB15") == "pending")]
    if pending:
        print(f"PENDING native evidence for {len(pending)} cases; finalize again after r2v_native.py completes")
    for arm, rows in final.items():
        keys = sorted({k for r in rows for k in r})
        with open(os.path.join(H, f"R2V_FINAL_{arm.upper()}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
        v1 = collections.Counter(r["v1_report"] for r in rows); v2 = collections.Counter(r["v2_report"] for r in rows)
        print(arm, "v1", dict(v1), "\n      v2", dict(v2))
    # reprocessing table: every pair whose report differs between versions
    diff = []
    for arm, rows in final.items():
        for r in rows:
            v1 = r["v1_report"]; v2 = r["v2_report"]
            if v1 != v2:
                diff.append({"arm": arm, "case": r["case_key"], "v1_report": v1, "v2_report": v2,
                             "v2_candidate": r.get("v2_candidate", ""), "unmet": r.get("unmet", ""),
                             "note": r.get("evidence_note", "")})
    with open(os.path.join(H, "R2V_V1_V2_REPROCESSING.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["arm", "case", "v1_report", "v2_report", "v2_candidate", "unmet", "note"])
        w.writeheader(); w.writerows(diff)
    print("pairs whose report differs between v1 and v2:", len(diff), collections.Counter((d["arm"], d["v1_report"], d["v2_report"]) for d in diff))

if __name__ == "__main__":
    main()
