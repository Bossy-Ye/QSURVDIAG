"""Finite-shot coverage under v2 (V2_SPECIFICATION.md sections 6-7), over the 599 primary pairs.

Kill decision. The suite-decisive marginal of each executed shot cell (599_B2_BOUND_FRESH.csv, role
suite_decisive) against the cell's stable native verdict (599_B2_SHOT_FRESH.csv). v2 moves neither
the suite nor R_T, so these rows are read unchanged; coverage is computed at c = 1, at the shot arm's
reference-budget factor c = 1 + N/2000 (Eq. cfactor; its references are 2,000-shot runs of the
original) and at a uniform c = 2.

Witness decision. The analytic surface over every pair and all eighteen (theta, N) schedules. The
decisive assertion follows spec section 6: w* (section 5 order) where an instance outside the
realized suite is decided above theta, and otherwise the largest admitted difference. A Hellinger or
KL decisive assertion is recorded as not covered (section 7). Marginal, probability and Z-product
forms are read at c = 1 and c = 2; the entropy and total-variation forms only at c = 1, since no
sampled-reference form is derived for their bias terms.

Bounds at c = 1 are decision_bound.bound_record (frozen). For c > 1 the Hoeffding exponents are
divided by c, as in build/verify/review_corrections.py. Before use, the frozen bound is checked
against every recorded universe-decisive row. Writes R2V_BOUND.json.
"""
import csv, json, math, os, sys, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T
from qsurvdiag_confirmatory import compare_threshold
from e1_lib import MUT, orig, nq, suite_terms
import e1_relations as REL
sys.path.insert(0, V.QSD + "/confirmatory")
from decision_bound import bound_record, single_repetition_bound

RC = V.PA + "github/results/recovered/"
THETAS = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
NS = [500, 2000, 8000]
R, ALPHA, N0 = 12, 0.05, 2000
FAM = {"marginal": "marginal", "zmask": "observable", "prob": "probability", "entropy": "entropy",
       "tvd": "distribution", "hellinger": None, "kl": None}

def covered(fam, d, theta, N, n, c):
    """True when the unanimity failure bound over R repetitions is at most alpha."""
    if fam is None: return False
    delta = abs(d - theta)
    if c == 1.0:
        rec = bound_record("v2", fam, d, theta, N, R, omega_bits=n if fam in ("distribution", "entropy") else None)
        return rec["supports_conclusion"] is True
    if fam in ("distribution", "entropy") or delta == 0.0: return False
    k = 2.0 if fam in ("marginal", "probability") else 0.5
    return R * min(1.0, 2.0 * math.exp(-k * N * delta * delta / c)) <= ALPHA

