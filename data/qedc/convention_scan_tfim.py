"""Hamiltonian convention check, TFIM variant of the QED-C Hamiltonian Simulation benchmark (v2.0.8, method 1 and 2).
Independent transcription of initial_state('ghz'), Tfim(...) and zz_gate(tau); the reference file is read as data.
Usage: python -I convention_scan_tfim.py <precalculated_data.json>"""
import json, sys
from math import pi
import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp
ref = json.load(open(sys.argv[1])); K, t = ref["k"], ref["t"]; tau = t / K; h = 1.0
def circuit(n):
    qc = QuantumCircuit(n); qc.h(0)
    for k in range(1, n): qc.cx(k - 1, k)
    for _ in range(K):
        for i in range(n): qc.rx(2 * tau * h, i)
        for j in range(2):
            for i in range(j % 2, n - 1, 2): qc.cx(i, i + 1); qc.rz(pi * tau, i + 1); qc.cx(i, i + 1)
    return qc
def exact(n, J):
    terms = [("ZZ", [i, i + 1], J) for i in range(n - 1)] + [("X", [i], h) for i in range(n)]
    H = SparsePauliOp.from_sparse_list(terms, num_qubits=n).to_matrix()
    psi0 = np.zeros(2 ** n, complex); psi0[0] = psi0[-1] = 2 ** -0.5
    return expm(-1j * t * H) @ psi0
def fh(p, q): return float(np.sum(np.sqrt(p * q)) ** 2)
def refvec(d, n, rev=False):
    v = np.zeros(2 ** n)
    for k, x in d.items(): v[int(k[::-1] if rev else k, 2)] = x
    return v / v.sum()
for n in range(2, 9):
    sv = Statevector(circuit(n)).data; pc = np.abs(sv) ** 2
    r1, r2 = refvec(ref[f"TFIM - Qubits{n}"], n), refvec(ref[f"Exact TFIM - Qubits{n}"], n)
    row = [f"n={n}", f"circuit vs ref_m1 F_H {fh(pc, r1):.6f}", f"circuit vs ref_m2 F_H {fh(pc, r2):.6f}"]
    for J, lab in ((1.0, "J=1"), (pi / 2, "J=pi/2")):
        e = exact(n, J); row.append(f"{lab}: state fid {abs(np.vdot(e, sv))**2:.6f}, exact vs ref_m2 F_H {fh(np.abs(e)**2, r2):.6f}")
    print(" | ".join(row))
