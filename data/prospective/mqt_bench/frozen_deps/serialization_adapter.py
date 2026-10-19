"""Frozen serialization adapter: qiskit op name -> OpenQASM 3 name accepted by QUTest.

This is a SERIALIZATION rule, not a QSurvDiag methodology change.  It renames an
operation to the spelling the target parser accepts.  It never changes a gate's
matrix, never reorders operands, and never rewrites a circuit structurally.

Rule (generic, not per circuit):
    an operation whose qiskit name has no OpenQASM 3 stdgates.inc spelling is
    emitted under its exact semantically equivalent stdgates.inc name, when one
    exists and the two denote the same unitary for all parameter values.

Currently one mapping qualifies:
    u(theta, phi, lambda)  ->  u3(theta, phi, lambda)
Both denote the same 2x2 unitary; qiskit's U3Gate is defined as an alias of UGate.
No other mapping is declared.  Unmapped unsupported operations stay unsupported.
"""
ADAPTER_VERSION = "1.0.0"
NAME_MAP = {"u": "u3"}          # arity and parameter order identical


def emit_name(qiskit_name):
    return NAME_MAP.get(qiskit_name, qiskit_name)


def adapter_hash():
    import hashlib
    payload = f"{ADAPTER_VERSION}|" + ";".join(f"{k}->{v}" for k, v in sorted(NAME_MAP.items()))
    return hashlib.sha256(payload.encode()).hexdigest()
