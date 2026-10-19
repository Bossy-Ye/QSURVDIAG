#!/usr/bin/env python3
"""Mutation allocation for the prospective external RQ5 cohort.

RECONSTRUCTION, NOT NEW METHOD. This reuses the packaged prospective-cohort
procedure of research_repair/phase5_validation/s2_cohort/s2_cohort.py verbatim in
substance: the frozen enumerator rq3_feasibility_gate.core.mutants.complete_pool,
the nine (operator, gate_class) strata, the largest-remainder apportionment over
available deduplicated sites, and first-k selection after sorting by
(location spec, sha256(canon_json(mutated_gates))).

No RNG is consumed; no mutation-selection seed exists or is needed.
No operator is added. No phase-specific mutation exists. Nothing is tuned.

Why the prospective convention: the external cohort is a prospective cohort, and
the prospective convention is the one that is packaged, runnable and deterministic.
The construction population used a different, equal-per-operator rule whose
within-stratum ordering is not recoverable (see PART 4/5 of the amendment record).
"""
import collections, hashlib, sys

OPS = ("gate_deletion", "gate_insertion", "gate_replacement")
CLS = ("local_basis_amplitude", "phase_parameterized", "entangling_controlled")
STRATA = [(o, c) for o in OPS for c in CLS]
PER_SUBJECT = 30


def largest_remainder(avail, total):
    """Verbatim from s2_cohort.py: proportional to availability, remainders by
    largest fraction then stratum order."""
    live = {k: v for k, v in avail.items() if v > 0}
    if not live:
        return {k: 0 for k in avail}
    S = sum(live.values())
    exact = {k: total * v / S for k, v in live.items()}
    base = {k: min(int(exact[k]), live[k]) for k in live}
    alloc = dict(base)
    while sum(alloc.values()) < total:
        cand = [k for k in live if alloc[k] < live[k]]
        if not cand:
            break
        cand.sort(key=lambda k: (-(exact[k] - base[k]), STRATA.index(k)))
        alloc[cand[0]] += 1
    return {k: alloc.get(k, 0) for k in avail}


def allocate(gates, n, circuit_id, complete_pool, canon_json, per_subject=PER_SUBJECT):
    """Enumerate -> deduplicate -> allocate -> materialize. Returns (picked, log)."""
    pool, _ = complete_pool(gates, n, circuit_id)
    by = collections.defaultdict(list)
    for m in pool:
        by[(m["op"], m["gate_class"])].append(m)
    for k in by:                       # frozen order
        by[k].sort(key=lambda m: (m["spec"],
                   hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest()))
    avail = {k: len(by[k]) for k in STRATA}
    alloc = largest_remainder(avail, per_subject)
    picked = []
    for k in STRATA:
        picked += [(k, m) for m in by[k][:alloc[k]]]
    deficit = per_subject - len(picked)
    if deficit > 0:                    # same rule over remaining capacity
        rem = {k: max(0, avail[k] - alloc[k]) for k in STRATA}
        extra = largest_remainder(rem, deficit)
        for k in STRATA:
            if extra[k]:
                picked += [(k, m) for m in by[k][alloc[k]:alloc[k] + extra[k]]]
    log = [{"stratum": f"{k[0]}/{k[1]}", "sites_available_deduped": avail[k],
            "allocation": alloc[k], "drawn": sum(1 for kk, _ in picked if kk == k)}
           for k in STRATA]
    return picked, log