def main():
    assert V.spec_unchanged()
    out = {}
    # ---- the frozen bound reproduces every recorded universe-decisive status
    BD = list(csv.DictReader(open(RC + "599_B2_BOUND_FRESH.csv")))
    mism = 0
    for r in BD:
        if r["role"] != "universe_decisive": continue
        rec = bound_record("chk", r["assertion_family"], float(r["d_a"]), float(r["theta"]), int(r["N"]), int(r["R"]),
                           omega_bits=int(r["n"]) if r["assertion_family"] in ("distribution", "entropy") else None)
        mism += rec["bound_status"] != r["bound_status"]
    out["v1_universe_rows_reproduced_mismatches"] = mism
    out["v1_witness_surface"] = {"covered": sum(1 for r in BD if r["role"] == "universe_decisive" and r["bound_status"] == "SUPPORTED"),
                                 "decisions": sum(1 for r in BD if r["role"] == "universe_decisive")}
    # ---- kill decision (read unchanged)
    SH = list(csv.DictReader(open(RC + "599_B2_SHOT_FRESH.csv")))
    stable = {(r["mutant_id"], float(r["theta"]), int(r["N"])): r["agree"] == "True"
              for r in SH if r["native_verdict"] in ("KILLED", "SURVIVED")}
    sdec = {(r["mutant_id"], float(r["theta"]), int(r["N"])): r for r in BD if r["role"] == "suite_decisive"}
    assert {r["assertion_family"] for r in sdec.values()} == {"marginal"}
    def kill_cov(cf):
        cov = {}
        for k in stable:
            x = sdec[k]
            cov[k] = covered("marginal", float(x["d_a"]), float(x["theta"]), int(x["N"]), int(x["n"]), cf(int(x["N"])))
        return cov
    k1, kb, k2 = kill_cov(lambda N: 1.0), kill_cov(lambda N: 1.0 + N / N0), kill_cov(lambda N: 2.0)
    out["kill_decision"] = {
        "stable_cells": len(stable),
        "covered_c1": sum(k1.values()), "covered_c_ref": sum(kb.values()), "covered_c2": sum(k2.values()),
        "disagreements_inside_c1": sum(1 for k, v in k1.items() if v and not stable[k]),
        "disagreements_inside_c_ref": sum(1 for k, v in kb.items() if v and not stable[k]),
        "disagreements_outside_c1": sum(1 for k, v in k1.items() if not v and not stable[k]),
        "gained_at_500_c_ref_vs_c2": sum(1 for k in kb if kb[k] and not k2[k] and k[2] == 500),
        "lost_at_8000_c_ref_vs_c2": sum(1 for k in kb if k2[k] and not kb[k] and k[2] == 8000),
        "lost_cells_disagreeing": sum(1 for k in kb if k2[k] and not kb[k] and not stable[k])}
    # ---- witness decision surface under v2
    surf = {1.0: collections.Counter(), 2.0: collections.Counter()}
    tvd2000 = []
    by_fam = collections.defaultdict(lambda: [0, 0])
    kinds = collections.Counter()
    pairs = sorted(r["mutant_id"] for r in csv.DictReader(open(os.path.join(V.HERE, "R2V_FINAL_PRIMARY.csv"))))
    for mid in pairs:
        m = MUT[mid]; sub = m["subject"]; n = nq[sub]
        pp = np.abs(REL._sv(orig[sub], n)) ** 2; pm = np.abs(REL._sv(m["gates"], n)) ** 2
        ordered, alld = V.ordered_universe(pp, pm, n)
        full = list(ordered) + [{"kind": "zmask", "key": 1 << q, "d": abs((1 - 2 * V.marg(pp, n, q)) - (1 - 2 * V.marg(pm, n, q)))}
                                for q in range(n)]
        assert abs(max(x["d"] for x in full) - max(alld)) < 1e-12 and len(full) == len(alld)
        sk = V.suite_keys_marginals([t[0] for t in suite_terms(sub)["S_MIN"]])
        top = max(full, key=lambda x: x["d"])
        for th in THETAS:
            w = next((x for x in ordered if (x["kind"], x["key"]) not in sk and compare_threshold(x["d"], th) is T), None)
            dec = w if w is not None else top
            kinds[dec["kind"]] += 1
            fam = FAM[dec["kind"]]
            for N in NS:
                for c in (1.0, 2.0):
                    ok = covered(fam, dec["d"], th, N, n, c)
                    surf[c][(th, N)] += ok
                    if c == 1.0:
                        by_fam[dec["kind"]][0] += ok; by_fam[dec["kind"]][1] += 1
                        if dec["kind"] == "tvd" and N == 2000:
                            tvd2000.append({"pair": mid, "n": n, "theta": th, "d": dec["d"],
                                            "delta": abs(dec["d"] - th), "covered": ok,
                                            "floor_N": (2 ** n - 1) / (4 * abs(dec["d"] - th) ** 2) if dec["d"] != th else None})
    out["witness_surface_v2"] = {
        "pairs": len(pairs), "decisions": len(pairs) * len(THETAS) * len(NS),
        "covered_c1": sum(surf[1.0].values()), "covered_c2": sum(surf[2.0].values()),
        "reference_schedule_c1": surf[1.0][(0.05, 2000)], "reference_schedule_c2": surf[2.0][(0.05, 2000)],
        "by_schedule_c1": {f"{th}|{N}": surf[1.0][(th, N)] for th in THETAS for N in NS},
        "by_schedule_c2": {f"{th}|{N}": surf[2.0][(th, N)] for th in THETAS for N in NS},
        "by_decisive_kind_c1": {k: {"covered": v[0], "decisions": v[1]} for k, v in by_fam.items()},
        "decisive_kind_by_pair_theta": dict(kinds),
        "distribution_row_N2000": tvd2000}
    json.dump(out, open(os.path.join(V.HERE, "R2V_BOUND.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items()}, indent=1)[:4500])

if __name__ == "__main__":
    main()
