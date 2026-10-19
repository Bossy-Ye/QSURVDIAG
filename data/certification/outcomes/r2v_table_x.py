"""Table X under v2 (V2_SPECIFICATION.md sections 3 and 7): every row from v2 decisions or re-read ledgers.

Observation rows: the lattice's own observation (frozen dists() of
qsurvcert_pilot/confirmatory/definitive_rerun_599/b1_observation_599.py, copied verbatim)
over the 193 construction survivors. Each R_O is decided by the v2 policy (spec 3) on the
margin max_a max |D_P,a - D_M,a| over the profile's basis assignments a; R_S is the v2
decision of R2V_FINAL_PRIMARY.csv.
Interface rows: QUTest (joint Z distribution over all qubits), QuCheck (single-qubit X, Y and
Z expectations on every qubit; margins of R2_MARGINS_EXT.csv) and pytest (endpoint state up to
a global phase), decided by the v2 policy for all 599 primary pairs.
Suite rows: native kill outcomes of the recorded suite runs. v2 changes no execution, so they
are re-read, not recomputed.
Shot-budget row: R2V_STATISTICS.json.
Each recomputed v1 decision is checked against its ledger before its margin is used, and each
row is compared with the recorded 599-pair record (T_TABLE_IX_599.json,
T_TABLE_IX_OBSERVATION_599.json). Writes R2V_TABLE_X.json and R2V_TABLE_X_DECISIONS.csv.
"""
import csv, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T, F, U
from r2v_stats import mcnemar, boot, loco
from e1_lib import MUT, nq, outreg
import e1_relations as REL

H = V.HERE; RC = V.PA + "github/results/recovered/"; B1 = V.PA + "manuscript/tse/batch1/"
V1_TOL = 1e-9

# ---- frozen observation definition (b1_observation_599.py, verbatim)
Hm  = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
SDG = np.array([[1, 0], [0, -1j]], dtype=complex)
ROT = {"Z": np.eye(2, dtype=complex), "X": Hm, "Y": Hm @ SDG}

def apply1(state, n, q, U_):
    t = state.reshape([2] * n)
    t = np.moveaxis(t, n - 1 - q, 0).reshape(2, -1)
    return np.moveaxis((U_ @ t).reshape([2] * n), 0, n - 1 - q).reshape(-1)

def dists(state, n, Q, basis):
    cur = {(): state}
    for q in Q:
        nxt = {}
        for pref, st in cur.items():
            for b in basis:
                nxt[pref + (b,)] = st if b == "Z" else apply1(st, n, q, ROT[b])
        cur = nxt
    out = {}
    for asg, st in cur.items():
        p = np.abs(st) ** 2
        d = np.zeros(2 ** len(Q))
        for idx in np.nonzero(p)[0]:
            key = 0
            for k, q in enumerate(Q):
                if (idx >> q) & 1: key |= (1 << k)
            d[key] += p[idx]
        out[asg] = d
    return out

PROFILES = [("Z_output", ("Z",), "sub"), ("Z_all", ("Z",), "all"),
            ("XYZ_output", ("X", "Y", "Z"), "sub"), ("XYZ_all", ("X", "Y", "Z"), "all")]
EDGES = [("Z_output", "Z_all", "Z: output -> all qubits"), ("Z_output", "XYZ_output", "output: Z -> XYZ"),
         ("Z_all", "XYZ_all", "all qubits: Z -> XYZ"), ("XYZ_output", "XYZ_all", "XYZ: output -> all qubits")]

def stat(d, cl):
    b, c = sum(1 for x in d if x == 1), sum(1 for x in d if x == -1)
    lo, hi = boot(d, cl); l1, l2 = loco(d, cl)
    return {"units": len(d), "clusters": len(set(cl)), "pos": b, "neg": c, "effect": sum(d) / len(d),
            "exact_mcnemar_p": mcnemar(b, c), "cluster_ci95": [lo, hi], "loco_range": [l1, l2]}

def tri(v): return V.tri_s(v)

