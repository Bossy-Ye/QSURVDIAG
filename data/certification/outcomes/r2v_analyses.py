"""v2 dependent analyses over the finalized records (V2_SPECIFICATION.md sections 7-8).

Reads R2V_FINAL_*.csv and R2V_TOLERANCE_PRIMARY.csv, and the recorded ledgers the analyses
re-read (native verdicts, suite kills, interface relations). Writes R2V_ANALYSES.json
(every derived count) plus R2V_RQ4_INVARIANCE.csv, R2V_DECISION_GRID.csv and
R2V_ABLATION.csv.
"""
import csv, json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T, F, U
from qsurvdiag_confirmatory import certify, empirical, requirements, candidate

H = V.HERE; G = V.PA + "github/results/"
TRI = {"true": T, "false": F, "undecided": U}
GRID = ["0.01", "0.025", "0.05", "0.1", "0.25", "0.5"]
def rd(p): return list(csv.DictReader(open(p)))
def rh(name): return rd(os.path.join(H, name))

def main():
    assert V.spec_unchanged()
    A = {}
    P = {r["mutant_id"]: r for r in rh("R2V_FINAL_PRIMARY.csv")}
    TOL = rh("R2V_TOLERANCE_PRIMARY.csv")
    # ---- reference condition
    ref = [r for r in P.values() if r["v2_report"] != "NA_KILLED"]
    A["primary_reference"] = dict(collections.Counter(r["v2_report"] for r in ref))
    A["primary_reference_by_population"] = {pop: dict(collections.Counter(r["v2_report"] for r in ref if r["population"] == pop))
                                            for pop in ("construction", "prospective")}
    # ---- tolerance grid: analytic candidates over all 599; decision-supported among survivors
    cand = collections.defaultdict(dict)
    for r in TOL: cand[r["theta"]][r["mutant_id"]] = r
    A["tolerance_cl5_candidates"] = [sum(1 for r in cand[t].values() if r["candidate"] == "CL5") for t in GRID]
    A["tolerance_cl5_resolution_limited"] = [sum(1 for r in cand[t].values() if r["undecided_relation"] == "R_A") for t in GRID]
    A["tolerance_cl5_decision_supported"] = [sum(1 for m, r in cand[t].items() if r["candidate"] == "CL5"
                                                 and P[m]["native_verdict"] == "SURVIVED") for t in GRID]
    inv = [(t, sum(1 for r in cand[t].values() if r["candidate"] == "CL1"),
            sum(1 for m in cand[t] if P[m]["R_S"] == "true" or P[m]["R_C"] == "true"),
            sum(1 for m in cand[t] if P[m]["R_O"] == "true")) for t in GRID]
    A["tolerance_theta_invariant_relations"] = {"R_C_true": sum(1 for r in P.values() if r["R_C"] == "true"),
                                                "R_S_true": sum(1 for r in P.values() if r["R_S"] == "true"),
                                                "R_O_true": sum(1 for r in P.values() if r["R_O"] == "true")}
    # ---- decision grid (shot arm): killed cells stop at the native verdict
    S = rd(G + "recovered/599_B2_SHOT_FRESH.csv"); rows = []
    for s in S:
        c = cand[s["theta"] if s["theta"] in cand else str(float(s["theta"]))][s["mutant_id"]]
        nv = s["native_verdict"]
        if nv == "KILLED": status = "killed"
        elif nv == "SPLIT": status = "unresolved_split"
        elif c["candidate"]: status = "decision_supported"
        else: status = "unresolved_" + (c["undecided_relation"] or "none")
        rows.append({"mutant_id": s["mutant_id"], "theta": s["theta"], "N": s["N"], "native_verdict": nv,
                     "v1_supported_report": s["supported_report"], "v2_candidate": c["candidate"], "v2_status": status,
                     "R_T_v1": s["R_T"], "R_T_v2": c["R_T"]})
    with open(os.path.join(H, "R2V_DECISION_GRID.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    A["decision_grid_by_N"] = {N: dict(collections.Counter(r["v2_status"].split("_")[0] if r["v2_status"].startswith("unresolved")
                                                           else r["v2_status"] for r in rows if r["N"] == N)) for N in ("500", "2000", "8000")}
    A["decision_grid_split_by_N"] = {N: sum(1 for r in rows if r["N"] == N and r["v2_status"] == "unresolved_split") for N in ("500", "2000", "8000")}
    A["decision_grid_R_T_unchanged"] = all(r["R_T_v1"] == r["R_T_v2"] for r in rows)
    A["decision_grid_cells"] = len(rows)
    # ---- evidence ablation over every v2 full certificate
    abl = []; nfull = 0
    arms = {"primary": "R2V_FINAL_PRIMARY.csv", "width": "R2V_FINAL_WIDTH.csv", "corpus": "R2V_FINAL_CORPUS.csv",
            "external": "R2V_FINAL_EXTERNAL.csv", "defect": "R2V_FINAL_DEFECT.csv"}
    for arm, f in arms.items():
        for r in rh(f):
            rep = r["v2_report"]
            if rep not in ("CL1", "CL2", "CL3", "CL4", "CL5"): continue
            nfull += 1
            rel = {k: TRI[r[k]] for k in ("R_C", "R_S", "R_O", "R_A", "R_T")}
            ev = {f"OB{i:02d}": r.get(f"OB{i:02d}", "satisfied") for i in range(1, 20)}
            for k in ("OB02", "OB13", "OB15"):
                if r.get(f"final_{k}"): ev[k] = r[f"final_{k}"]
            for ob in sorted(requirements(rep, rel)):
                for mode in ("unknown", "failed"):
                    e2 = dict(ev); e2[ob] = mode
                    res = certify(rel, e2, empirical_verdict=empirical(int(r["kills"]), int(r["reps"])))
                    abl.append({"arm": arm, "case": r["case_key"], "report": rep, "obligation": ob, "mode": mode,
                                "withdrawn": res["report"] == "Unresolved",
                                "named": ob in (res["failed"] + res["unknown"]),
                                "candidate_unchanged": res["candidate"] == rep})
    with open(os.path.join(H, "R2V_ABLATION.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(abl[0])); w.writeheader(); w.writerows(abl)
    A["ablation"] = {"certificates": nfull, "ablations": len(abl),
                     "all_withdrawn": all(a["withdrawn"] for a in abl), "all_named": all(a["named"] for a in abl),
                     "all_candidate_unchanged": all(a["candidate_unchanged"] for a in abl)}
    # ---- RQ4 invariance (spec 8)
    W = {r["case"]: r for r in rh("R2V_FINAL_WIDTH.csv")}
    pop = {r["case"]: r for r in rd(G + "actionability/B3_ACTIONABILITY_POPULATION.csv")}
    act = {r["case"]: r for r in rd(G + "actionability/B3_ACTIONABILITY_FRESH.csv")}
    b4 = {r["case"]: r for r in rd(G + "actionability/B4_MINIMAL_REPAIR_FRESH.csv")}
    v2_census = {m for m, r in P.items() if r["population"] == "prospective" and r["v2_report"] in ("CL3", "CL4")}
    v2_census |= {c for c, r in W.items() if 8 <= int(r["n"]) <= 10 and r["v2_report"] in ("CL3", "CL4")}
    inv_rows = []
    for c in sorted(set(pop) | v2_census):
        v1 = pop.get(c, {}).get("arm", ""); src = P.get(c) or W.get(c)
        v2 = src["v2_report"] if src else ""
        n = int(src["n"]) if src else None
        stress_ok = (act.get(c, {}).get("rung") == "MAXIMAL" and int(act[c]["assertions"]) == 2 ** (n + 1) + n - 1) if v1 == "CL4" else None
        rep_ok = None
        if v1 == "CL4" and c in b4:
            b = b4[c]; fam = {"marginal": "marginal", "zmask": "observable"}.get(src.get("w_kind"), src.get("w_kind"))
            rep_ok = (b["witness_family"] == fam and abs(float(b["witness_d_a"]) - float(src["w_d"])) < 1e-9)
        cl3_ok = (act.get(c, {}).get("rung", "").startswith("W")) if v1 == "CL3" else None
        inv_rows.append({"case": c, "v1_census": c in pop, "v2_census": c in v2_census, "v1_report": v1, "v2_report": v2,
                         "census_ok": (c in pop) == (c in v2_census), "diagnosis_ok": v1 == v2,
                         "stress_suite_ok": stress_ok, "repair_witness_ok": rep_ok, "cl3_suite_ok": cl3_ok,
                         "unmet": src.get("unmet", "") if src else "",
                         "retained": (c in pop) and (c in v2_census) and v1 == v2 and stress_ok is not False
                                     and rep_ok is not False and cl3_ok is not False,
                         "recorded_outcome": act.get(c, {}).get("outcome", ""), "recorded_repair": b4.get(c, {}).get("outcome", "")})
    with open(os.path.join(H, "R2V_RQ4_INVARIANCE.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(inv_rows[0])); w.writeheader(); w.writerows(inv_rows)
    A["rq4"] = {"v1_census": len(pop), "v2_census": len(v2_census),
                "retained": sum(1 for r in inv_rows if r["retained"]),
                "retained_by_arm": dict(collections.Counter(r["v1_report"] for r in inv_rows if r["retained"])),
                "failures": [(r["case"], r["v1_report"], r["v2_report"], r["unmet"]) for r in inv_rows if not r["retained"]]}
    # ---- secondary arms read against v2 reference sets
    cl3 = {m for m, r in P.items() if r["v2_report"] == "CL3"}; cl4 = {m for m, r in P.items() if r["v2_report"] == "CL4"}
    A1G = rd(G + "recovered/599_B5_A1G_POPULATION.csv")
    k = lambda su, S_: sum(1 for r in A1G if r["suite"] == su and r["mutant_id"] in S_ and r["outcome"] == "KILLED")
    A["suite_arm"] = {su: {"CL3_killed": k(su, cl3), "CL3": len(cl3), "CL4_killed": k(su, cl4), "CL4": len(cl4)}
                      for su in ("S_FAMILY", "S_COVER", "S_BOTH")}
    SS = rd(G + "recovered/T1_4_SSPEC_599.csv"); ssk = {r["mutant_id"]: r["outcome"] for r in SS}
    A["sspec_arm"] = {"CL4_killed": sum(1 for m in cl4 if ssk.get(m) == "KILLED"), "CL4": sum(1 for m in cl4 if m in ssk),
                      "CL3_killed": sum(1 for m in cl3 if ssk.get(m) == "KILLED"), "CL3": sum(1 for m in cl3 if m in ssk)}
    IF = {r["mutant_id"]: r for r in rd(G + "recovered/T1_4_INTERFACE_599.csv")}
    A["interface_matrix"] = {"CL3_same": sum(1 for m in cl3 if IF[m]["R_O_QuCheck"] == "True"),
                             "CL3_different": sum(1 for m in cl3 if IF[m]["R_O_QuCheck"] == "False"),
                             "CL4_same": sum(1 for m in cl4 if IF[m]["R_O_QuCheck"] == "True"),
                             "CL4_different": sum(1 for m in cl4 if IF[m]["R_O_QuCheck"] == "False"),
                             "CL3_muskit_same": sum(1 for m in cl3 if IF[m]["R_O_QUTest"] == "True"),
                             "CL3_pytest_same": sum(1 for m in cl3 if IF[m]["R_O_pytest"] == "True")}
    # ---- contract arm and semantic relations (margins-only; invariance check)
    surv = [r for r in P.values() if r["v2_report"] in ("CL1", "CL2", "CL3", "CL4", "CL5") or r["v1_report"] in ("CL1", "CL2", "CL3", "CL4", "CL5")]
    A["semantic_relations"] = {"R_S_true_among_diagnosed": sum(1 for r in ref if r["R_S"] == "true"),
                               "R_C_true_declared": sum(1 for r in ref if r["R_C"] == "true")}
    X = {r["pair"]: r for r in rh("R2_MARGINS_EXT.csv") if r["arm"] == "primary"}
    A["uniform_unitary_CL1"] = sum(1 for r in ref if r["v2_report"] != "Unresolved" and float(X[r["mutant_id"]]["unitary_margin"]) < V.LO)
    # ---- other arms
    for arm in ("width", "corpus", "external", "defect"):
        A[f"{arm}_reports"] = dict(collections.Counter(r["v2_report"] for r in rh(f"R2V_FINAL_{arm.upper()}.csv")))
    json.dump(A, open(os.path.join(H, "R2V_ANALYSES.json"), "w"), indent=1)
    print(json.dumps(A, indent=1)[:4000])

if __name__ == "__main__":
    main()
