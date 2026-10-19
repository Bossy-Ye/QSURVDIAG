"""Semantic evidence for the TFIM method-2 pair of the QED-C Hamiltonian Simulation benchmark (v2.0.8).
P: the kernel with the coupling stated in the README and used by the stored method-2 references (ZZ rotation
   angle 2*tau*J, J = 1). M: the kernel as shipped (ZZ rotation angle pi*tau, i.e. J = pi/2).
Everything else is identical: GHZ input, K = 5, t = 0.2, h = 1, gate order, every qubit measured in Z.
No sampling. Independent transcription; no upstream code runs; the reference file is read as data.
Usage: python -I tfim_pair.py <precalculated_data.json> [max_n]"""
import json, sys
from math import pi
import numpy as np
from scipy.sparse.linalg import expm_multiply
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp
ref = json.load(open(sys.argv[1])); K, t = ref["k"], ref["t"]; tau = t / K; h = 1.0
NMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 12
def forward(n, zz):
    qc = QuantumCircuit(n); qc.h(0)
    for k in range(1, n): qc.cx(k - 1, k)
    for _ in range(K):
        for i in range(n): qc.rx(2 * tau * h, i)
        for j in range(2):
            for i in range(j % 2, n - 1, 2): qc.cx(i, i + 1); qc.rz(zz, i + 1); qc.cx(i, i + 1)
    return qc
def mirror(n, zz):
    # method 3 without random Paulis: InverseTfim with zz_gate_mirror (the same ZZ angle negated)
    qc = forward(n, zz)
    for _ in range(K):
        for j in range(2):
            for i in range(j % 2, n - 1, 2): qc.cx(i, i + 1); qc.rz(-zz, i + 1); qc.cx(i, i + 1)
        for i in range(n): qc.rx(-2 * tau * h, i)
    return qc
def exact(n):
    terms = [("ZZ", [i, i + 1], 1.0) for i in range(n - 1)] + [("X", [i], h) for i in range(n)]
    H = SparsePauliOp.from_sparse_list(terms, num_qubits=n).to_matrix(sparse=True)
    psi0 = np.zeros(2 ** n, complex); psi0[0] = psi0[-1] = 2 ** -0.5
    return expm_multiply(-1j * t * H, psi0)
def fh(p, q): return float(np.sum(np.sqrt(p * q)) ** 2)
def polar(p, q):  # qedclib polarization rescaling: uniform distribution maps to 0
    u = np.full_like(q, 1 / len(q)); f0 = fh(u, q); return (fh(p, q) - f0) / (1 - f0)
def refvec(d, n):
    v = np.zeros(2 ** n)
    for k, x in d.items(): v[int(k, 2)] = x
    return v / v.sum()
def xbasis(sv, n):
    qc = QuantumCircuit(n); qc.h(range(n)); return np.abs(Statevector(sv).evolve(qc).data) ** 2
P_ZZ, M_ZZ = 2 * tau * 1.0, pi * tau
print("n | |<P|M>|^2 | Z obs: max|dp|, TVD | method 2 (stored ref): F_H P, M; polarization P, M | fidelity to exact e^{-iHt}|GHZ>: P, M"
      " | method 3 return prob: P, M | X-basis obs: TVD(P,M)")
for n in range(2, NMAX + 1):
    sp, sm = Statevector(forward(n, P_ZZ)).data, Statevector(forward(n, M_ZZ)).data
    pp, pm = np.abs(sp) ** 2, np.abs(sm) ** 2; r2 = refvec(ref[f"Exact TFIM - Qubits{n}"], n); e = exact(n)
    ghz = np.zeros(2 ** n, complex); ghz[0] = ghz[-1] = 2 ** -0.5
    m3 = [abs(np.vdot(ghz, Statevector(mirror(n, z)).data)) ** 2 for z in (P_ZZ, M_ZZ)]
    print(n, f"{abs(np.vdot(sp, sm))**2:.4f}", f"| {np.max(np.abs(pp-pm)):.1e} {0.5*np.abs(pp-pm).sum():.1e}",
          f"| {fh(pp, r2):.5f} {fh(pm, r2):.5f} {polar(pp, r2):.5f} {polar(pm, r2):.5f}",
          f"| {abs(np.vdot(e, sp))**2:.4f} {abs(np.vdot(e, sm))**2:.4f}", f"| {m3[0]:.6f} {m3[1]:.6f}",
          f"| {0.5*np.abs(xbasis(sp, n)-xbasis(sm, n)).sum():.3f}")
