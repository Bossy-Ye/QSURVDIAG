import json, numpy as np, networkx as nx, hashlib
from qiskit import transpile
from qiskit.quantum_info import Statevector
from mqt.bench.benchmarks import qwalk, graphstate, rg_qft_multiplier as rg
BASIS=["x","y","h","sx","rx","ry","z","s","t","p","rz","cx","cz","cp","rxx","rzz"]
def gl(qc):
    t=transpile(qc.remove_final_measurements(inplace=False),basis_gates=BASIS,optimization_level=0,seed_transpiler=0); out=[]
    for i in t.data:
        g={"gate":i.operation.name,"q":[t.find_bit(b).index for b in i.qubits]}
        if i.operation.params: g["angles"]=[float(x) for x in i.operation.params]
        out.append(g)
    return out, t.num_qubits
S={}
for n in (4,5):
    g,nq=gl(qwalk.create_circuit(n)); S[f"qwalk_{n}"]=dict(n=nq,prep=[],body=g,contract="C_FIXED_INPUT_STATE",outreg=list(range(nq)))
for n in (8,12):
    k=n//4; g,nq=gl(rg.create_circuit(n)); prep=[{"gate":"h","q":[q]} for q in range(2*k)]
    S[f"rg_mult_{n}"]=dict(n=nq,prep=prep,body=g,contract="C_ARBITRARY_INPUT_UNITARY",outreg=list(range(nq)))
for n in (6,8):
    seed=0
    while not nx.is_connected(nx.random_regular_graph(3,n,seed=seed)): seed+=1
    g,nq=gl(graphstate.create_circuit(n,degree=3,seed=seed)); S[f"graphstate_d3_{n}"]=dict(n=nq,prep=[],body=g,contract="C_FIXED_INPUT_STATE",outreg=list(range(nq)),seed=seed,
        edges=sorted(tuple(sorted(e)) for e in nx.random_regular_graph(3,n,seed=seed).edges))
from qiskit import QuantumCircuit
for k,s in S.items():
    qc=QuantumCircuit(s["n"])
    for g in s["prep"]+s["body"]:
        getattr(qc,g["gate"])(*(g.get("angles",[])+g["q"]))
    p=np.abs(Statevector(qc).data)**2; n=s["n"]
    s["analytic_marginals_p1"]=[float(sum(p[i] for i in range(2**n) if (i>>q)&1)) for q in range(n)]
    s["sha_body"]=hashlib.sha256(json.dumps(s["body"],sort_keys=True).encode()).hexdigest()
    s["ops"]={}
    for g in s["body"]: s["ops"][g["gate"]]=s["ops"].get(g["gate"],0)+1
    print(k,n,len(s["body"]),s["ops"],[round(x,4) for x in s["analytic_marginals_p1"]], s.get("seed"), s.get("edges"))
json.dump(S,open("out/candidate_subjects.json","w"))
