"""Every v2 number the manuscript prints, derived from the v2 records (R2V_NUMBERS.json).

Adds to R2V_ANALYSES.json the corpus and width evidence breakdowns, the low-order baseline
over v2 CL4 sets, the excluded-kind sensitivity over v2 CL5 sets, the CL4/CL5 separation
profiles over the full primary population and the corpus, and the endpoint-state effect
groups (tuple keys, so a signed zero cannot split two identical states).
"""
import csv, json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V

H = V.HERE; G = V.PA + "github/results/"
def rh(n): return list(csv.DictReader(open(os.path.join(H, n))))

def main():
    A = json.load(open(os.path.join(H, "R2V_ANALYSES.json")))
    N = {}
    # ---- evidence breakdowns for CL4 candidates, per arm
    nat = {r["job_id"]: r for r in rh("R2V_NATIVE.csv")}
    for arm, f in (("primary", "R2V_FINAL_PRIMARY.csv"), ("width", "R2V_FINAL_WIDTH.csv"),
                   ("corpus", "R2V_FINAL_CORPUS.csv"), ("external", "R2V_FINAL_EXTERNAL.csv")):
        rows = [r for r in rh(f) if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"]
        br = collections.Counter()
        for r in rows:
            if r["v2_report"] == "CL4": br["supported"] += 1; continue
            o13, o15, o02 = r.get("final_OB13"), r.get("final_OB15"), r.get("final_OB02")
            if not r.get("c_kind"): br["no_control"] += 1
            elif o02 == "failed": br["guard_false_failure"] += 1
            elif o13 == "failed": br["witness_split"] += 1
            elif o15 == "failed": br["control_killed"] += 1
            else: br["other:" + r.get("unmet", "")] += 1
        runs = [v for k, v in nat.items() if k.startswith(arm + "|")]
        N[f"{arm}_cl4_candidates"] = len(rows); N[f"{arm}_cl4_breakdown"] = dict(br)
        N[f"{arm}_native_jobs"] = len(runs)
    dnat = rh("R2V_NATIVE_DEFECTS.csv")              # defect 26: witness only, no control can be formed
    N["defect_native_jobs"] = len(dnat)
    N["native_jobs_total"] = len(nat) + len(dnat)
    N["native_qutest_runs"] = sum(len(r["guard_verdicts"].split(";")) + len(r["verdicts"].split(";"))
                                  for r in list(nat.values()) + dnat)
    N["primary_ob13_recorded_reuse"] = sum(1 for r in rh("R2V_FINAL_PRIMARY.csv") if r.get("ob13_source"))
    # ---- low-order baseline over v2 CL4 sets
    CB = rh("R2_CHEAP_BASELINE.csv")
    cor = {r["case_key"]: r for r in rh("R2V_FINAL_CORPUS.csv")}
    T2A = [json.loads(l) for l in open(G + "corpus/T2A_STRATIFIED_RAW.jsonl")]
    keyed = []
    cbc = [r for r in CB if r["arm"] == "corpus"]
    for c, t in zip(cbc, [t for t in T2A if t["diagnostic_outcome"] != "NA_KILLED"]):
        keyed.append((f"{t['case_set']}/{t['pair_id']}", c))
    v2cl4 = {k for k, r in cor.items() if r["v2_report"] == "CL4"}
    N["corpus_v2_cl4_low_order"] = sum(1 for k, c in keyed if k in v2cl4 and c.get("cheap_witness") == "True")
    N["corpus_v2_cl4_higher_order"] = sum(1 for k, c in keyed if k in v2cl4 and c.get("cheap_witness") == "False")
    # QRA_513 is a v2 CL4 whose witness is a distance: not in the v1 cheap-baseline CL4 rows
    N["corpus_v2_cl4_distance_witness"] = sum(1 for k, r in cor.items() if r["v2_report"] == "CL4" and r.get("w_kind") in ("tvd", "hellinger", "kl", "entropy"))
    wid = {r["case_key"]: r for r in rh("R2V_FINAL_WIDTH.csv")}
    N["width_v2_cl4_low_order"] = sum(1 for c in CB if c["arm"] == "width" and wid.get(c["pair"], {}).get("v2_report") == "CL4" and c.get("cheap_witness") == "True")
    N["width_v2_cl4"] = sum(1 for r in wid.values() if r["v2_report"] == "CL4")
    # ---- excluded-kind sensitivity over v2 CL5 sets
    CS = rh("R2_CONDITIONAL_SEPARATIONS.csv")
    for arm, fin in (("corpus", cor), ("width", wid)):
        cl5 = {k for k, r in fin.items() if r["v2_report"] == "CL5"}
        key = (lambda r: f"{r['case_set']}/{r['pair_id']}") if arm == "corpus" else (lambda r: r["pair_id"])
        rows = [r for r in CS if r["arm"] == arm and key(r) in cl5]
        N[f"{arm}_v2_cl5"] = len(cl5)
        N[f"{arm}_v2_cl5_excluded_separate"] = sum(1 for r in rows if r["separated_by_excluded_kinds"] == "True")
        N[f"{arm}_v2_cl5_rare_bit_only"] = sum(1 for r in rows if r["only_rare_bit_separations"] == "True")
        N[f"{arm}_v2_cl5_most_frequent"] = sum(1 for r in rows if r["most_frequent_separates"] == "True")
    # ---- CL4/CL5 separation profiles (recorded measure: max over the v1 families)
    P2 = {r["mutant_id"]: r for r in rh("R2_PRIMARY_PAIRS.csv")}
    prim = {r["mutant_id"]: r for r in rh("R2V_FINAL_PRIMARY.csv")}
    ps = [float(P2[m]["max_U5"]) for m, r in prim.items() if r["v2_report"] in ("CL4", "CL5")]
    tsep = {f"{t['case_set']}/{t['pair_id']}": t["max_universe_separation"] for t in T2A}
    cs = [tsep[k] for k, r in cor.items() if r["v2_report"] in ("CL4", "CL5")]
    cs5 = [tsep[k] for k, r in cor.items() if r["v2_report"] == "CL5"]
    cs4 = [tsep[k] for k, r in cor.items() if r["v2_report"] == "CL4"]
    one = lambda xs: sum(1 for x in xs if abs(x - 1.0) < 1e-9)
    ge1 = lambda xs: sum(1 for x in xs if x > 1.0 - 1e-9)
    N["sep_primary"] = {"cases": len(ps), "exactly_one": one(ps), "at_least_one": ge1(ps), "at_or_below_theta": sum(1 for x in ps if x <= V.THETA)}
    N["sep_corpus"] = {"cases": len(cs), "exactly_one": one(cs), "at_least_one": ge1(cs), "min": min(cs), "at_or_below_theta": sum(1 for x in cs if x <= V.THETA),
                       "largest_cl5_u5": max(cs5), "smallest_cl4_u5": min(cs4)}
    # ---- endpoint-state effect groups (tuple keys)
    import numpy as np
    from e1_lib import MUT, nq
    import e1_relations as REL
    def groups(ids):
        g = set()
        for mid in ids:
            m = MUT[mid]; s = np.round(np.asarray(REL._sv(m["gates"], nq[m["subject"]])), 9)
            g.add((m["subject"], tuple(s)))
        return len(g)
    cl3 = [m for m, r in prim.items() if r["v2_report"] == "CL3"]
    cl2c = [m for m, r in prim.items() if r["v2_report"] == "CL2" and r["population"] == "construction"]
    # ---- decision grid by mutation gate (spec 7): Unresolved share among cells not killed natively
    import math
    def wilson(k, n, z=1.959964):
        p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return [(c - h) / d, (c + h) / d]
    DG = rh("R2V_DECISION_GRID.csv")
    ph = {m for m in {r["mutant_id"] for r in DG} if any(g["gate"] in ("rzz", "rxx") for g in MUT[m]["gates"])}
    bg = {}
    for grp in ("phase", "other"):
        rows8 = [r for r in DG if r["N"] == "8000" and ((r["mutant_id"] in ph) == (grp == "phase"))]
        nk = [r for r in rows8 if r["v2_status"] != "killed"]
        u = sum(1 for r in nk if r["v2_status"].startswith("unresolved"))
        bg[grp] = {"mutants": len({r["mutant_id"] for r in rows8}), "cells_8000": len(rows8), "not_killed": len(nk),
                   "unresolved": u, "share": u / len(nk), "wilson95": wilson(u, len(nk)),
                   "reference_cl3": sum(1 for m in {r["mutant_id"] for r in rows8} if prim[m]["v2_report"] == "CL3")}
    N["decision_grid_by_gate_8000"] = bg
    N["effects_cl3"] = {"cases": len(cl3), "groups": groups(cl3)}
    N["effects_cl2_construction"] = {"cases": len(cl2c), "groups": groups(cl2c)}
    A.update(N)
    json.dump(A, open(os.path.join(H, "R2V_NUMBERS.json"), "w"), indent=1)
    print(json.dumps(N, indent=1))

if __name__ == "__main__":
    main()
