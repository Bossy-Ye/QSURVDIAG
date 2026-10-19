import sys as _sys; _sys.dont_write_bytecode = True   # keep the package free of interpreter caches
# Copy of data/primary/records/b3_output_condition.py; only path handling and output location differ.
# Run by scripts/reproduce_analytic.py with the study library on the import path (requires Qiskit).
"""RT1 -- the algorithm-level output-condition counterfactual for Simon and Bernstein-Vazirani.

The declared contract for these subjects is endpoint-state equality, which is strictly
stronger than what the algorithm's own output condition requires. Read at the output
condition's own strength, a mutant that changes the endpoint state but still meets the
condition becomes contract-equivalent.

Output conditions, taken from SSPEC_PROVENANCE.json and not invented here:
  simon_4  "input-register distribution uniform over {y : y.s = 0 mod 2}, s = 11",
           expected parameter {"00": 0.5, "11": 0.5}, grounded in the frozen manifest.
  bv_n     "the query register holds the hidden string s with certainty". The string is
           recorded nowhere, so it is read from the ORIGINAL program: the condition is
           that the mutant's output register is a point mass on the same basis state.
           SSPEC_PROVENANCE labels this REFERENCE_DERIVED, and it is reported as such.

Run with POP=546 or POP=599.
"""
import csv, json, os, sys, collections
import numpy as np
sys.path.insert(0,"."); sys.path.insert(0,"../cross_tool_stage/qutest")
from e1_lib import MUT, orig, nq, outreg
import e1_relations as REL
EPS = 1e-9
POP = os.environ.get("POP","599")
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "lib"))
from paths import orig as _porig, out_dir as _out_dir
REFP={"599": str(_porig("data/primary/records/T1_3_REFERENCE_599.csv"))}[POP]   # the 546-stage input is not packaged
COL ={"546":"published_report","599":"report"}[POP]

def outdist(gates, sub):
    """distribution over the declared output register"""
    n=nq[sub]; p=np.abs(REL._sv(gates,n))**2; idx=np.arange(2**n)
    Q=outreg[sub]; d=collections.Counter()
    for i in np.nonzero(p)[0]:
        key="".join("1" if (int(i)>>q)&1 else "0" for q in Q)
        d[key]+=float(p[i])
    return d

def meets(mid):
    sub=MUT[mid]["subject"]; dm=outdist(MUT[mid]["gates"], sub)
    if sub.startswith("simon"):
        # uniform over {y : y.s = 0 mod 2} with s = 11, i.e. {"00","11"} at 0.5 each
        tgt={"00":0.5,"11":0.5}
        return all(abs(dm.get(k,0.0)-v)<EPS for k,v in tgt.items()) and \
               all(abs(v)<EPS for k,v in dm.items() if k not in tgt)
    # bv: point mass on the same basis state the ORIGINAL yields (reference-derived)
    do=outdist(orig[sub], sub)
    so=max(do, key=do.get)
    if abs(do[so]-1.0)>=EPS: return False           # original itself not deterministic
    return abs(dm.get(so,0.0)-1.0)<EPS

ref={r["mutant_id"]:r for r in csv.DictReader(open(REFP))}
pool=[m for m,r in ref.items()
      if r["subject"].startswith(("simon","bv")) and r[COL]!="NA_KILLED"]
movers=[m for m in pool if ref[m][COL]!="CL1" and meets(m)]
out_of=[m for m in pool if ref[m][COL]=="CL1" and not meets(m)]
by=collections.Counter(ref[m][COL] for m in movers)
allcl3=sum(1 for r in ref.values() if r[COL]=="CL3")
print(f"population {POP}")
print(f"  simon+bv non-killed        : {len(pool)}")
print(f"  move INTO contract equivalence: {len(movers)}   from {dict(by)}")
print(f"  move OUT of it               : {len(out_of)}")
print(f"  of the movers, CL3           : {by.get('CL3',0)}  of {allcl3} total CL3 reports")
json.dump({"population":POP,"pool":len(pool),"movers":len(movers),"out":len(out_of),
           "movers_by_report":dict(by),"total_cl3":allcl3},
          open(_out_dir("analytic") / f"outcond_{POP}.json","w"), indent=2)
