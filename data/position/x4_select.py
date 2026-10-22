"""X4, section 2: rebuild the 18 programs, regenerate their pools, and select 10 middle-third and 10 last-third
mutations per program (PLAN.md). No execution. Writes X4_SELECTION.csv, X4_POOL_CHECKS.json and the runner inputs
X4_SUBJECTS.json (sha256 ac1dc89e...) and X4_MUTANT_GATES.json (sha256 7753081c...), which hold third-party gate lists
and are not archived.

Programs: the five other circuits (S1_SUBJECTS.json), the four MQT Bench programs (SUBJECTS.json, prep kept apart),
the seven Qolumbina programs (circuit hashes of data/external/protocol/EXTERNAL_COHORT_FREEZE.json, which also records
the archive MD5) and two QASMBench circuits (pinned commit,
LF line endings). Original gate lists follow the populations' rule: transpile to the enumerator basis at level 0.
"""
import ast, collections, csv, hashlib, importlib, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; PKG = HERE.parents[1]; D = PKG / "data"
QOL = Path(os.environ.get("QOLUMBINA_SRC", "."))     # qolumbina-infrastructure-main of 10.5281/zenodo.20987327
QASMB = Path(os.environ.get("QASMBENCH_SRC", "."))    # QASMBench checkout at the commit of data/external
OUT = Path(os.environ.get("QSD_OUT", PKG / "output")) / "position"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(D / "prospective/mqt_bench/cohort_enumerator"))
sys.path.insert(0, str(QOL))
from rq3_cohort.core import mutants as MUT
from rq3_cohort.core.representation import canon_json
from qiskit import QuantumCircuit, transpile
from qiskit.qasm3 import dumps as q3dumps

OPS = ("gate_deletion", "gate_insertion", "gate_replacement")
CLS = ("local_basis_amplitude", "phase_parameterized", "entangling_controlled")
STRATA = [(o, c) for o in OPS for c in CLS]
_src = open(D / "external/protocol/impl/external_allocation.py").read(); _ns = {"STRATA": STRATA}
for node in ast.parse(_src).body:
    if isinstance(node, ast.FunctionDef) and node.name == "largest_remainder":
        exec(compile(ast.Module([node], []), "external_allocation", "exec"), _ns)
largest_remainder = _ns["largest_remainder"]


def _gl(s):
    if isinstance(s, list): return s
    try: return json.loads(s)
    except Exception: return ast.literal_eval(s)


def to_gatelist(qc):
    t = transpile(qc, basis_gates=list(MUT.ARITY), optimization_level=0); out = []
    for ins in t.data:
        nm = ins.operation.name
        if nm in ("barrier", "measure"): continue
        g = {"gate": nm, "q": [t.find_bit(q).index for q in ins.qubits]}
        if ins.operation.params: g["angles"] = [float(p) for p in ins.operation.params]
        out.append(g)
    return out


def prep_gates(xa, xb, n):  # data/prospective/mqt_bench/frozen_deps/r2_external.py
    d = xa ^ xb; k = (d & -d).bit_length() - 1
    g = [{"gate": "h", "q": [k]}]
    g += [{"gate": "cx", "q": [k, j]} for j in range(n) if j != k and (d >> j) & 1]
    g += [{"gate": "x", "q": [j]} for j in range(n) if (xa >> j) & 1]
    return g


def subjects():
    S = {}
    for s in json.load(open(D / "prospective/mqt_bench/frozen_deps/S1_SUBJECTS.json")):
        S[s["subject"]] = {"population": "other", "n": int(s["n"]), "prep": [], "gates": _gl(s["base_gates"]),
                           "outreg": _gl(s["output_register_qubits"]),
                           "contract": "unitary" if s["contract_id"] == "C_ARBITRARY_INPUT_UNITARY" else "fixed"}
    for s in json.load(open(D / "prospective/mqt_bench/subjects/SUBJECTS.json")):
        S[s["subject"]] = {"population": "mqt", "n": int(s["n"]), "prep": _gl(s["prep"]), "gates": _gl(s["body"]),
                           "outreg": _gl(s["outreg"]), "contract": s["contract"]}
    v1 = json.load(open(D / "external/protocol/EXTERNAL_COHORT_FREEZE.json"))
    v3 = json.load(open(D / "external/protocol/EXTERNAL_COHORT_FREEZE_v3.json"))
    pairs = {r["subject"]: (r["x_a"], r["x_b"]) for r in v3["realized_inputs"]}
    alloc = {r["subject"]: r["orig_gatelist_sha256"] for r in csv.DictReader(open(D / "external/cohort/EXTERNAL_ALLOCATION.csv"))}
    MODS = {"ParityPhase": "qolumbina.programs.parity.parity_phase", "Is2PowerPhase": "qolumbina.programs.is_two_power.is_two_power_phase",
            "LessThanPhase": "qolumbina.programs.comparator.less_than_phase", "DiagonalZHamiltonian": "qolumbina.programs.hamiltonian.diagonal_hamiltonian",
            "IsingEvolution": "qolumbina.programs.ising.ising", "DraperAdder": "qolumbina.programs.quantum_adder.draper_adder",
            "AdderHamiltonianMixture": "qolumbina.programs.hamiltonian.adder_hamiltonian_mixture"}
    OUTREG = {"ParityPhase": list(range(6)), "Is2PowerPhase": list(range(6)), "LessThanPhase": list(range(5)),
              "DiagonalZHamiltonian": [0, 1, 2], "IsingEvolution": list(range(7)), "DraperAdder": list(range(5, 10)),
              "AdderHamiltonianMixture": list(range(5, 10)), "qft_n4": list(range(4)), "deutsch_n2": [0]}
    for s in v1["subjects"]:
        name = s["subject"]
        if s["group"] == "MgcosA":
            qc = getattr(importlib.import_module(MODS[name]), name)(**s["parameters"])
            assert hashlib.sha256(q3dumps(qc).encode()).hexdigest() == s["circuit_sha256"], name
        else:
            raw = (QASMB / f"small/{name}/{name}.qasm").read_bytes().replace(b"\r\n", b"\n")
            assert hashlib.sha256(raw).hexdigest()[:16] == s["circuit_sha256_16"], name
            qc = QuantumCircuit.from_qasm_str(raw.decode()).remove_final_measurements(inplace=False)
        gl = to_gatelist(qc)
        assert hashlib.sha256(canon_json(gl).encode()).hexdigest() == alloc[name], (name, "orig_gatelist_sha256")
        S[name] = {"population": "external", "n": qc.num_qubits, "prep": prep_gates(*pairs[name], qc.num_qubits) if name in pairs else [],
                   "gates": gl, "outreg": OUTREG[name], "contract": "unitary" if name in MODS else "fixed"}
    return S


