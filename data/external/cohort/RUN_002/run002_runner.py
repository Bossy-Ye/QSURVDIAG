"""Run 002 — clean execution and diagnosis of the frozen prospective external cohort.

v4 execution path, applied uniformly:
  frozen program/mutant -> frozen harness-side preparation -> uniform adapter -> QUTest
Run 001 case-level outputs are never read. Results go to a clean RUN_002 directory.
"""
import csv, json, os, sys, hashlib, time, collections
sys.path.insert(0, "."); sys.path.insert(0, "../cross_tool_stage/qutest")
sys.path.insert(0, "definitive_rerun_b1")
import numpy as np
from qiskit.qasm3 import loads as q3loads
from qiskit import QuantumCircuit, transpile

import e1_lib as L
from e1_lib import MUT, orig, nq, outreg, assertions_for, execute, REPS
import e1_relations as REL
from qsurvdiag_confirmatory import T, F, certify, empirical
from b1_smin_runner import guard_smin
from qutest_adapter import make_test, run_qutest, INNER_SHOTS, SEED
from qutest_execution_adapter import adapt, is_identity, ADAPTER_VERSION
from guard_integrity import check_execution_support, guarded, GUARD_INTEGRITY_VERSION

# frozen definitions extracted by AST (e1_07_diagnose has an unreachable module-level path)
import ast as _a
_s7 = open("e1_07_diagnose.py").read(); _t7 = _a.parse(_s7)
_w = {"UNITARY_CONTRACTS","_unitary","_uc","evidence_for"}; _k=[]
for _n in _t7.body:
    if isinstance(_n,_a.FunctionDef) and _n.name in _w: _k.append(_n)
    elif isinstance(_n,_a.Assign) and any(isinstance(t,_a.Name) and t.id in _w for t in _n.targets): _k.append(_n)
_ns={"QuantumCircuit":QuantumCircuit,"Operator":__import__("qiskit.quantum_info",fromlist=["Operator"]).Operator}
exec(compile(_a.Module(body=_k,type_ignores=[]),"e1_07_diagnose.py","exec"),_ns)
UNITARY_CONTRACTS=_ns["UNITARY_CONTRACTS"]; _unitary=_ns["_unitary"]; _uc=_ns["_uc"]; evidence_for=_ns["evidence_for"]

EXT="/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/external_cohort"
PRO="/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/protocol"
OUT=EXT+"/RUN_002"; os.makedirs(OUT,exist_ok=True)
V3=json.load(open(PRO+"/EXTERNAL_COHORT_FREEZE_v3.json"))
OUTREG={"ParityPhase":list(range(6)),"Is2PowerPhase":list(range(6)),"LessThanPhase":list(range(5)),
 "DiagonalZHamiltonian":[0,1,2],"IsingEvolution":list(range(7)),"DraperAdder":[5,6,7,8,9],
 "AdderHamiltonianMixture":[5,6,7,8,9],"qft_n4":[0,1,2,3],"deutsch_n2":[0]}
CONTRACT={s:"C_ARBITRARY_INPUT_UNITARY" for s in
 ("ParityPhase","Is2PowerPhase","LessThanPhase","DiagonalZHamiltonian","IsingEvolution",
  "DraperAdder","AdderHamiltonianMixture")}
CONTRACT.update({"qft_n4":"C_FIXED_INPUT_STATE","deutsch_n2":"C_FIXED_INPUT_STATE"})
PAIRS={r["subject"]:(r["x_a"],r["x_b"]) for r in V3["realized_inputs"]}
GROUP={s:("MgcosA" if s in PAIRS else "QASMBench/Qiskit") for s in OUTREG}

def prep_gates(xa,xb,n):
    d=xa^xb; k=(d&-d).bit_length()-1
    g=[{"gate":"h","q":[k]}]
    g+=[{"gate":"cx","q":[k,j]} for j in range(n) if j!=k and (d>>j)&1]
    g+=[{"gate":"x","q":[j]} for j in range(n) if (xa>>j)&1]
    return g
def qasm_to_gates(p):
    qc=q3loads(open(p).read()); out=[]
    for i in qc.data:
        if i.operation.name in ("barrier","measure"): continue
        g={"gate":i.operation.name,"q":[qc.find_bit(b).index for b in i.qubits]}
        if i.operation.params: g["angles"]=[float(x) for x in i.operation.params]
        out.append(g)
    return out,qc.num_qubits
