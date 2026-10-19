"""Analytic evaluation time of the two distances v2 adds (V2_SPECIFICATION.md section 10).

Fig. 6(b) shows the recorded v1 run, which enumerated the v1 universe; v2 does not re-measure it.
This script reports, separately, how long the Hellinger and Kullback--Leibler distances take to
evaluate over the two exact distributions of each executed width-set pair, beside the total
variation the v1 universe already held. States are rebuilt from the packaged QASM programs and
their acquisition is not timed. Writes R2V_DISTANCE_TIMING.json (medians per width, in ms).
"""
import json, os, sys, time, statistics, collections, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_relation_corpus import state

PROG = V.PA + "zenodo/inputs/programs/"
REPS = 7

def clock(f, *a):
    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter(); f(*a); ts.append(time.perf_counter() - t0)
    return statistics.median(ts)

def main():
    assert V.spec_unchanged()
    import csv
    W = list(csv.DictReader(open(os.path.join(V.HERE, "R2V_FINAL_WIDTH.csv"))))
    by = collections.defaultdict(lambda: {"tvd": [], "hellinger": [], "kl": []})
    for r in W:
        hits = sorted(glob.glob(PROG + f"*/{r['case']}_origin.qasm"))
        if not hits: continue
        sa, n = state(hits[0]); sb, _ = state(hits[0].replace("_origin.qasm", "_mutant.qasm"))
        assert n == int(r["n"])
        pp, pm = np.abs(sa) ** 2, np.abs(sb) ** 2
        for k, f in (("tvd", V.tvd), ("hellinger", V.hellinger), ("kl", V.kl)):
            by[n][k].append(1000 * clock(f, pm, pp))
    out = {"pairs": sum(len(v["tvd"]) for v in by.values()),
           "median_ms_by_width": {str(n): {k: statistics.median(v[k]) for k in v} | {"pairs": len(v["tvd"])}
                                  for n, v in sorted(by.items())}}
    json.dump(out, open(os.path.join(V.HERE, "R2V_DISTANCE_TIMING.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
