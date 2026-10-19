"""Case-by-case agreement between the ideal prediction and the native verdict of the corrected output-condition
suites, and the four surviving Simon cases. No sampling.
Run in artifact/outcomes of the input tree that scripts/reproduce_analytic.py assembles:
  python -I oc_casewise.py <OC_RUNS.csv> <out csv>"""
import csv, os, sys, collections
import numpy as np
sys.path.insert(0, os.getcwd())
import r2v_lib as V
from e1_lib import MUT, orig, nq
import e1_relations as REL
TH = V.THETA
def target(sub, n):
    t = np.zeros(2 ** n)
    if sub.startswith("qft"): t[:] = 1 / 2 ** n
    else:
        for q in range(n): t[1 << q] = 1 / n
    return t
def predicted_kill(sub, n, pm):
    if sub.startswith("simon"):
        return any(abs(V.marg(pm, n, q) - 0.5) > TH for q in (0, 1)) or abs(V.zexp(pm, n, 0b11) - 1.0) > TH
    ref = 0.5 if sub.startswith("qft") else 1 / n
    return any(abs(V.marg(pm, n, q) - ref) > TH for q in range(n)) or V.tvd(pm, target(sub, n)) > TH
nat = collections.defaultdict(list)
for r in csv.DictReader(open(sys.argv[1])):
    if r["kind"] == "mutant": nat[r["case"]].append(r["verdict"])
final = {r["mutant_id"]: r for r in csv.DictReader(open("R2V_FINAL_PRIMARY.csv"))}
rows, agree = [], 0
for mid, v in sorted(nat.items()):
    sub = MUT[mid]["subject"]; n = nq[sub]
    pm = np.abs(REL._sv(MUT[mid]["gates"], n)) ** 2
    pk = predicted_kill(sub, n, pm); k = v.count("KILLED")
    nv = "KILLED" if k == 12 else ("SURVIVED" if k == 0 else f"SPLIT {k}/12")
    ok = (nv == "KILLED") == pk and not nv.startswith("SPLIT"); agree += ok
    f = final[mid]
    rows.append({"mutant_id": mid, "subject": sub, "baseline_report": f["v2_report"], "witness": f"{f['w_kind']} {f['w_key']}".strip(),
                 "predicted_kill": pk, "native": nv, "agree": ok})
with open(sys.argv[2], "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
print(f"cases {len(rows)}, agreeing {agree}")
for r in rows:
    if r["subject"] == "simon_4" and r["baseline_report"] == "CL4" and r["native"] != "KILLED": print("surviving Simon suite omission:", r)
