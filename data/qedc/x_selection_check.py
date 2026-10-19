"""Release check of the frozen X-basis selection rule for the natural pair (P, M).

The rule (PLAN.md) takes the first instance, in the study's witness order, of the X-basis
distributions whose difference exceeds theta. The witness order of scripts/analytic/r2v_lib.py omits the weight-1 Z
products, which restate the single-qubit marginals on the expectation scale; the full universe U(P) includes them.
The closed order of data/certification/witness_order appends them and selects at n = 2 (native.py, CHANGES.csv).
For n = 2..8 this script prints the selected instance, the largest difference in the witness order, and the largest
difference over the full universe. No execution; ideal states only.
Usage: python -I x_selection_check.py <package root> <run tree> <precalculated_data.json> <out dir>
"""
import sys
from pathlib import Path
import numpy as np
PKG = Path(sys.argv[1]).resolve()
src = open(PKG / "data/qedc/case_run.py").read().split("# ------------------------------------------------------------------ native runner")[0]
g = {"__name__": "x_selection_check"}; exec(src, g)
print("n | selected (kind, key, d) | largest in witness order (kind, key, d) | largest over U(P)")
for n in g["WIDTHS"]:
    sx = {k: g["state"](g["PROG"][k](n, True), n) for k in "PM"}
    ox, alld = g["ordered_universe"](np.abs(sx["P"]) ** 2, np.abs(sx["M"]) ** 2, n)
    xs = next((x for x in ox if g["compare_threshold"](x["d"], g["THETA"]) is g["T"]), None)
    top = max(ox, key=lambda x: x["d"])
    f = lambda x: "none" if x is None else f"{x['kind']} {x['key']} {x['d']:.4f}"
    print(f"{n} | {f(xs)} | {f(top)} | {max(alld):.4f}")