def gh(g): return hashlib.sha256(json.dumps(g,sort_keys=True,default=str).encode()).hexdigest()

alloc=list(csv.DictReader(open(EXT+"/EXTERNAL_ALLOCATION.csv")))
subs=sorted({a["subject"] for a in alloc})
sys.path.insert(0,os.environ["QOLROOT"])
import importlib
from rq3_feasibility_gate.core import mutants as MM
BASIS=list(MM.ARITY)
MODS={"ParityPhase":("qolumbina.programs.parity.parity_phase",{"input_qubits":6}),
 "Is2PowerPhase":("qolumbina.programs.is_two_power.is_two_power_phase",{"input_qubits":6}),
 "LessThanPhase":("qolumbina.programs.comparator.less_than_phase",{"input_qubits":5,"integer":10}),
 "DiagonalZHamiltonian":("qolumbina.programs.hamiltonian.diagonal_hamiltonian",{"input_qubits":3,"t":0.2}),
 "IsingEvolution":("qolumbina.programs.ising.ising",{"input_qubits":7,"J":1.0,"B":1.0,"t":0.2}),
 "DraperAdder":("qolumbina.programs.quantum_adder.draper_adder",{"input_qubits":5}),
 "AdderHamiltonianMixture":("qolumbina.programs.hamiltonian.adder_hamiltonian_mixture",{"input_qubits":5,"t":0.2})}
QF={"qft_n4":os.environ["SCR"]+"/ext/QASMBench/small/qft_n4/qft_n4.qasm",
    "deutsch_n2":os.environ["SCR"]+"/ext/QASMBench/small/deutsch_n2/deutsch_n2.qasm"}
def to_gl(qc):
    t=transpile(qc,basis_gates=BASIS,optimization_level=0); out=[]
    for i in t.data:
        if i.operation.name in ("barrier","measure"): continue
        g={"gate":i.operation.name,"q":[t.find_bit(b).index for b in i.qubits]}
        if i.operation.params: g["angles"]=[float(x) for x in i.operation.params]
        out.append(g)
    return out
PREP={}; PROG={}; ADAPTED_ORIG={}
for s in subs:
    _,n=qasm_to_gates(os.path.join(EXT,[a for a in alloc if a["subject"]==s][0]["mutant_path"]))
    nq[s]=n; outreg[s]=OUTREG[s]
    PREP[s]=prep_gates(*PAIRS[s],n) if s in PAIRS else []
    if s in MODS: mod,kw=MODS[s]; qc=getattr(importlib.import_module(mod),s)(**kw)
    else: qc=QuantumCircuit.from_qasm_file(QF[s]).remove_final_measurements(inplace=False)
    PROG[s]=to_gl(qc)
    orig[s]=adapt(PREP[s]+PROG[s])          # uniform adapter, no-op where unnecessary
    ADAPTED_ORIG[s]=gh(orig[s])
FROZEN_H={}; ADAPTED_H={}
for a in alloc:
    gl,_=qasm_to_gates(os.path.join(EXT,a["mutant_path"]))
    FROZEN_H[a["mutant_id"]]=a["mutated_hash"]
    full=adapt(PREP[a["subject"]]+gl)
    ADAPTED_H[a["mutant_id"]]=gh(full)
    MUT[a["mutant_id"]]={"subject":a["subject"],"population":"prospective","gates":full,
                         "order":int(a["allocation_rank"])}
def contract_equivalent(mid):
    m=MUT[mid]; sub=m["subject"]; n=nq[sub]
    if CONTRACT[sub] in UNITARY_CONTRACTS:
        if sub not in _uc: _uc[sub]=_unitary(orig[sub],n)
        tr=abs(np.trace(_uc[sub].conj().T@_unitary(m["gates"],n)))/(2**n)
        return bool(abs(tr-1.0)<1e-9)
    sva,_,_=REL._orig_cache(sub)
    return REL.state_equal(sva,REL._sv(m["gates"],n))

