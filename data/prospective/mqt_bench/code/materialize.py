"""Freeze B: deterministic materialization of the mutant population (Pass 3B).

Enumeration + allocation only: no QUTest run, no state, no observation, no diagnosis, no RNG.
Reuses:
  * mutants.complete_pool (insertion, replacement, deletion; frozen policy) from the cohort copy
    rq3_cohort.core, identical to rq3_feasibility_gate.core except QUBIT_LIMIT 10 -> 14 (PD-1),
  * s2_cohort.largest_remainder (extracted by AST; its source hash must equal the external
    cohort's recorded apportionment_fn_sha256),
  * the external cohort's dedup / sort / allocation / deficit rule (materialize.py, 2026-09-06),
    30 per subject over 3 operators x 3 gate classes.
Mutation acts on the converted program body only; the declared-input preparation is prepended at
execution and never mutated (external-cohort convention).
Environment: .venv-qutest-audit (qiskit 2.5.0).
"""
import ast, collections, csv, hashlib, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.dirname(ROOT)
sys.path.insert(0, PILOT); sys.path.insert(0, os.path.join(ROOT, "code")); sys.path.insert(0, os.path.join(ROOT, "cohort_enumerator"))
import deps; deps.verify()
# PD-1: the cohort-specific copy of the enumerator (only QUBIT_LIMIT 10 -> 14; cohort_enumerator/PD1_QUBIT_LIMIT.diff)
from rq3_cohort.core import mutants as MUT
from rq3_cohort.core.representation import canon_json
COHORT_ENUM_FILES = {f: hashlib.sha256(open(os.path.join(ROOT, "cohort_enumerator", "rq3_cohort", "core", f), "rb").read()).hexdigest()
                     for f in ("__init__.py", "mutants.py", "gate_config.py", "fragment.py", "representation.py")}
from qiskit import QuantumCircuit
from qiskit.qasm3 import dumps as q3dumps

PER_SUBJECT = 30
OPS = ("gate_deletion", "gate_insertion", "gate_replacement")
CLS = ("local_basis_amplitude", "phase_parameterized", "entangling_controlled")
STRATA = [(o, c) for o in OPS for c in CLS]
EXT_RECORD = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/external_cohort/MATERIALIZATION_RECORD.json"

# ---- frozen apportionment, extracted from the frozen copy of s2_cohort.py
S2 = os.path.join(ROOT, "frozen_deps", "s2_cohort.py")
_src = open(S2).read(); _tree = ast.parse(_src)
_fn = next(n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name == "largest_remainder")
FN_SHA = hashlib.sha256(ast.get_source_segment(_src, _fn).encode()).hexdigest()
_ns = {"STRATA": STRATA}
exec(compile(ast.Module(body=[_fn], type_ignores=[]), S2, "exec"), _ns)
largest_remainder = _ns["largest_remainder"]
assert FN_SHA == json.load(open(EXT_RECORD))["allocator"]["apportionment_fn_sha256"], "allocator drift"


def main():
    S = json.load(open(os.path.join(ROOT, "subjects", "SUBJECTS.json")))
    out = os.path.join(ROOT, "population"); os.makedirs(os.path.join(out, "mutants"), exist_ok=True)
    alloc_rows, census, pool_rows = [], [], []
    for s in S:
        name, n, body = s["subject"], s["n"], s["body"]
        ok, why = MUT.circuit_eligible(body, n)
        if not ok:
            census.append({"subject": name, "n": n, "eligible": False, "reasons": "; ".join(why[:3]),
                           "legal_opportunities": 0, "deduplicated": 0, "allocated": 0})
            continue
        pool, inel = MUT.complete_pool(body, n, name)
        seen, dedup = set(), []
        for m in pool:
            if m["mutated_hash"] in seen: continue
            seen.add(m["mutated_hash"]); dedup.append(m)
        by = collections.defaultdict(list)
        for m in dedup: by[(m["op"], m["gate_class"])].append(m)
        for k in by:
            by[k].sort(key=lambda m: (m["spec"], hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest()))
        avail = {k: len(by[k]) for k in STRATA}
        total = min(PER_SUBJECT, len(dedup))
        alloc = largest_remainder(avail, total)
        picked = []
        for k in STRATA: picked += [(k, m) for m in by[k][:alloc[k]]]
        deficit = total - len(picked)
        if deficit > 0:
            rem = {k: max(0, avail[k] - alloc[k]) for k in STRATA}
            extra = largest_remainder(rem, deficit)
            for k in STRATA:
                if extra[k]: picked += [(k, m) for m in by[k][alloc[k]:alloc[k] + extra[k]]]
        for m in dedup:
            pool_rows.append({"subject": name, "operator": m["op"], "gate_class": m["gate_class"],
                              "location": m["spec"], "mutated_hash": m["mutated_hash"]})
        os.makedirs(os.path.join(out, "mutants", name), exist_ok=True)
        for j, (k, m) in enumerate(picked):
            mid = f"{name}#m{j:02d}"
            gl = json.loads(m["mutated_gates"]) if isinstance(m["mutated_gates"], str) else m["mutated_gates"]
            qc = QuantumCircuit(n)
            for g in gl: getattr(qc, g["gate"])(*g.get("angles", []), *[int(q) for q in g["q"]])
            base = os.path.join("mutants", name, mid.replace("#", "_"))
            open(os.path.join(out, base + ".json"), "w").write(json.dumps(gl, sort_keys=True))
            open(os.path.join(out, base + ".qasm"), "w").write(q3dumps(qc))
            alloc_rows.append({"mutant_id": mid, "subject": name, "family": s["family"], "n": n,
                               "orig_body_sha256": s["body_sha256"], "operator": m["op"],
                               "gate_class": m["gate_class"], "stratum": f"{k[0]}/{k[1]}", "location": m["spec"],
                               "anchor_index": m.get("anchor_index", ""), "third": m.get("third", ""),
                               "allocation_rank": j, "gate_count": len(gl), "mutated_hash": m["mutated_hash"],
                               "definition_sha256": hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest(),
                               "gates_path": base + ".json", "qasm_path": base + ".qasm"})
        c = collections.Counter(m["op"] for _, m in picked)
        census.append({"subject": name, "n": n, "eligible": True, "reasons": "",
                       "legal_opportunities": len(pool), "ineligible_candidates": len(inel),
                       "deduplicated": len(dedup), "allocated": len(picked),
                       "insertion": c["gate_insertion"], "replacement": c["gate_replacement"],
                       "deletion": c["gate_deletion"], "strata_available": {f"{a}/{b}": v for (a, b), v in avail.items()}})
    def wcsv(fn, rows):
        p = os.path.join(out, fn)
        with open(p, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    wcsv("MUTANT_MANIFEST.csv", alloc_rows); wcsv("MUTATION_POOL.csv", pool_rows)
    json.dump({"census": census, "allocator_fn_sha256": FN_SHA, "enumerator": "rq3_cohort (PD-1)", "enumerator_qubit_limit": __import__("rq3_cohort.core.gate_config", fromlist=["x"]).QUBIT_LIMIT, "enumerator_file_sha256": COHORT_ENUM_FILES,
               "per_subject": PER_SUBJECT, "strata": [f"{a}/{b}" for a, b in STRATA]},
              open(os.path.join(out, "CENSUS.json"), "w"), indent=1)
    for c in census: print(c)

if __name__ == "__main__":
    main()
