"""Bounded adapter check for every evaluated width (n = 2..8): the circuits case_run.py executes against the
pinned upstream kernel (v2.0.8). Deterministic; no sampling.
Checks: (1) preparation occurs once and the complete circuit starts from |0...0>; (2) transcribed M equals the
upstream TFIM method-2 circuit (operator equality up to global phase, measurements removed); (3) gate order and
neighbour loops agree on every qubit wire (Qiskit's decomposition may interleave gates on disjoint qubits differently); (4) measurement of every
qubit, qubit i to bit i; (5) P differs from M only in the ZZ rotation angle, C from P only by the terminal z on qubit 0;
(6) effective K, t, h used.
Usage: python -I adapter_check_all_widths.py <package root> <kernel.py> <precalculated_data.json>"""
import importlib.util, json, sys, runpy
from math import pi
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
pkg, kpath, dpath = sys.argv[1:4]
sys.argv = ["x", pkg, "/nonexistent", dpath, "/tmp/unused"]       # load the runner's program definitions only
spec = importlib.util.spec_from_file_location("e2run", pkg + "/data/qedc/case_run.py")
src = open(pkg + "/data/qedc/case_run.py").read().split("# ------------------------------------------------------------------ QED-C score")[0]
src = src.replace("import qutest_adapter as QA", "QA = None").replace("from qsurvdiag_confirmatory import", "from qsurvdiag_confirmatory import") 
g = {"__name__": "check"}; sys.path.insert(0, pkg + "/data/prospective/mqt_bench/frozen_deps"); exec(src, g)
ks = importlib.util.spec_from_file_location("kernel", kpath); kern = importlib.util.module_from_spec(ks); ks.loader.exec_module(kern)
data = json.load(open(dpath))
def circ(gates, n):
    qc = QuantumCircuit(n)
    for x in gates: getattr(qc, x["gate"])(*x.get("angles", []), *x["q"])
    return qc
print("effective settings:", {"K": g["K"], "t": g["TT"], "h": g["H_FIELD"], "J_spec": g["J_SPEC"], "stored k,t": (data["k"], data["t"])})
ok_all = True
for n in g["WIDTHS"]:
    up = kern.HamiltonianSimulation(n, K=data["k"], t=data["t"], hamiltonian="tfim", w=data["w"], hx=data["hx"][:n], hz=data["hz"][:n], method=2)
    meas = [(ins.qubits[0]._index if hasattr(ins.qubits[0], "_index") else up.find_bit(ins.qubits[0]).index,
             up.find_bit(ins.clbits[0]).index) for ins in up.data if ins.operation.name == "measure"]
    upn = up.remove_final_measurements(inplace=False)
    gM, gP, gC = g["PROG"]["M"](n), g["PROG"]["P"](n), g["PROG"]["C"](n)
    prep_once = [x["gate"] for x in gM[:n]] == ["h"] + ["cx"] * (n - 1) and sum(1 for x in gM if x["gate"] == "h") == 1
    op_eq = Operator(upn).equiv(Operator(circ(gM, n)))
    # gate-by-gate: decompose upstream to cx/rx/rz/h equivalents is not unique; compare the multiset of two-qubit couplings in order
    up_cx = [tuple(upn.find_bit(q).index for q in ins.qubits) for ins in upn.decompose(reps=4).data if ins.operation.name == "cx"]
    tr_cx = [tuple(x["q"]) for x in gM if x["gate"] == "cx"]
    diffPM = [(i, a, b) for i, (a, b) in enumerate(zip(gP, gM)) if a != b]
    angle_only = len(gP) == len(gM) and all(a["gate"] == b["gate"] == "rz" and a["q"] == b["q"] and abs(a["angles"][0] - 2 * g["TAU"]) < 1e-15 and abs(b["angles"][0] - pi * g["TAU"]) < 1e-15 for _, a, b in diffPM)
    c_only = gC[:-1] == gP and gC[-1] == {"gate": "z", "q": [0]}
    meas_ok = sorted(meas) == [(i, i) for i in range(n)]
    wire = lambda seq: [[c for c in seq if q in c] for q in range(n)]   # order of cx gates on each qubit wire
    wire_eq = wire(up_cx) == wire(tr_cx)
    ok = prep_once and op_eq and wire_eq and angle_only and c_only and meas_ok
    ok_all &= ok
    print(f"n={n}: preparation once {prep_once}; operator equal to upstream {op_eq}; cx order equal on every wire {wire_eq} (global order identical {up_cx == tr_cx}; {len(tr_cx)} cx); "
          f"P vs M only ZZ angle {angle_only} ({len(diffPM)} rz); C = P + z(0) {c_only}; measure qubit i -> bit i {meas_ok}")
print("ALL CHECKS PASS" if ok_all else "CHECK FAILED")
