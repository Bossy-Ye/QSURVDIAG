"""Generate and convert the four frozen subjects (Pass 3B). Original programs only.

Environment: .venv-mqt-bench-230 (mqt.bench 2.3.0, qiskit 2.5.2; env/requirements-mqt.lock).
Conversion: the external-cohort convention -- qiskit.transpile to the mutation enumerator's
vocabulary (MUT.ARITY), optimization_level 0, seed_transpiler 0, measurements removed.
Declared input for the multipliers: the external-cohort two-basis-state preparation
(r2_external.prep_gates), with x_a = (a=1, b=1, out=0) and x_b = (a=2^k-1, b=2^k-1, out=0).
Writes subjects/SUBJECTS.json. No mutant is created here.
"""
import hashlib, json, os, sys, ast
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from mqt.bench.benchmarks import qwalk, rg_qft_multiplier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = os.path.join(ROOT, "frozen_deps")
BASIS = ["x", "y", "h", "sx", "rx", "ry", "z", "s", "t", "p", "rz", "cx", "cz", "cp", "rxx", "rzz"]  # MUT.ARITY

def extract(path, name):
    src = open(path).read(); t = ast.parse(src)
    f = next(n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = {}; exec(compile(ast.Module(body=[f], type_ignores=[]), path, "exec"), ns); return ns[name]
prep_gates = extract(os.path.join(FD, "r2_external.py"), "prep_gates")   # frozen copy, verified by deps.py

def canon(gl): return json.dumps(gl, sort_keys=True, separators=(",", ":"))
def lower(qc):
    t = transpile(qc.remove_final_measurements(inplace=False), basis_gates=BASIS,
                  optimization_level=0, seed_transpiler=0)
    out = []
    for i in t.data:
        g = {"gate": i.operation.name, "q": [t.find_bit(b).index for b in i.qubits]}
        if i.operation.params: g["angles"] = [float(x) for x in i.operation.params]
        out.append(g)
    return out, t.num_qubits
def build(gl, n):
    qc = QuantumCircuit(n)
    for g in gl: getattr(qc, g["gate"])(*g.get("angles", []), *g["q"])
    return qc

SUBJECTS = [
    {"subject": "qwalk_4", "family": "quantum_walk", "module": "qwalk", "args": {"num_qubits": 4},
     "contract": "fixed", "contract_id": "C_FIXED_INPUT_STATE", "declared_input": "|0...0>: walker at node 0, coin |0>"},
    {"subject": "qwalk_5", "family": "quantum_walk", "module": "qwalk", "args": {"num_qubits": 5},
     "contract": "fixed", "contract_id": "C_FIXED_INPUT_STATE", "declared_input": "|0...0>: walker at node 0, coin |0>"},
    {"subject": "rg_mult_8", "family": "multiplication", "module": "rg_qft_multiplier", "args": {"num_qubits": 8},
     "contract": "unitary", "contract_id": "C_ARBITRARY_INPUT_UNITARY",
     "declared_input": "(|a=1,b=1,out=0> + |a=3,b=3,out=0>)/sqrt2"},
    {"subject": "rg_mult_12", "family": "multiplication", "module": "rg_qft_multiplier", "args": {"num_qubits": 12},
     "contract": "unitary", "contract_id": "C_ARBITRARY_INPUT_UNITARY",
     "declared_input": "(|a=1,b=1,out=0> + |a=7,b=7,out=0>)/sqrt2"},
]
MODS = {"qwalk": qwalk, "rg_qft_multiplier": rg_qft_multiplier}

def main():
    out = []
    for s in SUBJECTS:
        qc = MODS[s["module"]].create_circuit(**s["args"])
        body, n = lower(qc)
        if s["family"] == "multiplication":
            k = n // 4
            xa = 1 | (1 << k); xb = (2 ** k - 1) | ((2 ** k - 1) << k)
            prep = prep_gates(xa, xb, n); s["x_a"], s["x_b"] = xa, xb
        else:
            prep = []
        sv = Statevector(build(prep + body, n)).data; p = np.abs(sv) ** 2
        marg = [float(p[((np.arange(2 ** n) >> q) & 1) == 1].sum()) for q in range(n)]
        out.append({**s, "n": n, "prep": prep, "body": body, "outreg": list(range(n)),
                    "analytic_marginals_p1": marg,
                    "body_sha256": hashlib.sha256(canon(body).encode()).hexdigest(),
                    "prep_sha256": hashlib.sha256(canon(prep).encode()).hexdigest(),
                    "mqt_circuit_qasm2_sha256": hashlib.sha256(
                        __import__("qiskit").qasm2.dumps(qc).encode()).hexdigest(),
                    "gates": len(body)})
        print(s["subject"], n, len(body), [round(x, 4) for x in marg], flush=True)
    os.makedirs(os.path.join(ROOT, "subjects"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "subjects", "SUBJECTS.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
