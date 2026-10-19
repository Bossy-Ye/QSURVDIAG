"""Mutation taxonomy, complete static-eligible pool, and the FROZEN outcome-blind stratified
selection of exactly 18 primary mutants per circuit.

Taxonomy (frozen): 3 operators x 3 gate-semantic classes x 2 samples = 18.
  operator class = class of the gate DELETED / INSERTED / SUBSTITUTED-IN.
  local_basis_amplitude {x,y,h,sx,rx,ry} | phase_parameterized {z,s,t,p,rz} | entangling_controlled {cx,cz,cp,rxx,rzz}
Selection is deterministic (per-circuit seed from MASTER_SEED_HEX), balanced across position-thirds,
and OUTCOME-BLIND (no survival / equivalence / witness / pre-cert information used).
Static-infeasible cells (e.g. deletion-phase for a phase-gate-free algorithm) are filled by a frozen,
fully-disclosed redistribution within the same operator; every deviation is logged.
"""
import hashlib
import random

from .gate_config import (GATE_SEMANTIC_CLASSES, MUTATION_OPERATORS, SAMPLES_PER_CELL,
                          MASTER_SEED_HEX, PI)
from .fragment import circuit_eligible
from .representation import canon, circuit_hash, position_third

CLASS_OF = {g: cls for cls, gs in GATE_SEMANTIC_CLASSES.items() for g in gs}
ARITY = {"x": 1, "y": 1, "h": 1, "sx": 1, "rx": 1, "ry": 1,
         "z": 1, "s": 1, "t": 1, "p": 1, "rz": 1,
         "cx": 2, "cz": 2, "cp": 2, "rxx": 2, "rzz": 2}
ANGLED = {"rx", "ry", "p", "rz", "cp", "rxx", "rzz"}
INSERT_ANGLE = round(PI / 2, 12)              # frozen angle for any inserted/substituted parameterized gate
CLASSES = tuple(GATE_SEMANTIC_CLASSES.keys())


def _seed(circuit_id, salt):
    return int(hashlib.sha256(f"{MASTER_SEED_HEX}|{circuit_id}|{salt}".encode()).hexdigest(), 16) % (2 ** 32)


def _mk(name, q):
    g = {"gate": name, "q": list(q)}
    if name in ANGLED:
        g["angles"] = [INSERT_ANGLE]
    return g


def _class_gate_instances(cls, n):
    """All (gate, qubits) instances of a class placeable on n qubits (bounded, deterministic)."""
    out = []
    for name in GATE_SEMANTIC_CLASSES[cls]:
        if ARITY[name] == 1:
            for q in range(n):
                out.append((name, (q,)))
        else:
            pairs = [(a, a + 1) for a in range(n - 1)]
            if n > 2:
                pairs.append((0, n - 1))
            for (a, b) in pairs:
                out.append((name, (a, b)))
    return out


def _insert_positions(L):
    """Frozen bounded position grid covering all thirds (documented; not a silent cap)."""
    if L <= 40:
        return list(range(L + 1))
    grid = sorted(set([0, L] + [round(L * f) for f in
                  (0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95)]))
    return grid


def complete_pool(gates, n, circuit_id):
    """Complete static-eligible mutant pool under the frozen enumeration policy.
    Each entry: {mutant_key, op, gate_class, third, site/pos, spec, mutated_gates, mutated_hash}."""
    pool, ineligible = [], []
    L = len(gates)

    def add(op, cls, anchor_index, spec, mutated):
        ok, reasons = circuit_eligible(mutated, n)
        rec = {"op": op, "gate_class": cls, "third": position_third(anchor_index, L),
               "anchor_index": anchor_index, "spec": spec,
               "mutated_gates": canon(mutated), "mutated_hash": circuit_hash(mutated, n)}
        rec["mutant_key"] = f"{op}:{cls}:{spec}"
        if ok:
            pool.append(rec)
        else:
            rec["reasons"] = reasons
            ineligible.append(rec)

    # ---- deletion: class = class of deleted gate (only covered-class gates) ----
    for i, g in enumerate(gates):
        cls = CLASS_OF.get(g["gate"])
        if cls is None:
            continue
        mutated = gates[:i] + gates[i + 1:]
        add("gate_deletion", cls, i, f"del@{i}:{g['gate']}", mutated)

    # ---- insertion: class = class of inserted gate ----
    for cls in CLASSES:
        for (name, q) in _class_gate_instances(cls, n):
            for pos in _insert_positions(L):
                mutated = gates[:pos] + [_mk(name, q)] + gates[pos:]
                add("gate_insertion", cls, pos, f"ins@{pos}:{name}{list(q)}", mutated)

    # ---- replacement: class = class of substituted-in gate (arity-preserving) ----
    for i, g in enumerate(gates):
        a = len(g["q"])
        for cls in CLASSES:
            for name in GATE_SEMANTIC_CLASSES[cls]:
                if ARITY[name] != a:
                    continue
                new = _mk(name, g["q"])
                if new["gate"] == g["gate"] and new.get("angles") == g.get("angles"):
                    continue
                mutated = gates[:i] + [new] + gates[i + 1:]
                add("gate_replacement", cls, i, f"rep@{i}:{g['gate']}->{name}", mutated)

    return pool, ineligible


