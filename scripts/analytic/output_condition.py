"""Output-condition counterfactual for Simon and Bernstein-Vazirani: the survivors that meet the output
condition of the algorithm although their final state differs from the original's.

Adapted from data/primary/records/b3_output_condition.py: the conditions are those of SSPEC_PROVENANCE.json.
Run by scripts/reproduce_analytic.py in a copy of the study layout."""

import collections, csv, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np

sys.path.insert(0, ".")
sys.path.insert(0, "../cross_tool_stage/qutest")
from e1_lib import MUT, orig, nq, outreg
import e1_relations as REL

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import archived, out_dir

EPS = 1e-9
REFERENCE = archived("data/primary/records/T1_3_REFERENCE_599.csv")


def outdist(gates, sub):
    """Distribution over the declared output register."""
    n = nq[sub]
    p = np.abs(REL._sv(gates, n)) ** 2
    d = collections.Counter()
    for i in np.nonzero(p)[0]:
        key = "".join("1" if (int(i) >> q) & 1 else "0" for q in outreg[sub])
        d[key] += float(p[i])
    return d


def meets(mid):
    sub = MUT[mid]["subject"]
    dm = outdist(MUT[mid]["gates"], sub)
    if sub.startswith("simon"):
        # Simon: uniform over {y : y.s = 0 mod 2} with s = 11, that is "00" and "11" at 0.5 each.
        tgt = {"00": 0.5, "11": 0.5}
        return all(abs(dm.get(k, 0.0) - v) < EPS for k, v in tgt.items()) and all(
            abs(v) < EPS for k, v in dm.items() if k not in tgt
        )
    # Bernstein-Vazirani: the hidden string is recorded nowhere, so the condition is a point mass on the basis
    # state that the original yields.
    do = outdist(orig[sub], sub)
    so = max(do, key=do.get)
    if abs(do[so] - 1.0) >= EPS:
        return False
    return abs(dm.get(so, 0.0) - 1.0) < EPS


with open(REFERENCE) as f:
    ref = {r["mutant_id"]: r for r in csv.DictReader(f)}
pool = [m for m, r in ref.items() if r["subject"].startswith(("simon", "bv")) and r["report"] != "NA_KILLED"]
movers = [m for m in pool if ref[m]["report"] != "CL1" and meets(m)]
out_of = [m for m in pool if ref[m]["report"] == "CL1" and not meets(m)]
by = collections.Counter(ref[m]["report"] for m in movers)
allcl3 = sum(1 for r in ref.values() if r["report"] == "CL3")
print("population 599")
print(f"  simon+bv non-killed        : {len(pool)}")
print(f"  move INTO contract equivalence: {len(movers)}   from {dict(by)}")
print(f"  move OUT of it               : {len(out_of)}")
print(f"  of the movers, CL3           : {by.get('CL3',0)}  of {allcl3} total CL3 reports")
with open(out_dir("analytic") / "outcond_599.json", "w") as f:
    json.dump(
        {
            "population": "599",
            "pool": len(pool),
            "movers": len(movers),
            "out": len(out_of),
            "movers_by_report": dict(by),
            "total_cl3": allcl3,
        },
        f,
        indent=2,
    )
