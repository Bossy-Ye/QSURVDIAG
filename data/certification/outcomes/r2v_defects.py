"""v2 reprocessing of the controlled closed-profile defect arm (4 eligible BUGS4Q defects)
and the targeted released-Qiskit CL3 case (V2_SPECIFICATION.md sections 3-9).

The fixed version is the original P and the buggy version the mutant M, over the
translated gate lists the recorded arm executed (e5_translations.json). The realized suite
is S_MIN over the declared output register. A CL4 candidate gets its OB13 and OB15 runs
here; the results also go to R2V_NATIVE.csv.
"""
import csv, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T, F, THETA, exists_above
from qsurvdiag_confirmatory import candidate
from r2v_arms import sv
import r2v_native as N

G = V.PA + "github/results/defects/"

def main():
    assert V.spec_unchanged()
    trans = json.load(open(f"{V.QSD}/confirmatory/e5_translations.json"))
    rows, native_rows = [], []
    for r in csv.DictReader(open(G + "B3_CLOSED_PROFILE_FRESH.csv")):
        d = r["defect_id"]; t = trans[d]; fx, bg = t["fixed"], t["buggy"]
        n = max(fx["num_qubits"], bg["num_qubits"]); outq = sorted({q for q, _ in fx["measurement_map"]})
        og, mg = fx["gate_list"], bg["gate_list"]
        sa, sb = sv(og, n), sv(mg, n); pp, pm = np.abs(sa) ** 2, np.abs(sb) ** 2
        ms = abs(abs(np.vdot(sa, sb)) - 1.0); mo = float(np.max(np.abs(pp - pm)))
        ordered, alld = V.ordered_universe(pp, pm, n)
        sd = [abs(V.marg(pp, n, q) - V.marg(pm, n, q)) for q in outq]
        rel = {"R_C": F if r["R_C"] == "false" else T,   # recorded contract relation (declared output contract)
               "R_S": V.eq_decision(ms), "R_O": V.eq_decision(mo),
               "R_A": exists_above(alld, THETA), "R_T": exists_above(sd, THETA) if sd else F}
        row = {"defect_id": d, "n": n, "v1_report": r["diagnostic_outcome"], "native_verdict": r["native_verdict"],
               "kills": r["kills_recorded"], "reps": r["reps"], "margin_state": ms, "margin_obs": mo,
               "universe_v1": r["universe_size"], "universe_v2": len(alld), **{k: V.tri_s(v) for k, v in rel.items()}}
        if r["native_verdict"] == "KILLED":
            row["v2_report"] = "NA_KILLED"; rows.append(row); continue
        cand, _, und = candidate(rel); row["v2_candidate"] = cand or ""
        if cand == "CL4":
            sk = V.suite_keys_marginals(outq)
            w, c = V.select(ordered, sk, T), V.select(ordered, sk, F)
            row.update({"w_kind": w["kind"], "w_key": w["key"], "w_d": w["d"],
                        "c_kind": c["kind"] if c else "", "c_key": c["key"] if c else "", "c_d": c["d"] if c else ""})
            for purpose, inst in (("OB13", w), ("OB15", c)):
                if inst is None: row[purpose] = "unknown"; continue
                job = {"job_id": f"defect|{d}|{purpose}", "arm": "defect", "case": d, "purpose": purpose, "n": n,
                       "orig_gates": og, "mut_gates": mg, "lines": V.pragmas(inst, n, pp),
                       "inst": {k: inst[k] for k in ("kind", "key", "d")}}
                res = N.run(job); native_rows.append(res)
                row[purpose] = V.ob13_status(res) if purpose == "OB13" else V.ob15_status(res)
        rows.append(row)
    keys = sorted({k for r in rows for k in r})
    with open(os.path.join(V.HERE, "R2V_REPORTS_DEFECTS.csv"), "w", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=keys); w_.writeheader(); w_.writerows(rows)
    with open(os.path.join(V.HERE, "R2V_NATIVE_DEFECTS.csv"), "w", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=N.FIELDS); w_.writeheader(); w_.writerows(native_rows)
    for r in rows: print({k: r.get(k) for k in ("defect_id", "v1_report", "v2_candidate", "universe_v1", "universe_v2", "w_kind", "OB13", "OB15")})

if __name__ == "__main__":
    main()
