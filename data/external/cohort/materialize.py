"""Materialize the frozen prospective external mutant population.

Enumeration + allocation only. No native test, no endpoint state, no observation,
no QSurvDiag, no CL classification. No RNG and no execution seed is consumed.

largest_remainder is executed from the packaged s2_cohort.py source via AST
extraction, so the apportionment is the packaged function itself; importing the
module is avoided because it is top-level script code that would re-run S2 against
the read-only study tree.
"""
import ast, collections, csv, hashlib, importlib, json, os, sys, time

STUDY = "/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot"
SCR   = os.environ["SCR"]
OUT   = os.environ["OUT"]
sys.path.insert(0, STUDY)
sys.path.insert(0, os.path.join(STUDY, "cross_tool_stage", "qutest"))
sys.path.insert(0, os.path.join(SCR, "qol", "infra", "qolumbina-infrastructure-main"))
sys.path.insert(0, os.path.join(SCR, "pylibs"))

from rq3_feasibility_gate.core import mutants as MUT
from rq3_feasibility_gate.core.representation import canon_json
from qiskit import QuantumCircuit, transpile
from qiskit.qasm3 import dumps as q3dumps

# ---- packaged apportionment, extracted verbatim (no module side effects) ----
S2 = os.path.join(STUDY, "research_repair/phase5_validation/s2_cohort/s2_cohort.py")
_src = open(S2).read()
_tree = ast.parse(_src)
_fn = next(n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name == "largest_remainder")
OPS = ("gate_deletion", "gate_insertion", "gate_replacement")
CLS = ("local_basis_amplitude", "phase_parameterized", "entangling_controlled")
STRATA = [(o, c) for o in OPS for c in CLS]
_ns = {"STRATA": STRATA}
exec(compile(ast.Module(body=[_fn], type_ignores=[]), S2, "exec"), _ns)
largest_remainder = _ns["largest_remainder"]
PACKAGED_FN_SHA = hashlib.sha256(ast.get_source_segment(_src, _fn).encode()).hexdigest()

BASIS = list(MUT.ARITY)          # exactly the enumerator's own vocabulary
PER_SUBJECT = 30
FREEZE = json.load(open("/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/protocol/EXTERNAL_COHORT_FREEZE_v2.json"))
V1 = json.load(open("/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/protocol/EXTERNAL_COHORT_FREEZE.json"))

def to_gatelist(qc):
    t = transpile(qc, basis_gates=BASIS, optimization_level=0)
    out = []
    for inst in t.data:
        nm = inst.operation.name
        if nm in ("barrier", "measure"):
            continue
        qs = [t.find_bit(q).index for q in inst.qubits]
        g = {"gate": nm, "q": qs}
        if inst.operation.params:
            g["angles"] = [float(p) for p in inst.operation.params]
        out.append(g)
    return t, out

# ---------------------------------------------------------------- subjects
QOL = {s["subject"]: s for s in V1["subjects"] if s["group"] == "MgcosA"}
MODS = {
 "ParityPhase":"qolumbina.programs.parity.parity_phase",
 "Is2PowerPhase":"qolumbina.programs.is_two_power.is_two_power_phase",
 "LessThanPhase":"qolumbina.programs.comparator.less_than_phase",
 "DiagonalZHamiltonian":"qolumbina.programs.hamiltonian.diagonal_hamiltonian",
 "IsingEvolution":"qolumbina.programs.ising.ising",
 "DraperAdder":"qolumbina.programs.quantum_adder.draper_adder",
 "AdderHamiltonianMixture":"qolumbina.programs.hamiltonian.adder_hamiltonian_mixture"}
QASM = {"qft_n4": os.path.join(SCR,"ext/QASMBench/small/qft_n4/qft_n4.qasm"),
        "deutsch_n2": os.path.join(SCR,"ext/QASMBench/small/deutsch_n2/deutsch_n2.qasm")}

subjects, hashcheck = [], []
for name, spec in QOL.items():
    qc = getattr(importlib.import_module(MODS[name]), name)(**spec["parameters"])
    h = hashlib.sha256(q3dumps(qc).encode()).hexdigest()
    hashcheck.append({"subject":name,"group":"MgcosA","frozen":spec["circuit_sha256"],
                      "recomputed":h,"match":h==spec["circuit_sha256"]})
    t, gl = to_gatelist(qc)
    subjects.append({"subject":name,"group":"MgcosA","n":qc.num_qubits,"gates":gl,
                     "orig_gatelist_sha256":hashlib.sha256(canon_json(gl).encode()).hexdigest()})
