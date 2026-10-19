"""For every primary pair reported as observation limitation (CL3), evaluate every instance of U(P),
including the three distances, from the simulated distributions, and report the largest difference.
Run in artifact/outcomes of the input tree that scripts/reproduce_analytic.py assembles."""
import csv, os, sys
import numpy as np
sys.path.insert(0, os.getcwd())
import r2v_lib as V
from e1_lib import MUT, orig, nq
import e1_relations as REL
rows = [r for r in csv.DictReader(open("R2V_FINAL_PRIMARY.csv")) if r["v2_report"] == "CL3"]
worst = []
for r in rows:
    mid = r["mutant_id"]; m = MUT[mid]; sub = m["subject"]; n = nq[sub]
    pp = np.abs(REL._sv(orig[sub], n)) ** 2; pm = np.abs(REL._sv(m["gates"], n)) ** 2
    ordered, alld = V.ordered_universe(pp, pm, n)
    kind = max(ordered, key=lambda x: x["d"])
    worst.append((max(alld), mid, kind["kind"], float(np.max(np.abs(pp - pm))), r["margin_obs"]))
worst.sort(reverse=True)
print(f"observation-limitation reports among the 599 primary pairs: {len(rows)}")
print(f"largest difference of any of the 2^(n+1)+n+3 instances over these pairs: {worst[0][0]:.3g} ({worst[0][1]}, {worst[0][2]})")
print(f"instances above theta = {V.THETA}: {sum(w[0] > V.THETA for w in worst)}")
print("five largest:", [(f"{w[0]:.2e}", w[1], w[2], f"max|dp| {w[3]:.1e}", f"recorded margin_obs {w[4]}") for w in worst[:5]])
