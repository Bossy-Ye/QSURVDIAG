"""Ideal effect of the recorded output-condition suites (S_SPEC) and of suites that express the
recorded or cited condition in full, on the 239 pairs of the eight subjects. No sampling.
Run in artifact/outcomes of the input tree that scripts/reproduce_analytic.py assembles."""
import csv, os, sys, collections
import numpy as np
sys.path.insert(0, os.getcwd())
import r2v_lib as V
from e1_lib import MUT, orig, nq
import e1_relations as REL
TH = V.THETA
final = {r["mutant_id"]: r for r in csv.DictReader(open("R2V_FINAL_PRIMARY.csv"))}
def dist_target(sub, n):
    t = np.zeros(2 ** n)
    if sub.startswith("ghz"): t[0] = t[-1] = 0.5
    elif sub.startswith("qft"): t[:] = 1 / 2 ** n
    elif sub.startswith("wstate"):
        for q in range(n): t[1 << q] = 1 / n
    return t
def kills(sub, n, pm):
    """(recorded S_SPEC kills, full-condition suite kills), each from ideal differences against spec references."""
    if sub.startswith("ghz"):
        k = V.tvd(pm, dist_target(sub, n)) > TH; return k, k
    if sub.startswith(("qft", "wstate")):
        ref = 0.5 if sub.startswith("qft") else 1 / n
        rec = any(abs(V.marg(pm, n, q) - ref) > TH for q in range(n))
        return rec, rec or V.tvd(pm, dist_target(sub, n)) > TH
    if sub.startswith("simon"):
        rec = any(abs(V.marg(pm, n, q) - 0.5) > TH for q in (0, 1))
        return rec, rec or abs(V.zexp(pm, n, 0b11) - 1.0) > TH
subs = ("ghz_4", "ghz_5", "ghz_7", "qft_4", "qft_5", "qft_6", "simon_4", "wstate_4")
tab = collections.defaultdict(collections.Counter)
for mid, m in MUT.items():
    sub = m["subject"]
    if sub not in subs or mid not in final: continue
    n = nq[sub]
    po = np.abs(REL._sv(orig[sub], n)) ** 2
    assert kills(sub, n, po) == (False, False), (sub, "original fails its output-condition suite")
    pm = np.abs(REL._sv(m["gates"], n)) ** 2
    rec, full = kills(sub, n, pm)
    rep = final[mid]["v2_report"]
    tab[sub][(rep, rec, full)] += 1
tot = collections.Counter()
for sub in subs:
    print(sub, dict(sorted(tab[sub].items())))
    for (rep, rec, full), c in tab[sub].items(): tot[(rep, rec, full)] += c
print("\nall 239 (v2_report, recorded-suite kill, full-condition kill):", dict(sorted(tot.items())))
for lab in ("CL3", "CL4"):
    print(lab, "recorded kills", sum(c for (r, a, b), c in tot.items() if r == lab and a), "full-condition kills", sum(c for (r, a, b), c in tot.items() if r == lab and b))
print("NA_KILLED pairs newly killed only by the full condition:", sum(c for (r, a, b), c in tot.items() if r == "NA_KILLED" and b and not a))
