"""Ties in the 'largest admitted difference' fallback of r2v_bound.py, the cause of the unprinted witness-surface
differences of analytic check A06 (tie_check.out: the maximum is attained by more than one kind in 1,273 of 1,324 cells).
Run in artifact/outcomes of the input tree that scripts/reproduce_analytic.py assembles, in its environment."""
import csv, os, sys, collections
import numpy as np
sys.path.insert(0, os.getcwd())
import r2v_lib as V
from r2v_lib import T
from qsurvdiag_confirmatory import compare_threshold
from e1_lib import MUT, orig, nq, suite_terms
import e1_relations as REL
THETAS = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
pairs = sorted(r["mutant_id"] for r in csv.DictReader(open("R2V_FINAL_PRIMARY.csv")))
fallback = tied = 0; kinds = collections.Counter(); examples = []
for mid in pairs:
    m = MUT[mid]; sub = m["subject"]; n = nq[sub]
    pp = np.abs(REL._sv(orig[sub], n)) ** 2; pm = np.abs(REL._sv(m["gates"], n)) ** 2
    ordered, _ = V.ordered_universe(pp, pm, n)
    full = list(ordered) + [{"kind": "zmask", "key": 1 << q, "d": abs((1 - 2 * V.marg(pp, n, q)) - (1 - 2 * V.marg(pm, n, q)))} for q in range(n)]
    sk = V.suite_keys_marginals([t[0] for t in suite_terms(sub)["S_MIN"]])
    top = max(x["d"] for x in full)
    near = {x["kind"] for x in full if abs(x["d"] - top) <= 1e-12}
    for th in THETAS:
        w = next((x for x in ordered if (x["kind"], x["key"]) not in sk and compare_threshold(x["d"], th) is T), None)
        if w is None:
            fallback += 1
            if len(near) > 1:
                tied += 1; kinds[tuple(sorted(near))] += 1
                if len(examples) < 5: examples.append((mid, th, top, sorted(near)))
print(f"(pair, theta) cells using the largest-difference fallback: {fallback}")
print(f"  of these, cells whose maximum is attained within 1e-12 by instances of more than one kind: {tied}")
print("  tied kind sets:", dict(kinds)); print("  examples:", examples)
