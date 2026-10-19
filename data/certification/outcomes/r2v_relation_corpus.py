"""Relation-level corpus census under v2 (V2_SPECIFICATION.md section 3).

The recorded census (github/results/scale/B2_CORPUS_FRESH.json) decides R_S and R_O at a single
tolerance of 1e-9 for the 1,569 distinct corpus pairs at two to twenty qubits, 32 of them above
the certification frame. This script recomputes both margins for every pair from the packaged
QASM programs (zenodo/inputs/programs/<set>/, final measurements removed, realized input
|0...0>) and applies the v2 policy: true below 1e-10, false above 1e-8, undecided between.
Each recomputed v1 decision is checked against the recorded row first. Writes
R2V_RELATION_CORPUS.json (per-width CL3-substrate counts under v1 and v2, and every pair whose
decision lies in the guard band).
"""
import json, os, sys, collections
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Statevector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T, F, U

REC = V.PA + "github/results/scale/B2_CORPUS_FRESH.json"
PROG = V.PA + "zenodo/inputs/programs/"
V1_TOL = 1e-9

def state(path):
    qc = qasm2.loads(open(path).read(), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    qc = qc.remove_final_measurements(inplace=False)
    return np.asarray(Statevector.from_instruction(qc).data), qc.num_qubits

def main():
    assert V.spec_unchanged()
    rec = json.load(open(REC))
    rows = rec["rows"]; assert len(rows) == rec["distinct_pairs"] == 1569
    by1, by2 = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    band, mismatch, eq_max, ne_small = [], [], 0.0, []
    comp = {k: {"max_equal": 0.0, "min_different": None, "band": 0} for k in ("state", "obs")}
    for r in rows:
        po = PROG + f"{r['set']}/{r['origin']}"
        pm = po.replace("_origin.qasm", "_mutant.qasm")
        sa, n = state(po); sb, _ = state(pm)
        assert n == r["n"]
        ms = abs(abs(np.vdot(sa, sb)) - 1.0)
        mo = float(np.max(np.abs(np.abs(sa) ** 2 - np.abs(sb) ** 2)))
        if (ms < V1_TOL) != r["R_S"] or (mo < V1_TOL) != r["R_O"]:
            mismatch.append((r["set"], r["origin"], ms, mo))
        ds, do = V.eq_decision(ms), V.eq_decision(mo)
        for m, d in ((ms, ds), (mo, do)):
            if d is T: eq_max = max(eq_max, m)
        for k, m, d in (("state", ms, ds), ("obs", mo, do)):
            c = comp[k]
            if d is T: c["max_equal"] = max(c["max_equal"], m)
            elif d is F: c["min_different"] = m if c["min_different"] is None else min(c["min_different"], m)
            else: c["band"] += 1
        if (ds is F and ms < 1e-6) or (do is F and mo < 1e-6):
            ne_small.append({"set": r["set"], "pair": r["origin"].replace("_origin.qasm", ""), "n": n,
                             "state_margin": ms, "obs_margin": mo, "v1_substrate": r["substrate"]})
        if ds is U or do is U:
            band.append({"set": r["set"], "pair": r["origin"].replace("_origin.qasm", ""), "n": n,
                         "state_margin": ms, "obs_margin": mo, "v1_substrate": r["substrate"]})
        sub2 = ("undecided" if (ds is U or do is U) else
                "CL3_SUBSTRATE" if (ds is F and do is T) else
                "EQUIVALENT_NO_MEASUREMENT_SEPARATES" if ds is T else "OBSERVABLE_IN_Z")
        by1[n][r["substrate"]] += 1; by2[n][sub2] += 1
    widths = sorted(by1)
    out = {"pairs": len(rows), "v1_recomputation_mismatches": mismatch,
           "cl3_substrate": {"v1": sum(by1[w]["CL3_SUBSTRATE"] for w in widths),
                             "v2": sum(by2[w]["CL3_SUBSTRATE"] for w in widths)},
           "undecided_v2": sum(by2[w]["undecided"] for w in widths),
           "band_pairs": band,
           "max_margin_decided_equal": eq_max,
           "by_comparison": comp,
           "decided_different_below_1e-6": ne_small,
           "min_margin_decided_different": min([min(x for x in (b["state_margin"], b["obs_margin"]) if x > V.HI)
                                                 for b in ne_small], default=None),
           "by_width": {str(w): {"pairs": sum(by1[w].values()), "cl3_v1": by1[w]["CL3_SUBSTRATE"],
                                 "cl3_v2": by2[w]["CL3_SUBSTRATE"], "undecided_v2": by2[w]["undecided"]}
                        for w in widths},
           "shares_v2": {"n<=7": [sum(by2[w]["CL3_SUBSTRATE"] for w in widths if w <= 7),
                                  sum(sum(by2[w].values()) for w in widths if w <= 7)],
                         "n>=8": [sum(by2[w]["CL3_SUBSTRATE"] for w in widths if w >= 8),
                                  sum(sum(by2[w].values()) for w in widths if w >= 8)]}}
    json.dump(out, open(os.path.join(V.HERE, "R2V_RELATION_CORPUS.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("by_width",)}, indent=1))

if __name__ == "__main__":
    main()
