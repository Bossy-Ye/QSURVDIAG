"""Canonical, version-independent circuit representation shared by BOTH method adapters.

A circuit is a list of canonical gates. A canonical gate is a dict:
    {"gate": <name>, "q": [<qubit indices>], "angles": [<float>, ...]}   # "angles" omitted if none

The canonical form is pure Python (no qiskit) so the SAME mutant is hashed identically and run
under both QuCheck (its own venv) and QOPS (its own venv). Angles are rounded to ANGLE_NDIGITS
for a stable hash. qiskit materialization happens only inside each adapter, in its own venv.
"""
import hashlib
import json

ANGLE_NDIGITS = 12


def gate(name, *q, angles=None):
    d = {"gate": name, "q": [int(x) for x in q]}
    if angles:
        d["angles"] = [round(float(a), ANGLE_NDIGITS) for a in angles]
    return d


def canon(gates):
    """Deterministic canonical list (angles rounded, keys ordered)."""
    out = []
    for g in gates:
        d = {"gate": g["gate"], "q": [int(x) for x in g["q"]]}
        if g.get("angles"):
            d["angles"] = [round(float(a), ANGLE_NDIGITS) for a in g["angles"]]
        out.append(d)
    return out


def canon_json(gates):
    return json.dumps(canon(gates), sort_keys=True, separators=(",", ":"))


def circuit_hash(gates, n):
    return hashlib.sha256(f"n={n};".encode() + canon_json(gates).encode()).hexdigest()


def gate_support(g):
    return set(int(x) for x in g["q"])


def apply_to_qiskit(qc, gates):
    """Materialize canonical gates onto a qiskit QuantumCircuit (called INSIDE an adapter venv).
    Angle-bearing gates pass angles first, matching qiskit signatures (e.g. qc.cp(theta, c, t))."""
    for g in gates:
        name, q = g["gate"], g["q"]
        ang = g.get("angles", [])
        fn = getattr(qc, name)
        if ang:
            fn(*ang, *q)
        else:
            fn(*q)
    return qc


def to_measured_qasm(gates, n):
    """OpenQASM-independent textual rendering for provenance (not executed)."""
    lines = [f"// canonical circuit, n={n}"]
    for g in gates:
        a = ("(" + ",".join(f"{x:.6f}" for x in g["angles"]) + ")") if g.get("angles") else ""
        lines.append(f"{g['gate']}{a} " + ",".join(f"q[{i}]" for i in g["q"]) + ";")
    return "\n".join(lines)


def depth_len(gates):
    return len(gates)


def position_third(index, total):
    """Frozen mapping of a gate index to its circuit third (first/middle/last)."""
    if total <= 0:
        return "first"
    frac = index / total
    if frac < 1 / 3:
        return "first"
    if frac < 2 / 3:
        return "middle"
    return "last"
