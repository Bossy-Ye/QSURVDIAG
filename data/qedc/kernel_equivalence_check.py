"""Inspect the circuits the pinned QED-C kernel actually constructs (v2.0.8) and check that the study's
transcriptions equal them. Loads only the kernel file (imports qiskit, numpy, math) from the pinned checkout; no
benchmark driver, analysis or execution code runs.
Usage: python -I kernel_equivalence_check.py <kernel.py> <precalculated_data.json>"""
import importlib.util, json, sys
from math import pi
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
spec = importlib.util.spec_from_file_location("qedc_kernel", sys.argv[1]); kern = importlib.util.module_from_spec(spec); spec.loader.exec_module(kern)
ref = json.load(open(sys.argv[2])); K, t, w = ref["k"], ref["t"], ref["w"]; tau = t / K
def transcription(n, zz):
    qc = QuantumCircuit(n); qc.h(0)
    for k in range(1, n): qc.cx(k - 1, k)
    for _ in range(K):
        for i in range(n): qc.rx(2 * tau, i)
        for j in range(2):
            for i in range(j % 2, n - 1, 2): qc.cx(i, i + 1); qc.rz(zz, i + 1); qc.cx(i, i + 1)
    return qc
for n in (2, 4, 6):
    up = kern.HamiltonianSimulation(n, K=K, t=t, hamiltonian="tfim", w=w, hx=ref["hx"][:n], hz=ref["hz"][:n], method=2)
    up_nom = up.remove_final_measurements(inplace=False)
    ops = {g.operation.name for g in up_nom.data}
    s_up = Statevector(up_nom).data; s_tr = Statevector(transcription(n, pi * tau)).data
    print(f"tfim n={n}: upstream gates {sorted(ops)}; |<upstream|shipped transcription>|^2 = {abs(np.vdot(s_up, s_tr))**2:.12f}; "
          f"measured qubits {up.num_clbits}; depth {up.depth()}")
    # K and t passed to the kernel do change the circuit; the driver, however, always passes the stored k and t
    up2 = kern.HamiltonianSimulation(n, K=K + 1, t=t, hamiltonian="tfim", w=w, hx=ref["hx"][:n], hz=ref["hz"][:n], method=2)
    print(f"   kernel with K+1 differs from K: {not np.allclose(Statevector(up2.remove_final_measurements(inplace=False)).data, s_up)}")
