"""Revision 2, step 2.2 (continued): margins of the remaining floating-point comparisons.

r2_margins.py covers endpoint-state and joint-Z observation equality. This script adds
  - the arbitrary-input unitary contract, | |Tr(U_P^dag U_M)| / 2^n - 1 |, for all 599
    primary pairs (the comparison behind the uniform counterfactual and every declared
    unitary contract);
  - QuCheck's observation, L-infinity over single-qubit X, Y, Z expectations, on every
    qubit and on the declared register, for all 599 primary pairs (frozen xyz() of
    b5_a4_interface.py, copied verbatim);
  - endpoint-state and observation margins for all 270 external-cohort pairs, rebuilt as
    in r2_external.py.
Each recomputed decision at 1e-9 is checked against the frozen ledger before any margin
is used.
"""
import csv, json, os, sys
import numpy as np
sys.path.insert(0, "/Users/mac/Desktop/ZX-STUDY/paper-artifact/github/code/qsurvdiag")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1_lib import MUT, orig, nq, outreg
import e1_relations as REL
from e1_07_diagnose import _unitary
import r2_external as X

PA = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/"
OUT = os.path.dirname(os.path.abspath(__file__))
TOL = 1e-9

def xyz(s, n, qubits):  # verbatim from github/code/experiments/b5_a4_interface.py
    v = []
    for q in qubits:
        for pauli in "XYZ":
            if pauli == "Z":
                v.append(sum((abs(a) ** 2) * (-1 if (i >> q) & 1 else 1) for i, a in enumerate(s)))
                continue
            acc = 0j
            for i, a in enumerate(s):
                j = i ^ (1 << q)
                acc += (np.conj(s[j]) * a) if pauli == "X" else \
                       (1j * (1 if (i >> q) & 1 else -1) * np.conj(s[j]) * a)
            v.append(float(np.real(acc)))
    return np.array(v)

def main():
    con = {r["mutant_id"]: r for r in csv.DictReader(open(PA + "github/results/recovered/599_B1_CONTRACT_RERUN.csv"))}
    # the 599-pair interface ledger behind the paper's counts (T1_4_INTERFACE_599: QuCheck on all qubits);
    # the 546-row B5_A4 ledger predates the recovery and also carries the declared-register column
    t14 = {r["mutant_id"]: r for r in csv.DictReader(open(PA + "github/results/recovered/T1_4_INTERFACE_599.csv"))}
    a4 = {r["mutant_id"]: r for r in csv.DictReader(open(PA + "github/results/decision/B5_A4_INTERFACE_CORRECTED.csv"))}
    rows, uc = [], {}
    for mid in sorted(t14):
        sub = MUT[mid]["subject"]; n = nq[sub]
        if sub not in uc: uc[sub] = _unitary(orig[sub], n)
        um = _unitary(MUT[mid]["gates"], n)
        um_margin = abs(abs(np.trace(uc[sub].conj().T @ um)) / 2 ** n - 1.0)
        sva, _, _ = REL._orig_cache(sub); svb = REL._sv(MUT[mid]["gates"], n)
        qa = float(np.max(np.abs(xyz(sva, n, range(n)) - xyz(svb, n, range(n)))))
        qd = float(np.max(np.abs(xyz(sva, n, outreg[sub]) - xyz(svb, n, outreg[sub]))))
        ok_u = (con[mid]["R_C_unitary"] == ("true" if um_margin < TOL else "false")) if mid in con else None
        ok_qa = t14[mid]["R_O_QuCheck"] == ("True" if qa < TOL else "False")
        ok_qd = (a4[mid]["R_O_QuCheck_declared_register"] == ("true" if qd < TOL else "false")) if mid in a4 else None
        rows.append({"arm": "primary", "pair": mid, "unitary_margin": um_margin,
                     "qucheck_all_margin": qa, "qucheck_decl_margin": qd,
                     "unitary_agrees_frozen": ok_u, "qucheck_all_agrees_frozen": ok_qa,
                     "qucheck_decl_agrees_frozen": ok_qd})
    # external cohort: every allocated pair whose subject reconstructs consistently
    alloc = list(csv.DictReader(open(X.EXT + "/EXTERNAL_ALLOCATION.csv")))
    rel = {r["mutant_id"]: r for r in csv.DictReader(open(X.EXT + "/RUN_002/L3_STAGE2_RELATIONS.csv"))}
    originals = {}
    for s in sorted({a["subject"] for a in alloc}):
        recon, n = set(), None
        for a in alloc:
            if a["subject"] != s or a["operator"] != "gate_insertion": continue
            gl, n = X.gates_of(os.path.join(X.EXT, a["mutant_path"]))
            k = int(a["location"].split("@")[1].split(":")[0])
            recon.add(json.dumps(gl[:k] + gl[k + 1:], sort_keys=True))
        if len(recon) == 1: originals[s] = (json.loads(recon.pop()), n)
    for a in alloc:
        mid, s = a["mutant_id"], a["subject"]
        if s not in originals or mid not in rel: continue
        og, n = originals[s]
        prep = X.prep_gates(*X.PAIRS[s], n) if s in X.PAIRS else []
        mg, _ = X.gates_of(os.path.join(X.EXT, a["mutant_path"]))
        sva, svb = X.sv(prep + og, n), X.sv(prep + mg, n)
        sm = abs(abs(np.vdot(sva, svb)) - 1.0)
        om = float(np.max(np.abs(np.abs(sva) ** 2 - np.abs(svb) ** 2)))
        fr_s, fr_o = rel[mid]["R_S"], rel[mid]["R_O"]
        rows.append({"arm": "external", "pair": mid, "state_margin": sm, "obs_margin": om,
                     "state_agrees_frozen": None if "TRUE" not in fr_s and "FALSE" not in fr_s
                     else (("TRUE" in fr_s) == (sm < TOL)),
                     "obs_agrees_frozen": None if "TRUE" not in fr_o and "FALSE" not in fr_o
                     else (("TRUE" in fr_o) == (om < TOL))})
    keys = sorted({k for r in rows for k in r})
    with open(os.path.join(OUT, "R2_MARGINS_EXT.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("rows", len(rows), "external subjects reconstructed", len(originals))

if __name__ == "__main__":
    main()
