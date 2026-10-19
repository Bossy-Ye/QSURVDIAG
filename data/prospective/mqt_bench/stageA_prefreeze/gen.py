"""Pass 3A.1 Stage-A original-program checks only. No mutants, no QUTest, no outcomes."""
import json, hashlib, collections, itertools, sys
import numpy as np, networkx as nx
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, Operator
from mqt.bench.benchmarks import qwalk, graphstate, hhl, hrs_cumulative_multiplier as hrs, multiplier as mul, rg_qft_multiplier as rg
BASIS = ["x","y","h","sx","rx","ry","z","s","t","p","rz","cx","cz","cp","rxx","rzz"]   # MUT.ARITY (external convention)
def strip(qc): return qc.remove_final_measurements(inplace=False)
def lower(qc): return transpile(qc, basis_gates=BASIS, optimization_level=0, seed_transpiler=0)
def glist(t):
    out=[]
    for i in t.data:
        g={"gate":i.operation.name,"q":[t.find_bit(b).index for b in i.qubits]}
        if i.operation.params: g["angles"]=[round(float(x),12) for x in i.operation.params]
        out.append(g)
    return out
def summary(name, qc):
    s=strip(qc); t=lower(s); gl=glist(t)
    rng=np.random.default_rng(0); fids=[]
    for _ in range(4):
        v=rng.normal(size=2**s.num_qubits)+1j*rng.normal(size=2**s.num_qubits); v/=np.linalg.norm(v)
        a=Statevector(v).evolve(s).data; b=Statevector(v).evolve(t).data; fids.append(abs(np.vdot(a,b)))
    fid=min(fids)
    h=hashlib.sha256(json.dumps(gl,sort_keys=True).encode()).hexdigest()
    return dict(name=name,n=s.num_qubits,gates=len(gl),depth=t.depth(),ops=dict(collections.Counter(g["gate"] for g in gl)),
                min_state_fidelity=round(float(fid),12),sha=h), s, t
R={}
# ---- quantum walk: independent coined walk on the cycle Z_{2^m}, coin last qubit
def walk_ref(m, steps, sign_coin1):
    N=2**m; psi=np.zeros((2,N),complex); psi[0,0]=1
    H=np.array([[1,1],[1,-1]])/np.sqrt(2)
    for _ in range(steps):
        psi=H@psi
        new=np.zeros_like(psi)
        new[1]=np.roll(psi[1], sign_coin1); new[0]=np.roll(psi[0], -sign_coin1)
        psi=new
    return psi
for n in (4,5,6):
    qc=qwalk.create_circuit(n); info,s,t=summary(f"qwalk_{n}",qc)
    sv=Statevector(t).data; m=n-1
    best=None
    for sign in (1,-1):
        for rev in (False,True):
            ref=walk_ref(m,3,sign); vec=np.zeros(2**n,complex)
            for c in (0,1):
                for x in range(2**m):
                    xi=int(format(x,f'0{m}b')[::-1],2) if rev else x
                    vec[(c<<m)|xi]=ref[c,x]
            ov=abs(np.vdot(vec,sv))
            if best is None or ov>best[0]: best=(ov,sign,rev)
    info["contract_check"]={"max_overlap_with_independent_walk":round(best[0],12),"coin1_shift":best[1],"node_bits_reversed":best[2]}
    R[info["name"]]=info; print(info["name"],info["n"],info["gates"],info["depth"],info["min_state_fidelity"],info["contract_check"],flush=True)
# ---- multiplication: |a>|b>|0..> -> |a>|b>|a*b> on the full operand domain
def check_mult(qc, k):
    s=strip(qc); n=s.num_qubits; bad=0
    for a in range(2**k):
        for b in range(2**k):
            idx=a | (b<<k)                         # qiskit little-endian: a on qubits 0..k-1, b next
            out=Statevector.from_int(idx,2**n).evolve(s).data; j=int(np.argmax(abs(out)))
            exp= a | (b<<k) | ((a*b)<<(2*k))
            if j!=exp or abs(abs(out[j])-1)>1e-9: bad+=1
    return bad
for mod,nm,ws in ((hrs,"hrs_mult",(5,9,13)),(mul,"multiplier",(4,8,12)),(rg,"rg_mult",(4,8,12))):
    for n in ws:
        qc=mod.create_circuit(n); k=n//4
        info,s,t=summary(f"{nm}_{n}",qc)
        info["regs"]=[(r.name,r.size) for r in s.qregs]; info["operand_bits"]=k
        info["contract_check"]={"wrong_products_on_full_domain":check_mult(qc,k),"domain":4**k}
        R[info["name"]]=info; print(info["name"],info["n"],info["gates"],info["depth"],info["min_state_fidelity"],info["contract_check"],flush=True)
# ---- graph state, degree 3 (corpus holds degree-2 cycles only)
def stab_ok(t, G):
    sv=Statevector(t); n=t.num_qubits; worst=0
    from qiskit.quantum_info import Pauli
    for v in G.nodes:
        lab=['I']*n; lab[v]='X'
        for u in G.neighbors(v): lab[u]='Z'
        p=Pauli(''.join(reversed(lab)))
        worst=max(worst, abs(1-np.real(sv.expectation_value(p))))
    return worst
for n in (6,8,10):
    for seed in (1,):
        qc=graphstate.create_circuit(n, degree=3, seed=seed); G=nx.random_regular_graph(3,n,seed=seed)
        info,s,t=summary(f"graphstate_d3_{n}_s{seed}",qc)
        info["edges"]=sorted(tuple(sorted(e)) for e in G.edges)
        info["contract_check"]={"max_stabilizer_deviation":round(float(stab_ok(t,G)),12)}
        R[info["name"]]=info; print(info["name"],info["n"],info["gates"],info["depth"],info["min_state_fidelity"],info["contract_check"],flush=True)
# ---- HHL: does the circuit realise A^{-1}|b> for the documented A?
for n in (4,5):
    qc=hhl.create_circuit(n); info,s,t=summary(f"hhl_{n}",qc)
    A=np.array([[1,1],[1,3]]); x=np.linalg.solve(A,np.array([0,1.0])); x/=np.linalg.norm(x)
    sv=Statevector(t).data; n_=t.num_qubits
    # system qubit = qubit 0 (first register); postselect ancilla (last qubit) = 1
    p=np.zeros(2)
    for i,a in enumerate(sv):
        if (i>>(n_-1))&1: p[i&1]+=abs(a)**2
    p=p/p.sum() if p.sum()>0 else p
    info["contract_check"]={"documented_solution_probs":np.round(x**2,6).tolist(),"circuit_postselected_probs":np.round(p,6).tolist(),
                            "regs":[(r.name,r.size) for r in s.qregs]}
    R[info["name"]]=info; print(info["name"],info["n"],info["gates"],info["depth"],info["min_state_fidelity"],info["contract_check"],flush=True)
json.dump(R,open("out/stageA_originals.json","w"),indent=1)
print("done")
