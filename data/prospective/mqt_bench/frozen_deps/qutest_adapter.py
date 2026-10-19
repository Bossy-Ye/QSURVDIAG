"""Native QUTest ToolAdapter. Uses QUTest's OWN OpenQASM3 //% expect assertions + tolerance rule via the real
qutest CLI. Contains NO Fisher exact, NO Holm, NO QuCheck n*, NO QuCheck input-generation, NO QuCheck basis
logic, NO 400-shot assumption. Native inner shots = 2000 (justified by atol; see QUTEST_POWER_DESIGN).
RUN env: .venv-qutest-audit (qiskit 2.5.0 + qutest CLI).
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

_ROOT = Path(__file__).resolve().parents[2]
QUTEST = str(_ROOT / ".venv-qutest-audit" / "bin" / "qutest")
INNER_SHOTS = 2000            # native; justified by atol (SE<=atol/4 at p=0.5). NOT QuCheck 400, NOT "8000 because 8000".
ATOL = 0.05                   # QUTest native tolerance
SEED = 42
_SIM = AerSimulator()


def _apply(qc, g):
    name = g["gate"]; idx = [int(x) for x in g["q"]]; ang = g.get("angles", [])
    getattr(qc, name)(*ang, *idx) if ang else getattr(qc, name)(*idx)


def make_test(gates, n, assertions, shots=INNER_SHOTS, seed=SEED):
    L = ["OPENQASM 3;", 'include "stdgates.inc";', "def test_q() {",
         f"    //% shots {shots}", f"    //% seed {seed}", "    //% backend ideal",
         f"    qubit[{n}] q;", f"    bit[{n}] m;"]
    for g in gates:
        a = ("(" + ",".join(f"{x}" for x in g.get("angles", [])) + ")") if g.get("angles") else ""
        L.append("    " + f"{g['gate']}{a} " + ", ".join(f"q[{i}]" for i in g["q"]) + ";")
    L.append("    m = measure q;")
    L += ["    " + a for a in assertions]
    L.append("}")
    return "\n".join(L) + "\n"


def run_qutest(text):
    """NATIVE decision: qutest CLI tolerance rule. passed->SURVIVED, failed->KILLED, error->UNSUPPORTED."""
    with tempfile.NamedTemporaryFile("w", suffix=".qasm", delete=False) as f:
        f.write(text); p = f.name
    try:
        r = subprocess.run([QUTEST, "run", p], capture_output=True, text=True, timeout=180)
        out = (r.stdout + r.stderr).strip(); summ = out.splitlines()[-1] if out else ""
        if "error" in summ:
            return "UNSUPPORTED", summ[:120]
        if "failed" in summ:
            return "KILLED", summ[:120]
        if "passed" in summ:
            return "SURVIVED", summ[:120]
        return "UNSUPPORTED", out[:120]
    finally:
        Path(p).unlink(missing_ok=True)


def _counts(gates, n, shots=INNER_SHOTS, seed=SEED):
    qc = QuantumCircuit(n, n)
    for g in gates:
        _apply(qc, g)
    qc.measure(range(n), range(n))
    return _SIM.run(transpile(qc, _SIM, optimization_level=0, seed_transpiler=42), shots=shots, seed_simulator=seed).result().get_counts()


def marginal_p1(counts, q, shots=INNER_SHOTS):
    return sum(c for k, c in counts.items() if k[len(k) - 1 - q] == "1") / shots


def reference_marginal(orig_gates, n, q, shots=INNER_SHOTS, seed=SEED):
    """Native reference: shot-based marginal of the ORIGINAL only (never the mutant)."""
    return round(marginal_p1(_counts(orig_gates, n, shots, seed), q, shots), 4)


# ---- native assertion grammar (Z-basis only) ----
def marginal_assertion(q, ref, atol=ATOL):
    return f"//% expect marginal m[{q}] p1 ~= {ref} atol={atol}"


def nonZ_observable_assertion(pauli_label="X0", ref=0.0, atol=ATOL):
    return f'//% expect observable "{pauli_label}" ~= {ref} atol={atol}'   # ILLEGAL: non-Z -> UNSUPPORTED


# ---- ToolAdapter-style interface ----
class QUTestAdapter:
    name = "qutest"

    def tool_contract(self):
        return {"inputs": "OpenQASM3 circuit + measurement m=measure q (fixed per test)",
                "observables": "Z-basis only: marginal/distribution/Z-observable/correlation(Z)/entanglement/entropy/output/probability",
                "non_Z": "REJECTED -> UNSUPPORTED", "decision_rule": "per-assertion tolerance (atol); kill=any violated",
                "resource_dims": ["assertions", "inner_shots", "circuit_executions"]}

    def check_candidate_legality(self, assertion_text):
        return assertion_text.strip().startswith("//% expect") and "observable" not in assertion_text.split("expect")[1].split()[0:1] \
            and 'observable "' not in assertion_text   # non-Z observable is illegal

    def native_decision_rule(self):
        return {"statistic": "tolerance (atol) on Z-basis assertion vs original-derived reference",
                "kill": "any //% expect violated", "multiplicity": "assertions within a test (native)",
                "NOT": ["fisher_exact", "holm", "qucheck_nstar", "qucheck_400"]}

    def resource_vector(self, n_assertions):
        return {"assertions": n_assertions, "inner_shots": INNER_SHOTS,
                "circuit_executions": n_assertions, "measurement_settings": "Z"}

    def run_suite(self, gates, n, assertions, seed=SEED):
        """NATIVE suite decision (used for original-baseline legality smoke tests ONLY in this stage)."""
        return run_qutest(make_test(gates, n, assertions, INNER_SHOTS, seed))

    def provenance(self):
        return {"tool": "QUTest 0.1.0 (github QBugs/qutest; Zenodo 21168567; Apache-2.0) -- NOT PyPI qutest",
                "inner_shots": {"value": INNER_SHOTS, "status": "experimental_configuration",
                                "justification": "SE<=atol/4 at p=0.5 (atol=0.05); NOT QuCheck 400; NOT '8000 because 8000'"},
                "decision": "qutest CLI tolerance", "reference": "original-only (never mutant)"}
