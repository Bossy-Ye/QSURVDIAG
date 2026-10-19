"""Hamiltonian convention check for the QED-C Hamiltonian Simulation benchmark (v2.0.8, Heisenberg, method 2).
Which Hamiltonian convention do (a) the kernel circuit and (b) the stored method-2 references implement?
Builds the circuit from an independent transcription (no upstream code is run); reads the reference file as data.
Usage: python -I convention_scan.py <precalculated_data.json>"""
import json, sys, itertools
from math import pi
import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp
ref = json.load(open(sys.argv[1])); K, t, w = ref["k"], ref["t"], ref["w"]; tau = t / K
def xxyyzz(qc, a, b):
    qc.rz(pi / 2, b); qc.cx(b, a); qc.rz(pi * tau - pi / 2, a); qc.ry(-pi / 2 + pi * tau, b)
    qc.cx(a, b); qc.ry(-pi * tau + pi / 2, b); qc.cx(b, a); qc.rz(-pi / 2, a)
def circuit(n):
    hx, hz = ref["hx"][:n], ref["hz"][:n]; qc = QuantumCircuit(n)
    for k in range(0, n, 2): qc.x(k)
    for _ in range(K):
        for i in range(n): qc.rx(2 * tau * w * hx[i], i)
        for i in range(n): qc.rz(2 * tau * w * hz[i], i)
        for j in range(2):
            for i in range(j % 2, n - 1, 2): xxyyzz(qc, i, i + 1)
    return qc
def exact(n, J, odd_start):
    hx, hz = ref["hx"][:n], ref["hz"][:n]
    terms = [(p + p, [i, i + 1], J) for i in range(n - 1) for p in "XYZ"]
    terms += [("X", [i], w * hx[i]) for i in range(n)] + [("Z", [i], w * hz[i]) for i in range(n)]
    H = SparsePauliOp.from_sparse_list(terms, num_qubits=n).to_matrix()
    psi0 = np.zeros(2 ** n, complex); psi0[sum(1 << k for k in range(1 if odd_start else 0, n, 2))] = 1
    return expm(-1j * t * H) @ psi0
def fh(p, q): return float(np.sum(np.sqrt(p * q)) ** 2)
def refvec(d, n, reverse_keys):
    v = np.zeros(2 ** n)
    for k, x in d.items(): v[int(k[::-1] if reverse_keys else k, 2)] = x
    return v / v.sum()
Js = {"1": 1.0, "-1": -1.0, "pi/2": pi / 2, "-pi/2": -pi / 2}
print("n | best convention for the circuit state (fidelity) | best convention for stored method-2 reference (Hellinger fidelity)")
for n in range(2, 9):
    sv = Statevector(circuit(n)).data
    cands = {(j, o): exact(n, Js[j], o) for j in Js for o in (False, True)}
    cs = max(((abs(np.vdot(v, sv)) ** 2, k) for k, v in cands.items()))
    r2 = ref[f"Exact Heisenberg - Qubits{n}"]
    rs = max(((fh(np.abs(v) ** 2, refvec(r2, n, rk)), k + (rk,)) for k, v in cands.items() for rk in (False, True)))
    r1 = refvec(ref[f"Heisenberg - Qubits{n}"], n, False)
    print(n, f"circuit~exact {cs[0]:.6f} at J={cs[1][0]} odd_start={cs[1][1]}", "|",
          f"ref_m2 {rs[0]:.6f} at J={rs[1][0]} odd_start={rs[1][1]} reversed_keys={rs[1][2]}", "|",
          f"circuit vs ref_m1 F_H {fh(np.abs(sv)**2, r1):.6f}", f"circuit vs ref_m2 F_H {fh(np.abs(sv)**2, refvec(r2, n, False)):.6f}")