def main():
    assert V.spec_unchanged()
    out, dec_rows, checks = {}, [], {}
    P = {r["mutant_id"]: r for r in csv.DictReader(open(os.path.join(H, "R2V_FINAL_PRIMARY.csv")))}
    ref = {r["mutant_id"]: r for r in csv.DictReader(open(RC + "599_B1_REFERENCE_RERUN_FRESH.csv"))}
    lat = {r["mutant_id"]: r for r in csv.DictReader(open(RC + "599_B1_OBSERVATION_RERUN.csv"))}
    # ---------------------------------------------------------------- observation lattice
    pop = sorted(m for m, r in ref.items() if r["population"] == "construction" and r["native_verdict"] == "SURVIVED")
    assert len(pop) == 193 and set(pop) == set(lat)
    cl3 = {}; v1_mismatch = 0; band = []; rtol_only = []
    for mid in pop:
        sub = MUT[mid]["subject"]; n = nq[sub]
        sva, _, _ = REL._orig_cache(sub); svb = REL._sv(MUT[mid]["gates"], n)
        rs = P[mid]["R_S"]
        rec = {"mutant_id": mid, "subject": sub, "n": n, "R_S_v2": rs}
        for name, basis, scope in PROFILES:
            Q = outreg[sub] if scope == "sub" else list(range(n))
            Do, Dm = dists(sva, n, Q, basis), dists(svb, n, Q, basis)
            m = max(float(np.max(np.abs(Do[a] - Dm[a]))) for a in Do)
            v1 = all(np.allclose(Do[a], Dm[a], atol=V1_TOL) for a in Do)      # frozen v1 comparison
            if ("true" if v1 else "false") != lat[mid][f"R_O_{name}"]: v1_mismatch += 1
            if v1 and m >= V1_TOL: rtol_only.append((mid, name, m))          # true only through allclose's rtol
            d2 = V.eq_decision(m)
            if d2 is U: band.append((mid, name, m))
            rec[f"margin_{name}"] = m; rec[f"R_O_v1_{name}"] = lat[mid][f"R_O_{name}"]; rec[f"R_O_v2_{name}"] = tri(d2)
            cl3[(mid, name)] = (T if (rs == "false" and d2 is T) else
                                F if (rs == "true" or d2 is F) else U)
        dec_rows.append({"part": "observation", **rec})
    checks["observation_v1_recomputation_mismatches"] = v1_mismatch
    checks["observation_band_decisions"] = band
    checks["observation_true_only_through_rtol"] = rtol_only
    rec_obs = {r["edge"]: r for r in json.load(open(B1 + "T_TABLE_IX_OBSERVATION_599.json"))}
    out["observation"] = []
    for a, b, label in EDGES:
        und = [m for m in pop if cl3[(m, a)] is U or cl3[(m, b)] is U]
        d = [int(cl3[(m, a)] is T) - int(cl3[(m, b)] is T) for m in pop]
        cl = [MUT[m]["subject"] for m in pop]
        s = stat(d, cl); s.update({"edge": label, "undecided_units": len(und),
                                   "cl3_from": sum(1 for m in pop if cl3[(m, a)] is T),
                                   "cl3_to": sum(1 for m in pop if cl3[(m, b)] is T)})
        r = rec_obs[label]
        s["matches_record"] = (s["pos"] == r["leave"] and s["neg"] == r["enter"] and s["units"] == r["pairs"]
                               and f"[{s['cluster_ci95'][0]:.3f}, {s['cluster_ci95'][1]:.3f}]" == r["ci95"]
                               and f"[{s['loco_range'][0]:.3f}, {s['loco_range'][1]:.3f}]" == r["loco"])
        out["observation"].append(s)
    # ---------------------------------------------------------------- interface
    IF = {r["mutant_id"]: r for r in csv.DictReader(open(RC + "T1_4_INTERFACE_599.csv"))}
    QX = {r["pair"]: r for r in csv.DictReader(open(os.path.join(H, "R2_MARGINS_EXT.csv"))) if r["arm"] == "primary"}
    assert len(IF) == 599 and set(IF) == set(QX)
    ro = {}; if_mis = 0; if_band = []
    for mid in sorted(IF):
        sub = MUT[mid]["subject"]; n = nq[sub]
        sva, pa, _ = REL._orig_cache(sub); svb = REL._sv(MUT[mid]["gates"], n); pb = REL.probs(svb)
        mq = float(np.max(np.abs(pa - pb)))
        mp = abs(abs(np.vdot(sva, svb)) - 1.0)
        mc = float(QX[mid]["qucheck_all_margin"])
        rec = {"mutant_id": mid, "subject": sub, "n": n}
        for tool, m, col in (("QUTest", mq, "R_O_QUTest"), ("QuCheck", mc, "R_O_QuCheck"), ("pytest", mp, "R_O_pytest")):
            if ("True" if m < V1_TOL else "False") != IF[mid][col]: if_mis += 1
            d2 = V.eq_decision(m)
            if d2 is U: if_band.append((mid, tool, m))
            ro[(mid, tool)] = d2
            rec[f"margin_{tool}"] = m; rec[f"R_O_v1_{tool}"] = IF[mid][col]; rec[f"R_O_v2_{tool}"] = tri(d2)
        dec_rows.append({"part": "interface", **rec})
    checks["interface_v1_recomputation_mismatches"] = if_mis
    checks["interface_band_decisions"] = if_band
    rec_tab = {r["contrast"]: r for r in json.load(open(B1 + "T_TABLE_IX_599.json"))}
    ids = sorted(IF); clI = [IF[m]["subject"] for m in ids]
    out["interface"] = []
    for tool, contrast in (("QuCheck", "QUTest -> QuCheck"), ("pytest", "QUTest -> pytest")):
        # +1: the new interface distinguishes a pair QUTest cannot (gained); -1: the reverse (lost)
        d = [int(ro[(m, "QUTest")] is T and ro[(m, tool)] is F) - int(ro[(m, "QUTest")] is F and ro[(m, tool)] is T) for m in ids]
        s = stat(d, clI); s["contrast"] = contrast
        s["undecided_units"] = sum(1 for m in ids if ro[(m, "QUTest")] is U or ro[(m, tool)] is U)
        r = rec_tab[contrast]
        s["matches_record"] = (s["pos"] == r["pos"] and s["neg"] == r["neg"] and s["units"] == r["pairs"]
                               and f"[{s['cluster_ci95'][0]:.3f}, {s['cluster_ci95'][1]:.3f}]" == r["ci95"]
                               and f"[{s['loco_range'][0]:.3f}, {s['loco_range'][1]:.3f}]" == r["loco"])
        out["interface"].append(s)
    out["interface_muskit_discordant"] = 0     # Muskit reads the same joint Z distribution as QUTest
    # ---------------------------------------------------------------- suites (re-read)
    A1G = list(csv.DictReader(open(RC + "599_B5_A1G_POPULATION.csv")))
    k = {(r["suite"], r["mutant_id"]): r["outcome"] == "KILLED" for r in A1G}
    sub = {r["mutant_id"]: r["subject"] for r in A1G}
    base = sorted(m for (su, m) in k if su == "S_MIN")
    out["suite"] = []
    for su in ("S_FAMILY", "S_COVER", "S_BOTH"):
        d = [int(k[(su, m)]) - int(k[("S_MIN", m)]) for m in base]
        s = stat(d, [sub[m] for m in base]); s["contrast"] = f"S_MIN -> {su}"
        r = rec_tab[s["contrast"]]
        s["matches_record"] = (s["pos"] == r["pos"] and s["neg"] == r["neg"] and s["units"] == r["pairs"]
                               and f"[{s['cluster_ci95'][0]:.3f}, {s['cluster_ci95'][1]:.3f}]" == r["ci95"]
                               and f"[{s['loco_range'][0]:.3f}, {s['loco_range'][1]:.3f}]" == r["loco"])
        out["suite"].append(s)
    SS = list(csv.DictReader(open(RC + "T1_4_SSPEC_599.csv")))
    d = [int(r["outcome"] == "KILLED") - int(k[("S_MIN", r["mutant_id"])]) for r in SS]
    s = stat(d, [r["subject"] for r in SS]); s["contrast"] = "S_MIN -> S_SPEC"
    r = rec_tab["S_MIN -> S_SPEC"]
    s["matches_record"] = (s["pos"] == r["pos"] and s["neg"] == r["neg"] and s["units"] == r["pairs"]
                           and f"[{s['cluster_ci95'][0]:.3f}, {s['cluster_ci95'][1]:.3f}]" == r["ci95"]
                           and f"[{s['loco_range'][0]:.3f}, {s['loco_range'][1]:.3f}]" == r["loco"])
    out["suite"].append(s)
    # ---------------------------------------------------------------- shot budget (v2)
    st = json.load(open(os.path.join(H, "R2V_STATISTICS.json")))
    out["budget"] = {"v2": st["v2"], "v1_recomputed": st["v1_recomputed"],
                     "v1_matches_record": st["v1_recomputed"]["resolved"] == rec_tab["N: 500 -> 8000"]["pos"]
                     and st["v1_recomputed"]["created"] == rec_tab["N: 500 -> 8000"]["neg"]}
    out["checks"] = checks
    json.dump(out, open(os.path.join(H, "R2V_TABLE_X.json"), "w"), indent=1)
    keys = sorted({kk for r in dec_rows for kk in r})
    with open(os.path.join(H, "R2V_TABLE_X_DECISIONS.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(dec_rows)
    print(json.dumps({kk: v for kk, v in out.items() if kk != "checks"}, indent=1)[:5000])
    print("checks:", json.dumps({kk: (v if not isinstance(v, list) else len(v)) for kk, v in checks.items()}))

if __name__ == "__main__":
    main()
