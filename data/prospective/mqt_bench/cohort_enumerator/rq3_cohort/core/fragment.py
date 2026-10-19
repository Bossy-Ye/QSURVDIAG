"""fragment_v2 static eligibility for canonical circuits and single gates.

Static-only checks (spec 6.1): syntactic validity, arity, angle count, qubit range, in-fragment.
A gate/circuit outside fragment_v2 is INELIGIBLE (excluded before execution, never silently fixed).
"""
from .gate_config import (FRAG_1Q_0, FRAG_1Q_1A, FRAG_1Q_3A, FRAG_2Q_0, FRAG_2Q_1A, QUBIT_LIMIT)

_1Q = FRAG_1Q_0 | FRAG_1Q_1A | FRAG_1Q_3A
_2Q = FRAG_2Q_0 | FRAG_2Q_1A
ALL_FRAGMENT_GATES = _1Q | _2Q


def gate_spec_ok(name, nq, nangles):
    """Arity + angle-count validity for a single gate name."""
    if name in FRAG_1Q_0:
        return nq == 1 and nangles == 0
    if name in FRAG_1Q_1A:
        return nq == 1 and nangles == 1
    if name in FRAG_1Q_3A:
        return nq == 1 and nangles == 3
    if name in FRAG_2Q_0:
        return nq == 2 and nangles == 0
    if name in FRAG_2Q_1A:
        return nq == 2 and nangles == 1
    return False


def gate_eligible(g, n):
    name = g.get("gate")
    q = g.get("q", [])
    ang = g.get("angles", [])
    if name not in ALL_FRAGMENT_GATES:
        return False, f"gate '{name}' not in fragment_v2"
    if not gate_spec_ok(name, len(q), len(ang)):
        return False, f"gate '{name}' arity/angle mismatch (q={len(q)}, angles={len(ang)})"
    if any((not isinstance(i, int)) or i < 0 or i >= n for i in q):
        return False, f"gate '{name}' qubit index out of range [0,{n})"
    if len(set(q)) != len(q):
        return False, f"gate '{name}' repeated qubit"
    return True, "ok"


def circuit_eligible(gates, n):
    """Whole-circuit static eligibility. Returns (ok, reasons[])."""
    reasons = []
    if n > QUBIT_LIMIT:
        reasons.append(f"n={n} exceeds qubit limit {QUBIT_LIMIT}")
    if not gates:
        reasons.append("empty circuit")
    for i, g in enumerate(gates):
        ok, why = gate_eligible(g, n)
        if not ok:
            reasons.append(f"gate[{i}] {why}")
    return (len(reasons) == 0), reasons
