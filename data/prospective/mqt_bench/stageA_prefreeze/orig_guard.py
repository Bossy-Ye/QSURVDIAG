"""Original-program-only QUTest parse/guard/timing check (Stage A). No mutants."""
import json, sys, time
sys.path.insert(0,"/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot/cross_tool_stage/qutest")
sys.path.insert(0,"/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/protocol/impl")
import qutest_adapter as QA
from qutest_execution_adapter import adapt
S=json.load(open(sys.argv[1])); out={}
for k,s in S.items():
    gates=adapt(s["prep"]+s["body"]); n=s["n"]
    a=[QA.marginal_assertion(q, round(s["analytic_marginals_p1"][q],4)) for q in s["outreg"]]
    ts=[]; v=[]
    for r in range(3):
        t0=time.time(); res=QA.run_qutest(QA.make_test(gates,n,a,seed=QA.SEED+r)); ts.append(time.time()-t0); v.append(res[0])
    out[k]=dict(adapted_gates=len(gates),verdicts=v,seconds=[round(x,2) for x in ts],detail=res[1])
    print(k,n,len(gates),v,[round(x,2) for x in ts],res[1],flush=True)
json.dump(out,open(sys.argv[2],"w"),indent=1)
