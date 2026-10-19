"""Global-X parity of the exact evolution E, the corrected implementation P, the shipped M and the constructed C,
and the overlap of C with E and with P (n = 2..8). Deterministic.
Usage: python -I parity_check.py <package root> <precalculated_data.json>"""
import sys
import numpy as np
from qiskit.quantum_info import SparsePauliOp
pkg, dpath = sys.argv[1:3]
src = open(pkg + "/data/qedc/case_run.py").read().split("# ------------------------------------------------------------------ QED-C score")[0]
sys.argv = ["x", pkg, "/nonexistent", dpath, "/tmp/unused"]
sys.path.insert(0, pkg + "/data/prospective/mqt_bench/frozen_deps")
g = {"__name__": "check"}; exec(src.replace("import qutest_adapter as QA", "QA = None"), g)
print("n | <X^n>: E, P, M, C | |<E|C>|^2 | |<P|C>|^2 | max |p_P - p_C| (Z basis)")
for n in g["WIDTHS"]:
    X = SparsePauliOp("X" * n).to_matrix(sparse=True)
    st = {k: g["state"](g["PROG"][k](n), n) for k in "PMC"}; st["E"] = g["exact"](n)
    par = {k: float(np.real(np.vdot(v, X @ v))) for k, v in st.items()}
    print(n, " ".join(f"{par[k]:+.12f}" for k in "EPMC"), f"| {abs(np.vdot(st['E'], st['C']))**2:.2e} | {abs(np.vdot(st['P'], st['C']))**2:.2e} |",
          f"{np.max(np.abs(np.abs(st['P'])**2 - np.abs(st['C'])**2)):.1e}")
