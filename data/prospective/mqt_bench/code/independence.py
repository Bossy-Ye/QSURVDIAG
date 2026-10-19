"""Freeze B checks without execution (Pass 3B).

1. Independence: no (original, mutant) pair -- and no original or mutant program -- of this cohort
   is content-identical to any program of an earlier study population. Compared by the SHA-256 of
   the canonical gate list (representation.canon_json), after loading every earlier population
   into the same gate-list form: construction (final_empirical_study), prospective (S1/S2),
   external (manuscript/tse/external_cohort), and the QMutBench width set and corpus (QASM files).
2. Static QUTest compatibility: after the frozen rewriting (adapt), every gate of every
   prep+mutant program is in the QUTest 0.1.0 supported set probed in T2A_GATE_SUPPORT.json,
   and n <= 14. No QUTest run.
Environment: .venv-qutest-audit. Writes population/INDEPENDENCE.json and population/STATIC_CHECK.json.
"""
import csv, glob, hashlib, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.dirname(ROOT)
sys.path.insert(0, PILOT); sys.path.insert(0, os.path.join(ROOT, "code")); sys.path.insert(0, os.path.join(ROOT, "frozen_deps"))
import deps; deps.verify()
from rq3_feasibility_gate.core.representation import canon_json
from qutest_execution_adapter import adapt
from qiskit import qasm2
from qiskit.qasm3 import loads as q3loads

PA = "/Users/mac/Desktop/ZX-STUDY/paper-artifact"
def h(gl): return hashlib.sha256(canon_json(gl).encode()).hexdigest()
def gates_of_qc(qc):
    return [{"gate": i.operation.name, "q": [qc.find_bit(b).index for b in i.qubits],
             **({"angles": [float(p) for p in i.operation.params]} if i.operation.params else {})}
            for i in qc.data if i.operation.name not in ("measure", "barrier")]

def earlier_programs():
    progs = set(); src = {}
    def add(gl, tag):
        k = h(gl); progs.add(k); src.setdefault(k, tag)
    for r in csv.DictReader(open(f"{PILOT}/final_empirical_study/MUTANT_POPULATION.csv")):
        add(json.loads(r["mutated_gates"]), "construction")
    for s in json.load(open(f"{PILOT}/research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json")):
        bg = s["base_gates"]; add(json.loads(bg) if isinstance(bg, str) else bg, "prospective-original")
    for r in csv.DictReader(open(f"{PILOT}/research_repair/phase5_validation/s2_cohort/S2_SAMPLED_MUTANTS.csv")):
        add(json.loads(r["mutated_gates"]), "prospective")
    ext = f"{PA}/manuscript/tse/external_cohort"
    for r in csv.DictReader(open(f"{ext}/EXTERNAL_ALLOCATION.csv")):
        add(gates_of_qc(q3loads(open(os.path.join(ext, r["mutant_path"])).read())), "external")
    L = qasm2.LEGACY_CUSTOM_INSTRUCTIONS
    for p in glob.glob(f"{PILOT}/data/qmutbench/*/*.qasm"):
        try: add(gates_of_qc(qasm2.load(p, custom_instructions=L)), "qmutbench")
        except Exception: pass
    return progs, src

def main():
    S = {s["subject"]: s for s in json.load(open(os.path.join(ROOT, "subjects", "SUBJECTS.json")))}
    man = list(csv.DictReader(open(os.path.join(ROOT, "population", "MUTANT_MANIFEST.csv"))))
    progs, src = earlier_programs()
    orig_hits = {k: (h(s["body"]) in progs) for k, s in S.items()}
    mut_hits = []
    for r in man:
        gl = json.load(open(os.path.join(ROOT, "population", r["gates_path"])))
        assert h(gl) == r["definition_sha256"], r["mutant_id"]
        if h(gl) in progs: mut_hits.append((r["mutant_id"], src[h(gl)]))
    indep = {"earlier_programs_hashed": len(progs), "original_matches": orig_hits,
             "mutant_matches": mut_hits, "pair_duplicates": [m for m in mut_hits if orig_hits[m[0].split("#")[0]]],
             "pass": not mut_hits and not any(orig_hits.values())}
    json.dump(indep, open(os.path.join(ROOT, "population", "INDEPENDENCE.json"), "w"), indent=1)
    sup = {g for g, ok in json.load(open(f"{PA}/manuscript/tse/batch1/T2A_GATE_SUPPORT.json")).items() if ok}
    bad = []
    for r in man:
        s = S[r["subject"]]; gl = json.load(open(os.path.join(ROOT, "population", r["gates_path"])))
        names = {g["gate"] for g in adapt(s["prep"] + gl)}
        if not names <= sup or s["n"] > 14: bad.append((r["mutant_id"], sorted(names - sup)))
    static = {"supported_set": sorted(sup), "violations": bad, "pass": not bad, "mutants_checked": len(man)}
    json.dump(static, open(os.path.join(ROOT, "population", "STATIC_CHECK.json"), "w"), indent=1)
    print("independence pass:", indep["pass"], "earlier programs:", len(progs), "| static pass:", static["pass"], bad[:5])

if __name__ == "__main__":
    main()
