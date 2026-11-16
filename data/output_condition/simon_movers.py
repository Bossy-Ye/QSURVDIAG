"""Which pairs does the RQ2 output-condition contract (scripts/analytic/output_condition.py, `meets`) make
contract-equivalent? Same predicate, applied to the 599-pair records; prints the Simon and BV movers.
Run in artifact/outcomes of the input tree that scripts/reproduce_analytic.py assembles."""
import csv, os, sys, collections
import numpy as np
sys.path.insert(0, os.getcwd())
import r2v_lib  # noqa: F401  (puts the frozen study modules on the path)
from e1_lib import MUT, orig, nq, outreg
import e1_relations as REL
EPS = 1e-9
def outdist(gates, sub):
    n = nq[sub]; p = np.abs(REL._sv(gates, n)) ** 2; d = collections.Counter()
    for i in np.nonzero(p)[0]: d["".join("1" if (int(i) >> q) & 1 else "0" for q in outreg[sub])] += float(p[i])
    return d
def meets(mid):
    sub = MUT[mid]["subject"]; dm = outdist(MUT[mid]["gates"], sub)
    if sub.startswith("simon"):
        tgt = {"00": 0.5, "11": 0.5}
        return all(abs(dm.get(k, 0.0) - v) < EPS for k, v in tgt.items()) and all(abs(v) < EPS for k, v in dm.items() if k not in tgt)
    do = outdist(orig[sub], sub); so = max(do, key=do.get)
    return abs(do[so] - 1.0) < EPS and abs(dm.get(so, 0.0) - 1.0) < EPS
for r in csv.DictReader(open("R2V_FINAL_PRIMARY.csv")):
    if r["subject"].startswith(("simon", "bv")) and r["v2_report"] not in ("NA_KILLED", "CL1") and meets(r["mutant_id"]):
        print(r["mutant_id"], r["v2_report"], r["w_kind"], r["w_key"])
