"""Condition B (semantic only): over the same Z counts, does any instance of the study's original-centred
universe (marginals, Z products, basis-state probabilities, entropy, TV, Hellinger, KL) separate the TFIM pair
(P: coupling J = 1 as specified; M: shipped kernel, J = pi/2) at theta = 0.05? And in the X basis?
Usage: python -I tfim_pair_universe.py <r2v_lib.py> [max_n]"""
import ast, sys
from math import pi
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
src = ast.parse(open(sys.argv[1]).read()); ns = {"np": np}
for node in src.body:
    if isinstance(node, ast.FunctionDef) and node.name in ("marg", "zexp", "shannon_bits", "tvd", "hellinger", "kl", "ordered_universe"):
        exec(compile(ast.Module([node], []), "r2v_lib", "exec"), ns)
K, t, h = 5, 0.2, 1.0; tau = t / K; NMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 10
def forward(n, zz, xbasis=False):
    qc = QuantumCircuit(n); qc.h(0)
    for k in range(1, n): qc.cx(k - 1, k)
    for _ in range(K):
        for i in range(n): qc.rx(2 * tau * h, i)
        for j in range(2):
            for i in range(j % 2, n - 1, 2): qc.cx(i, i + 1); qc.rz(zz, i + 1); qc.cx(i, i + 1)
    if xbasis: qc.h(range(n))
    return np.abs(Statevector(qc).data) ** 2
for n in range(2, NMAX + 1):
    out = []
    for xb in (False, True):
        pp, pm = forward(n, 2 * tau, xb), forward(n, pi * tau, xb)
        ordered, alld = ns["ordered_universe"](pp, pm, n)
        top = max(ordered, key=lambda x: x["d"]); first = next((x for x in ordered if x["d"] > 0.05), None)
        out.append(f"{'X' if xb else 'Z'} basis: max d {top['d']:.4f} ({top['kind']} {top['key']}), first above 0.05: "
                   + (f"{first['kind']} {first['key']} d={first['d']:.4f}" if first else "none"))
    print(f"n={n} | " + " | ".join(out))