STAGE=sys.argv[1]
if STAGE=="guard":
    rows=[]
    for s in subs:
        A=assertions_for(s,"S_MIN")
        sup=check_execution_support(s,orig[s],nq[s],A,REPS,SEED,make_test,run_qutest,INNER_SHOTS)
        frozen=guard_smin(s)
        r=guarded(s,sup,frozen); r["adapted_orig_sha256"]=ADAPTED_ORIG[s]
        r["adapter_applied"]=not is_identity(PREP[s]+PROG[s]); rows.append(r)
        print("GUARD",s,r["cell_status"],"support",r["execution_support"],"falsefails",r["false_fails"],flush=True)
    json.dump(rows,open(OUT+"/L1_ORIGINAL_GUARD.json","w"),indent=1)
elif STAGE=="exec":
    led=open(OUT+"/L2_NATIVE.jsonl","a"); done=set()
    if os.path.exists(OUT+"/L2_NATIVE.jsonl"):
        for ln in open(OUT+"/L2_NATIVE.jsonl"):
            try: done.add(json.loads(ln)["mutant_id"])
            except Exception: pass
    todo=[a["mutant_id"] for a in alloc if a["mutant_id"] not in done]
    print(f"native: {len(todo)} of {len(alloc)}",flush=True)
    for i,mid in enumerate(todo):
        try: rec=execute(mid,"S_MIN")
        except Exception as e: rec={"mutant_id":mid,"subject":MUT[mid]["subject"],"native_verdict":"ERROR","error":f"{type(e).__name__}: {e}"[:200]}
        rec["frozen_mutant_hash"]=FROZEN_H[mid]; rec["adapted_execution_hash"]=ADAPTED_H[mid]
        rec["adapter_version"]=ADAPTER_VERSION
        led.write(json.dumps(rec,default=str)+"\n"); led.flush()
        if (i+1)%30==0: print(f"  {i+1}/{len(todo)}",flush=True)
    led.close()
elif STAGE=="diag":
    cells=[json.loads(l) for l in open(OUT+"/L2_NATIVE.jsonl")]
    guards={g["subject"]:g for g in json.load(open(OUT+"/L1_ORIGINAL_GUARD.json"))}
    rel_rows=[]; ev_rows=[]; cert_rows=[]
    for c in sorted(cells,key=lambda x:x["mutant_id"]):
        mid=c["mutant_id"]; sub=c["subject"]; native=c.get("native_verdict")
        kills=c.get("kills_recorded",0); reps=c.get("reps",REPS)
        rc=contract_equivalent(mid); rel=REL.relations(mid,"S_MIN",rc)
        rel_rows.append({"mutant_id":mid,"subject":sub,"group":GROUP[sub],
            **{k:str(rel[k]) for k in ("R_C","R_S","R_O","R_A","R_T")},
            "max_universe_d_a":rel["max_universe_d_a"],"max_suite_d_a":rel["max_suite_d_a"]})
        if native=="KILLED":
            ev={}; out={"diagnostic_outcome":"NA_KILLED","candidate":"","required":"","failed":"","unknown":"","unresolved_reason":""}
        else:
            ev=evidence_for(None,native,"S_MIN"); ev["OB02"]=guards[sub]["OB02"]
            res=certify({k:rel[k] for k in ("R_C","R_S","R_O","R_A","R_T")},ev,empirical_verdict=empirical(kills,reps))
            out={"diagnostic_outcome":res["report"],"candidate":res["candidate"] or "",
                 "required":";".join(res["required"]),"failed":";".join(res["failed"]),
                 "unknown":";".join(res["unknown"]),"unresolved_reason":res["unresolved_reason"] or ""}
        ev_rows.append({"mutant_id":mid,"subject":sub,"native_verdict":native,**{k:v for k,v in sorted(ev.items())}})
        cert_rows.append({"mutant_id":mid,"subject":sub,"group":GROUP[sub],"native_verdict":native,
            "kills_recorded":kills,"reps":reps,"frozen_mutant_hash":c.get("frozen_mutant_hash",""),
            **{k:str(rel[k]) for k in ("R_C","R_S","R_O","R_A","R_T")},**out})
    for fn,rows in (("L3_STAGE2_RELATIONS.csv",rel_rows),("L4_EVIDENCE.csv",ev_rows),("L5_CERTIFICATES.csv",cert_rows)):
        cols=[]
        for r in rows:
            for k in r:
                if k not in cols: cols.append(k)
        with open(OUT+"/"+fn,"w",newline="") as fh:
            w=csv.DictWriter(fh,fieldnames=cols,restval="",lineterminator="\n"); w.writeheader(); w.writerows(rows)
    print("certificates:",len(cert_rows),flush=True)
