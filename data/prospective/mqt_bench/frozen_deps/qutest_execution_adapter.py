#!/usr/bin/env python3
"""Execution adapter: lower QUTest-unsupported composite gates to supported primitives.

Purpose. QUTest 0.1.0's OpenQASM 3 front end cannot parse `rzz` or `rxx`; they are not
in `stdgates.inc`. This adapter is a serialization step applied uniformly to every
original and every mutant immediately before QUTest invocation. It is OUTSIDE the
mutation region: it changes no mutation identity, no mutant selection, no legal pool
and no allocation.

Decompositions are exact, including global phase, and are the standard identities:

    rzz(t) a,b  ==  cx a,b ; rz(t) b ; cx a,b
    rxx(t) a,b  ==  h a ; h b ; cx a,b ; rz(t) b ; cx a,b ; h a ; h b

No optimization, no routing, no device mapping, no gate reordering, no
mutation-specific or outcome-dependent behaviour. Qubit indices, register width and
gate order are preserved exactly; every other gate passes through untouched.

ADAPTER_VERSION is part of the execution record.
"""
ADAPTER_VERSION = "1.0.0"

UNSUPPORTED = ("rzz", "rxx")


def _lower(g):
    """Lower one gate to a list of QUTest-supported gates. Identity for supported gates."""
    name = g["gate"]
    if name not in UNSUPPORTED:
        return [g]
    a, b = int(g["q"][0]), int(g["q"][1])
    t = g["angles"][0]
    if name == "rzz":
        return [{"gate": "cx", "q": [a, b]},
                {"gate": "rz", "q": [b], "angles": [t]},
                {"gate": "cx", "q": [a, b]}]
    return [{"gate": "h", "q": [a]}, {"gate": "h", "q": [b]},
            {"gate": "cx", "q": [a, b]},
            {"gate": "rz", "q": [b], "angles": [t]},
            {"gate": "cx", "q": [a, b]},
            {"gate": "h", "q": [a]}, {"gate": "h", "q": [b]}]


def adapt(gates):
    """Apply the adapter to a gate list. Returns a new list; input is not mutated."""
    out = []
    for g in gates:
        out.extend(_lower(g))
    return out


def is_identity(gates):
    """True when the adapter is a no-op for this circuit."""
    return not any(g["gate"] in UNSUPPORTED for g in gates)