def _pick_balanced(cands, k, rng, start=0):
    """Pick k candidates spread across thirds, deterministic. `start` rotates the third the
    cycle begins on, so many k=2 cells together still cover first/middle/last evenly."""
    by_third = {"first": [], "middle": [], "last": []}
    for c in cands:
        by_third[c["third"]].append(c)
    for t in by_third:
        rng.shuffle(by_third[t])
    base, picked = ["first", "middle", "last"], []
    order = base[start % 3:] + base[:start % 3]
    ti = 0
    while len(picked) < k and any(by_third.values()):
        t = order[ti % 3]; ti += 1
        if by_third[t]:
            picked.append(by_third[t].pop())
    return picked


def select_18(gates, n, circuit_id):
    """Frozen outcome-blind stratified selection of exactly 18 mutants + full selection log."""
    pool, ineligible = complete_pool(gates, n, circuit_id)
    rng = random.Random(_seed(circuit_id, "select"))
    cells = {(op, cls): [c for c in pool if c["op"] == op and c["gate_class"] == cls]
             for op in MUTATION_OPERATORS for cls in CLASSES}
    selected, log, used_keys = [], [], set()

    # pass 1: 2 per (operator, class), balanced across thirds (rotating start -> overall 6/6/6)
    deficits = {}
    cell_i = 0
    for op in MUTATION_OPERATORS:
        for cls in CLASSES:
            cands = [c for c in cells[(op, cls)] if c["mutated_hash"] not in used_keys]
            pick = _pick_balanced(cands, SAMPLES_PER_CELL, rng, start=cell_i); cell_i += 1
            for c in pick:
                used_keys.add(c["mutated_hash"]); selected.append(c)
            got = len(pick)
            log.append({"cell": f"{op}/{cls}", "available": len(cells[(op, cls)]), "picked": got})
            if got < SAMPLES_PER_CELL:
                deficits[(op, cls)] = SAMPLES_PER_CELL - got

    # pass 2: frozen disclosed redistribution — fill each deficit from the SAME operator's other classes
    redistribution = []
    for (op, cls), need in deficits.items():
        for _ in range(need):
            donors = [c for oc in CLASSES if oc != cls
                      for c in cells[(op, oc)] if c["mutated_hash"] not in used_keys]
            donors = _pick_balanced(donors, 1, rng, start=cell_i); cell_i += 1
            if donors:
                c = donors[0]; used_keys.add(c["mutated_hash"]); selected.append(c)
                redistribution.append({"deficit_cell": f"{op}/{cls}", "filled_from": f"{op}/{c['gate_class']}",
                                       "reason": "static-infeasible cell (no eligible gate of this class for this operator); frozen same-operator redistribution"})
            else:
                redistribution.append({"deficit_cell": f"{op}/{cls}", "filled_from": None,
                                       "reason": "no same-operator donor available"})

    # provenance + labels
    for idx, c in enumerate(selected):
        c["mutant_id"] = f"{circuit_id}#m{idx:02d}"
    thirds = {t: sum(1 for c in selected if c["third"] == t) for t in ("first", "middle", "last")}
    by_op = {op: sum(1 for c in selected if c["op"] == op) for op in MUTATION_OPERATORS}
    by_cls = {cls: sum(1 for c in selected if c["gate_class"] == cls) for cls in CLASSES}
    return {
        "circuit_id": circuit_id, "n": n, "n_selected": len(selected),
        "pool_size": len(pool), "ineligible_count": len(ineligible),
        "position_third_balance": thirds, "operator_balance": by_op, "class_balance": by_cls,
        "selection_log": log, "redistribution": redistribution,
        "selected": [{"mutant_id": c["mutant_id"], "op": c["op"], "gate_class": c["gate_class"],
                      "third": c["third"], "anchor_index": c["anchor_index"], "spec": c["spec"],
                      "mutated_hash": c["mutated_hash"], "mutated_gates": c["mutated_gates"]}
                     for c in selected],
    }, pool, ineligible