def pool(s, sid):
    p, _ = MUT.complete_pool(s["gates"], s["n"], sid); seen, out = set(), []
    for m in p:
        if m["mutated_hash"] in seen: continue
        seen.add(m["mutated_hash"]); out.append(m)
    return out


def _sha(m): return hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest()


def select_third(cands, k=10):
    by = collections.defaultdict(list)
    for m in cands: by[(m["op"], m["gate_class"])].append(m)
    for kk in by: by[kk].sort(key=lambda m: (int(m["anchor_index"]), m["spec"], m["mutated_hash"]))
    alloc = largest_remainder({kk: len(by[kk]) for kk in STRATA}, min(k, len(cands)))
    out = []
    for kk in STRATA:
        L, w = by[kk], alloc[kk]
        idx = [int((j + 0.5) * len(L) / w) for j in range(w)] if w else []
        out += [(kk, L, i) for i in idx]
    return out


if __name__ == "__main__":
    S = subjects()
    arch_pool = collections.defaultdict(set)
    for r in csv.DictReader(open(D / "external/cohort/EXTERNAL_OPPORTUNITY_POOL.csv")): arch_pool[r["subject"]].add(r["mutated_hash"])
    for r in csv.DictReader(open(D / "prospective/mqt_bench/population/MUTATION_POOL.csv")): arch_pool[r["subject"]].add(r["mutated_hash"])
    taken = collections.defaultdict(set)
    for r in csv.DictReader(open(D / "external/cohort/EXTERNAL_ALLOCATION.csv")): taken[r["subject"]].add(r["mutated_hash"])
    for r in csv.DictReader(open(D / "prospective/mqt_bench/population/MUTANT_MANIFEST.csv")): taken[r["subject"]].add(r["mutated_hash"])
    for r in csv.DictReader(open(D / "prospective/mqt_bench/frozen_deps/S2_GENERATED_MUTANTS.csv")): taken[r["subject"]].add(r["mutated_hash"])
    rows, checks, store = [], {}, {}
    for sid, s in S.items():
        dd = pool(s, sid); hs = {m["mutated_hash"] for m in dd}
        checks[sid] = {"pool": len(dd), "archived_pool_match": (hs == arch_pool[sid]) if arch_pool.get(sid) else "no archived pool",
                       "first_rule_mutations_in_pool": f"{len(taken[sid] & hs)}/{len(taken[sid])}"}
        assert taken[sid] <= hs, sid
        for third in ("middle", "last"):
            cands = [m for m in dd if m["third"] == third and m["mutated_hash"] not in taken[sid]]
            for j, (kk, L, i) in enumerate(select_third(cands)):
                m = L[i]
                mid = f"{sid}#p{'M' if third == 'middle' else 'L'}{j:02d}"
                rows.append({"mutant_id": mid, "subject": sid, "population": s["population"], "third": third,
                             "stratum": f"{kk[0]}/{kk[1]}", "location": m["spec"], "anchor_index": m["anchor_index"],
                             "cell_size": len(L), "cell_index": i, "mutated_hash": m["mutated_hash"], "definition_sha256": _sha(m)})
                store[mid] = m["mutated_gates"]
    with open(OUT / "X4_SELECTION.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump({sid: {k: v for k, v in s.items()} for sid, s in S.items()}, open(OUT / "X4_SUBJECTS.json", "w"))
    json.dump(store, open(OUT / "X4_MUTANT_GATES.json", "w"))
    json.dump(checks, open(OUT / "X4_POOL_CHECKS.json", "w"), indent=1)
    print(json.dumps(checks, indent=1))
    print("selected", len(rows), dict(collections.Counter(r["population"] for r in rows)))
