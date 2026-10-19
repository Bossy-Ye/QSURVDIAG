"""v2 reprocessing, primary population (599 pairs), reference condition and tolerance grid.

Implements V2_SPECIFICATION.md sections 3-8 for the primary arm. Writes
R2V_REPORTS_PRIMARY.csv (one row per pair, reference condition) and
R2V_TOLERANCE_PRIMARY.csv (one row per pair and grid tolerance). OB13 and OB15 are
'pending' wherever section 9 requires a native run; r2v_native.py fills them in.
"""
import csv, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T, F, U, THETA, exists_above
from e1_lib import MUT, orig, nq, outreg, suite_terms
import e1_relations as REL
import e1_07_diagnose as D7

G = V.PA + "github/results/"
GRID = ["0.01", "0.025", "0.05", "0.1", "0.25", "0.5"]

def main():
    assert V.spec_unchanged(), "V2_SPECIFICATION.md changed since its hash"
    E1E = {r["mutant_id"]: r for r in csv.DictReader(open(G + "recovered/599_B5_A1E_REFERENCE_EXACT.csv"))}
    GUARD = {r["subject"]: r for r in csv.DictReader(open(G + "decision/B5_A1B_GUARD_EXACT.csv")) if r["suite"] == "S_MIN"}
    B4 = {r["case"]: r for r in csv.DictReader(open(G + "actionability/B4_MINIMAL_REPAIR_FRESH.csv"))}
    uc, rows, trows = {}, [], []
    for mid in sorted(E1E):
        e = E1E[mid]; m = MUT[mid]; sub = m["subject"]; n = nq[sub]
        sva = REL._sv(orig[sub], n); svb = REL._sv(m["gates"], n)
        pp, pm = np.abs(sva) ** 2, np.abs(svb) ** 2
        ms = abs(abs(np.vdot(sva, svb)) - 1.0); mo = float(np.max(np.abs(pp - pm)))
        contract = D7.CONTRACT[sub]
        if contract in D7.UNITARY_CONTRACTS:
            if sub not in uc: uc[sub] = D7._unitary(orig[sub], n)
            mc = abs(abs(np.trace(uc[sub].conj().T @ D7._unitary(m["gates"], n))) / 2 ** n - 1.0)
        else:
            mc = ms
        ordered, alld = V.ordered_universe(pp, pm, n)
        smin = [t for t in suite_terms(sub)["S_MIN"]]
        sq = [t[0] for t in smin]
        sdiffs = [abs(REL.marginal_p1(pp, n, q) - REL.marginal_p1(pm, n, q)) for q in sq]
        rel = {"R_C": V.eq_decision(mc), "R_S": V.eq_decision(ms), "R_O": V.eq_decision(mo),
               "R_A": exists_above(alld, THETA), "R_T": exists_above(sdiffs, THETA) if sdiffs else F}
        killed = e["exact_ref_native_verdict"] == "KILLED"
        row = {"mutant_id": mid, "subject": sub, "population": e["population"], "n": n,
               "v1_report": e["published_report"], "native_verdict": e["exact_ref_native_verdict"],
               "kills": e["kills"], "reps": e["reps"], "contract": contract,
               "margin_contract": mc, "margin_state": ms, "margin_obs": mo,
               **{k: V.tri_s(v) for k, v in rel.items()}, "universe_size": len(alld)}
        # tolerance grid (spec 7): candidate per grid point
        for th in GRID:
            t = float(th)
            ra, rt = exists_above(alld, t), (exists_above(sdiffs, t) if sdiffs else F)
            relt = dict(rel, R_A=ra, R_T=rt)
            from qsurvdiag_confirmatory import candidate
            cand, _, und = candidate(relt)
            trows.append({"mutant_id": mid, "theta": th, "native_verdict": e["exact_ref_native_verdict"],
                          "candidate": cand or "", "undecided_relation": und or "",
                          "R_A": V.tri_s(ra), "R_T": V.tri_s(rt), "max_admitted_d": max(alld)})
        if killed:
            row.update({"v2_candidate": "", "v2_report": "NA_KILLED"}); rows.append(row); continue
        from qsurvdiag_confirmatory import candidate
        cand, path, und = candidate(rel)
        sk = V.suite_keys_marginals(sq)
        w = V.select(ordered, sk, T) if cand == "CL4" else None
        c = V.select(ordered, sk, F) if cand == "CL4" else None
        grid_ok = [(th, r["candidate"] == cand) for th in GRID for r in [trows[-6 + GRID.index(th)]]]
        dec = (w["d"] if w else None) if cand == "CL4" else (max(alld) if cand == "CL5" else None)
        ev = {"OB01": "satisfied",
              "OB02": "satisfied" if GUARD[sub]["exact_ref_guard"] == "CLEAN" else "failed",
              "OB03": "satisfied" if int(e["kills"]) in (0, int(e["reps"])) else "failed",
              "OB04": "satisfied", "OB05": "satisfied", "OB06": "satisfied", "OB07": "satisfied",
              "OB08": "satisfied", "OB09": "satisfied",
              "OB10": "satisfied" if len(alld) == 2 ** (n + 1) + n + 3 else "failed",
              "OB11": "satisfied" if w is not None else "failed",
              "OB12": "satisfied", "OB14": "satisfied",
              "OB16": ("n/a" if cand not in ("CL4", "CL5") else
                       "satisfied" if dec is not None and abs(dec - THETA) > V.THRESHOLD_RESOLUTION else "failed"),
              "OB17": "satisfied", "OB18": "satisfied", "OB19": "satisfied" if V.spec_unchanged() else "failed",
              "OB13": "pending", "OB15": "pending"}
        ob13_src = ""
        if cand == "CL4" and mid in B4 and e["population"] == "prospective":
            b = B4[mid]
            same = (w is not None and b["witness_family"] == {"marginal": "marginal", "zmask": "observable"}.get(w["kind"])
                    and abs(float(b["witness_d_a"]) - w["d"]) < 1e-9)
            if same and b["outcome"] == "KILLED" and int(b["kills"]) == 12 and b["guard_false_fails"] == "0":
                ev["OB13"] = "satisfied"; ob13_src = "recorded B4 repair (suite + w*, seeds 42-53)"
        row.update({"v2_candidate": cand or "", "undecided_relation": und or "",
                    "w_kind": w["kind"] if w else "", "w_key": w["key"] if w else "", "w_d": w["d"] if w else "",
                    "c_kind": c["kind"] if c else "", "c_key": c["key"] if c else "", "c_d": c["d"] if c else "",
                    "decisive_d": "" if dec is None else dec,
                    "grid_interval": V.grid_interval(grid_ok) if cand else "",
                    "ob13_source": ob13_src, **{k: ev[k] for k in sorted(ev)}})
        rows.append(row)
    keys = sorted({k for r in rows for k in r})
    with open(os.path.join(V.HERE, "R2V_REPORTS_PRIMARY.csv"), "w", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=keys); w_.writeheader(); w_.writerows(rows)
    with open(os.path.join(V.HERE, "R2V_TOLERANCE_PRIMARY.csv"), "w", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=list(trows[0])); w_.writeheader(); w_.writerows(trows)
    import collections
    print("v1 vs v2 candidate:", collections.Counter((r["v1_report"], r.get("v2_candidate", "")) for r in rows))
    print("OB13 reuse:", sum(1 for r in rows if r.get("ob13_source")), " CL4 needing native OB13:",
          sum(1 for r in rows if r.get("v2_candidate") == "CL4" and r.get("OB13") == "pending"))

if __name__ == "__main__":
    main()
