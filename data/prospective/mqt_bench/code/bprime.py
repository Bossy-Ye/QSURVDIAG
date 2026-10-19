"""Pass 3C, after Stage C and before Stage D: B and B' recommendations (analytic only).

Population: every v2 CL4 candidate with a stable baseline survival (OB03 satisfied).
B  : issue the named repair (S_MIN + w*) for every candidate.
B' : the frozen finite-shot bound (frozen_deps/decision_bound.py, bound_record unchanged;
     N = 2000, theta = 0.05, alpha = 0.05, c = 1 with analytic references):
     B'-repair issues iff the bound covers the w* kill (R = 12) and the w* guard on the
     original (difference 0, R = 3); B'-full additionally requires c* survival (R = 12) and the
     c* guard (R = 3). Hellinger and KL have no Eq. 4 row and are not covered.
     Family mapping and omega_bits = n follow revision2/r2v_bound.py and PASS2C2.
C  : the v2 report from Stage C (described; scored only against Stage D).
Reads records/stage_c/C3_REPORTS.csv; writes records/stage_c/B_BPRIME.csv. No native run.
"""
import csv, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code")); sys.path.insert(0, os.path.join(ROOT, "frozen_deps"))
import deps; deps.verify()
from decision_bound import bound_record
TH, N, ALPHA = 0.05, 2000, 0.05
FAM = {"marginal": "marginal", "zmask": "observable", "prob": "probability", "entropy": "entropy",
       "tvd": "distribution", "hellinger": None, "kl": None}

def cov(kind, d, R, n):
    fam = FAM[kind]
    if fam is None: return None
    return bound_record("b", fam, d, TH, N, R, omega_bits=n if fam in ("distribution", "entropy") else None,
                        alpha=ALPHA)["supports_conclusion"]

def main(src="stage_c"):
    rows = list(csv.DictReader(open(os.path.join(ROOT, "records", src, "C3_REPORTS.csv"))))
    out = []
    for r in rows:
        if r.get("v2_candidate") != "CL4" or r.get("OB03") != "satisfied": continue
        n = int(r["n"])
        b13 = cov(r["w_kind"], float(r["w_d"]), 12, n) if r["w_kind"] else None
        bgw = cov(r["w_kind"], 0.0, 3, n) if r["w_kind"] else None
        b15 = cov(r["c_kind"], float(r["c_d"]), 12, n) if r["c_kind"] else None
        bgc = cov(r["c_kind"], 0.0, 3, n) if r["c_kind"] else None
        rep = b13 is True and bgw is True
        out.append({"case": r["case"], "subject": r["subject"], "family": r["family"], "w_kind": r["w_kind"],
                    "w_d": r["w_d"], "c_kind": r["c_kind"], "c_d": r["c_d"], "B_issue": True,
                    "b13": b13, "bgw": bgw, "b15": b15, "bgc": bgc, "Bp_repair_issue": rep,
                    "Bp_full_issue": rep and b15 is True and bgc is True,
                    "C_report": r["v2_report"], "C_issue": r["v2_report"] == "CL4"})
    p = os.path.join(ROOT, "records", src, "B_BPRIME.csv")
    if out:
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"CL4 candidates with stable survival: {len(out)}")

if __name__ == "__main__":
    main("dry_run_stage_c" if "--dry-run" in sys.argv else "stage_c")
