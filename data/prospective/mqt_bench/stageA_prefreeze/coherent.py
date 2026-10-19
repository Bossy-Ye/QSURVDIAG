"""Original-only: coherent correctness of rg_qft_multiplier and input-weight arithmetic. No mutants."""
import numpy as np, json
from qiskit.quantum_info import Statevector
from mqt.bench.benchmarks import rg_qft_multiplier as rg
res={}
for n in (8,12):
    k=n//4; s=rg.create_circuit(n).remove_final_measurements(inplace=False)
    ph=[]; 
    for a in range(2**k):
        for b in range(2**k):
            v=Statevector.from_int(a|(b<<k),2**n).evolve(s).data
            exp=a|(b<<k)|((a*b)<<(2*k)); ph.append(np.angle(v[exp]))
    ph=np.array(ph); spread=float(np.max(np.abs(np.angle(np.exp(1j*(ph-ph[0]))))))
    # declared full-domain input: overlap with ideal phase-free product state
    D=4**k; ideal=np.zeros(2**n,complex)
    for a in range(2**k):
        for b in range(2**k): ideal[a|(b<<k)|((a*b)<<(2*k))]=1/np.sqrt(D)
    inp=np.zeros(2**n,complex)
    for a in range(2**k):
        for b in range(2**k): inp[a|(b<<k)]=1/np.sqrt(D)
    out=Statevector(inp).evolve(s).data
    res[f"rg_mult_{n}"]=dict(operand_bits=k,max_relative_phase_rad=round(spread,12),
        overlap_full_domain_with_ideal=round(float(abs(np.vdot(ideal,out))),12),
        weight_per_basis_input=1/D, max_marginal_shift_one_wrong_product=1/D, theta=0.05,
        one_wrong_product_exceeds_theta=bool(1/D>0.05))
    # two-state precedent input: (1,1) and (2^k-1,2^k-1)
    xa=1|(1<<k); xb=(2**k-1)|((2**k-1)<<k)
    inp2=np.zeros(2**n,complex); inp2[xa]=inp2[xb]=1/np.sqrt(2)
    o2=Statevector(inp2).evolve(s).data; p=np.abs(o2)**2
    res[f"rg_mult_{n}"]["two_state_input_marginals"]=[round(float(sum(p[i] for i in range(2**n) if (i>>q)&1)),4) for q in range(n)]
print(json.dumps(res,indent=1))
json.dump(res,open("out/coherent_check.json","w"),indent=1)
