"""Pass 3C reporting join (no scoring, no threshold): one row per frozen mutant, joining
population/MUTANT_MANIFEST.csv, records/stage_c/{C1_BASELINE,C2_NATIVE,C3_REPORTS,B_BPRIME}.csv and
records/stage_d/{D1_REPAIR,D2_OBSERVATION}.csv as recorded. Writes records/analysis/PASS3C_CASES.csv."""
import csv, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = lambda *p: list(csv.DictReader(open(os.path.join(ROOT, *p))))
man = R("population", "MUTANT_MANIFEST.csv")
b = {r["mutant_id"]: r for r in R("records", "stage_c", "C1_BASELINE.csv")}
c = {r["case"]: r for r in R("records", "stage_c", "C3_REPORTS.csv")}
bb = {r["case"]: r for r in R("records", "stage_c", "B_BPRIME.csv")}
nat = {(r["case"], r["purpose"]): r for r in R("records", "stage_c", "C2_NATIVE.csv")}
d1 = {r["case"]: r for r in R("records", "stage_d", "D1_REPAIR.csv")}
d2 = {r["case"]: r for r in R("records", "stage_d", "D2_OBSERVATION.csv")}
out = []
for m in man:
    k = m["mutant_id"]; C = c.get(k, {}); B = bb.get(k, {}); o13 = nat.get((k, "OB13"), {}); o15 = nat.get((k, "OB15"), {})
    D1 = d1.get(k, {}); D2 = d2.get(k, {})
    out.append({"mutant_id": k, "subject": m["subject"], "family": m["family"], "operator": m["operator"],
                "gate_class": m["gate_class"], "location": m["location"], "parse_excluded": b[k]["excluded"],
                "smin_kills_of_12": b[k].get("kills", ""), "baseline_verdict": b[k].get("native_verdict", ""),
                "v2_candidate": C.get("v2_candidate", ""), "v2_report": C.get("v2_report", ""), "unmet": C.get("unmet", ""),
                "OB02": C.get("final_OB02", ""), "OB03": C.get("OB03", ""), "OB13": C.get("final_OB13", ""), "OB15": C.get("final_OB15", ""),
                "witness_kind": C.get("w_kind", ""), "witness_key": C.get("w_key", ""), "witness_d": C.get("w_d", ""),
                "ob13_kills_of_12": o13.get("kills", ""), "ob13_guard_fails_of_3": o13.get("guard_fails", ""),
                "ob15_kills_of_12": o15.get("kills", ""), "ob15_guard_fails_of_3": o15.get("guard_fails", ""),
                "B_issue": B.get("B_issue", ""), "bound_b13": B.get("b13", ""), "bound_guard": B.get("bgw", ""),
                "Bp_repair_issue": B.get("Bp_repair_issue", ""), "Bp_full_issue": B.get("Bp_full_issue", ""), "C_issue": B.get("C_issue", ""),
                "d1_mutant_kills_of_12": D1.get("mutant_kills", ""), "d1_original_false_failures_of_12": D1.get("original_false_failures", ""),
                "d1_outcome": D1.get("outcome", ""), "d2_operative_rung": D2.get("operative_rung", ""),
                "d2_original_false_failures_of_12": D2.get("original_false_failures", ""), "d2_paired_agreement_of_12": D2.get("paired_agreement", ""),
                "d2_independent_mutant_kills_of_12": D2.get("mutant_independent_kills", ""), "d2_outcome": D2.get("outcome", "")})
with open(os.path.join(ROOT, "records", "analysis", "PASS3C_CASES.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(out), "rows")
