"""The QED-C metrics computed with the pinned upstream functions (qedclib/metrics.py, v2.0.8:
uniform_dist, hellinger_fidelity_with_expected, rescale_fidelity, polarization_fidelity, extracted verbatim by
ast), on the same noiseless Aer count histograms the case runner used (AerSimulator, seed_simulator = 8042..8053,
QA._counts), for P, M and C at 100 and 2,000 shots; also the ideal (exact-probability) values. Reports the raw
Hellinger fidelity (`hf_fidelity`) and the normalized score (`fidelity`) separately, and checks that the runner's
reimplementation gives the same values. No QUTest run.
Usage: python -I qedc_metrics_pinned.py <package root> <run tree> <metrics.py> <precalculated_data.json> <out json>"""
import ast, json, sys
import numpy as np
pkg, tree, mpath, dpath, outp = sys.argv[1:6]
src = open(pkg + "/data/qedc/case_run.py").read()
sys.argv = ["x", pkg, tree, dpath, "/tmp/unused"]
g = {"__name__": "metrics"}; exec(src.split("# ------------------------------------------------------------------ assertion text")[0], g)
ns = {"np": np}
for node in ast.parse(open(mpath).read()).body:
    if isinstance(node, ast.FunctionDef) and node.name in ("uniform_dist", "hellinger_fidelity_with_expected", "rescale_fidelity", "polarization_fidelity"):
        exec(compile(ast.Module([node], []), "metrics", "exec"), ns)
pf = ns["polarization_fidelity"]
out = []
for n in g["WIDTHS"]:
    ref = g["refdist"](n)
    for prog in "PMC":
        gates = g["PROG"][prog](n); p = np.abs(g["state"](gates, n)) ** 2
        ideal = pf({format(i, f"0{n}b"): float(p[i]) for i in range(2 ** n) if p[i] > 0}, ref)
        row = {"n": n, "program": prog, "ideal_hf_fidelity": ideal["hf_fidelity"], "ideal_fidelity": ideal["fidelity"]}
        for shots in (100, 2000):
            vals = [pf(g["QA"]._counts(gates, n, shots, sd), ref) for sd in g["VAL_ORIG"]]
            mine = [g["qedc_polarization"](g["QA"]._counts(gates, n, shots, sd), ref, n) for sd in g["VAL_ORIG"]]
            assert all(abs(a["fidelity"] - b[0]) < 1e-12 and abs(a["hf_fidelity"] - b[1]) < 1e-12 for a, b in zip(vals, mine))
            row[f"hf_fidelity_{shots}_mean"] = float(np.mean([v["hf_fidelity"] for v in vals]))
            row[f"fidelity_{shots}_mean"] = float(np.mean([v["fidelity"] for v in vals]))
            row[f"fidelity_{shots}_range"] = [float(min(v["fidelity"] for v in vals)), float(max(v["fidelity"] for v in vals))]
        out.append(row)
        print(n, prog, {k: (round(v, 5) if isinstance(v, float) else [round(x, 4) for x in v] if isinstance(v, list) else v) for k, v in row.items() if k not in ("n", "program")})
json.dump(out, open(outp, "w"), indent=1)
print("reimplementation identical to the pinned functions on every histogram")