for name, path in QASM.items():
    raw = open(path).read()
    h16 = hashlib.sha256(raw.encode()).hexdigest()[:16]
    frozen = next(s for s in V1["subjects"] if s["subject"]==name)["circuit_sha256_16"]
    hashcheck.append({"subject":name,"group":"QASMBench/Qiskit","frozen":frozen,
                      "recomputed":h16,"match":h16==frozen})
    qc = QuantumCircuit.from_qasm_file(path).remove_final_measurements(inplace=False)
    t, gl = to_gatelist(qc)
    subjects.append({"subject":name,"group":"QASMBench/Qiskit","n":qc.num_qubits,"gates":gl,
                     "orig_gatelist_sha256":hashlib.sha256(canon_json(gl).encode()).hexdigest()})

# ------------------------------------------------- pool + allocation
pool_rows, alloc_rows, census, elig = [], [], [], []
for s in subjects:
    ok, why = MUT.circuit_eligible(s["gates"], s["n"])
    elig.append({"subject":s["subject"],"eligible":ok,"reasons":"; ".join(why) if why else ""})
    pool, _ = MUT.complete_pool(s["gates"], s["n"], s["subject"])
    seen, dedup = set(), []
    for m in pool:
        k = m["mutated_hash"]
        if k in seen: continue
        seen.add(k); dedup.append(m)
    by = collections.defaultdict(list)
    for m in dedup: by[(m["op"], m["gate_class"])].append(m)
    for k in by:
        by[k].sort(key=lambda m: (m["spec"],
                   hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest()))
    avail = {k: len(by[k]) for k in STRATA}
    total = min(PER_SUBJECT, len(dedup))
    alloc = largest_remainder(avail, total)
    picked = []
    for k in STRATA: picked += [(k, m) for m in by[k][:alloc[k]]]
    deficit = total - len(picked)
    if deficit > 0:
        rem = {k: max(0, avail[k]-alloc[k]) for k in STRATA}
        extra = largest_remainder(rem, deficit)
        for k in STRATA:
            if extra[k]: picked += [(k, m) for m in by[k][alloc[k]:alloc[k]+extra[k]]]
    for m in dedup:
        pool_rows.append({"subject":s["subject"],"operator":m["op"],"gate_class":m["gate_class"],
            "location":m["spec"],"stratum":f'{m["op"]}/{m["gate_class"]}',
            "mutated_hash":m["mutated_hash"],"third":m.get("third",""),
            "anchor_index":m.get("anchor_index","")})
    os.makedirs(os.path.join(OUT,"mutants",s["subject"]), exist_ok=True)
    for j,(k,m) in enumerate(picked):
        mid=f'{s["subject"]}#x{j:02d}'
        qc=QuantumCircuit(s["n"])
        for g in m["mutated_gates"]:
            getattr(qc, g["gate"])(*g.get("angles",[]), *[int(q) for q in g["q"]])
        fp=os.path.join("mutants",s["subject"],f"{mid.replace('#','_')}.qasm")
        open(os.path.join(OUT,fp),"w").write(q3dumps(qc))
        alloc_rows.append({"mutant_id":mid,"subject":s["subject"],"group":s["group"],
            "orig_gatelist_sha256":s["orig_gatelist_sha256"],"operator":m["op"],
            "gate_class":m["gate_class"],"stratum":f'{k[0]}/{k[1]}',"location":m["spec"],
            "anchor_index":m.get("anchor_index",""),"third":m.get("third",""),
            "allocation_rank":j,"n_qubits":qc.num_qubits,"gate_count":len(m["mutated_gates"]),
            "mutated_hash":m["mutated_hash"],
            "definition_sha256":hashlib.sha256(canon_json(m["mutated_gates"]).encode()).hexdigest(),
            "mutant_path":fp})
    c=collections.Counter(m["op"] for _,m in picked)
    census.append({"subject":s["subject"],"group":s["group"],"n":s["n"],
        "legal_opportunities":len(pool),"deduplicated":len(dedup),"allocated":len(picked),
        "insertion":c["gate_insertion"],"replacement":c["gate_replacement"],"deletion":c["gate_deletion"]})

def wcsv(fn, rows):
    p=os.path.join(OUT,fn)
    with open(p,"w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return hashlib.sha256(open(p,"rb").read()).hexdigest()
res={"hashcheck":hashcheck,"eligibility":elig,"census":census,
     "packaged_largest_remainder_sha256":PACKAGED_FN_SHA,
     "pool_csv_sha256":wcsv("EXTERNAL_OPPORTUNITY_POOL.csv",pool_rows),
     "alloc_csv_sha256":wcsv("EXTERNAL_ALLOCATION.csv",alloc_rows),
     "census_csv_sha256":wcsv("EXTERNAL_CENSUS.csv",census),
     "total_pool":len(pool_rows),"total_allocated":len(alloc_rows)}
json.dump(res,open(os.path.join(OUT,"_materialize_result.json"),"w"),indent=1)
print(json.dumps({k:v for k,v in res.items() if k not in("hashcheck","eligibility","census")},indent=1))
