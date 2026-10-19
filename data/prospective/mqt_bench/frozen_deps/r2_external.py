"""Revision 2, step 3.2: entanglement-witness sensitivity for the external cohort's CL3 cases.

The cohort's originals are built from external generators that are not installed here, so
each subject's original is reconstructed from its frozen insertion mutants: an insertion
`ins@k:g[q]` is undone by removing gate k. Every insertion mutant of a subject must yield
the same original; the reconstruction is used only if they all agree. The harness-side
preparation (|x_a> + |x_b>)/sqrt(2) of the frozen FREEZE_v3 record is prepended to original
and mutant alike, exactly as in the definitive run. Observation equality is recomputed and
checked against the frozen stage-2 ledger before any witness is evaluated.
"""
import csv, json, os, sys, hashlib
import numpy as np
from qiskit import QuantumCircuit
from qiskit.qasm3 import loads as q3loads
from qiskit.quantum_info import Statevector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r2_primary import witness_separation

EXT = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/external_cohort"
PRO = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/manuscript/tse/protocol"
OUT = os.path.dirname(os.path.abspath(__file__))
V3 = json.load(open(PRO + "/EXTERNAL_COHORT_FREEZE_v3.json"))
PAIRS = {r["subject"]: (r["x_a"], r["x_b"]) for r in V3["realized_inputs"]}

def prep_gates(xa, xb, n):  # copied from confirmatory/exec_external.py
    d = xa ^ xb
    k = (d & -d).bit_length() - 1
    g = [{"gate": "h", "q": [k]}]
    g += [{"gate": "cx", "q": [k, j]} for j in range(n) if j != k and (d >> j) & 1]
    g += [{"gate": "x", "q": [j]} for j in range(n) if (xa >> j) & 1]
    return g

def gates_of(path):
    qc = q3loads(open(path).read()); out = []
    for inst in qc.data:
        if inst.operation.name in ("barrier", "measure"): continue
        g = {"gate": inst.operation.name, "q": [qc.find_bit(b).index for b in inst.qubits]}
        if inst.operation.params: g["angles"] = [float(p) for p in inst.operation.params]
        out.append(g)
    return out, qc.num_qubits

def sv(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        getattr(qc, g["gate"])(*g.get("angles", []), *g["q"])
    return np.asarray(Statevector.from_int(0, dims=(2,) * n).evolve(qc).data)

def key(gl): return hashlib.sha256(json.dumps(gl, sort_keys=True).encode()).hexdigest()

def main():
    alloc = list(csv.DictReader(open(EXT + "/EXTERNAL_ALLOCATION.csv")))
    rep = {r["mutant_id"]: r for r in csv.DictReader(open(EXT + "/RUN_002/L5_CERTIFICATES.csv"))}
    rel = {r["mutant_id"]: r for r in csv.DictReader(open(EXT + "/RUN_002/L3_STAGE2_RELATIONS.csv"))}
    originals, audit = {}, {}
    for s in sorted({a["subject"] for a in alloc}):
        recon = set(); n = None
        for a in alloc:
            if a["subject"] != s or a["operator"] != "gate_insertion": continue
            gl, n = gates_of(os.path.join(EXT, a["mutant_path"]))
            k = int(a["location"].split("@")[1].split(":")[0])
            recon.add(json.dumps(gl[:k] + gl[k + 1:], sort_keys=True))
        audit[s] = {"insertion_mutants_used": sum(1 for a in alloc if a["subject"] == s and a["operator"] == "gate_insertion"),
                    "distinct_reconstructions": len(recon)}
        if len(recon) == 1:
            originals[s] = (json.loads(recon.pop()), n)
    rows = []
    for a in alloc:
        mid, s = a["mutant_id"], a["subject"]
        if rep[mid]["diagnostic_outcome"] != "CL3" or s not in originals: continue
        og, n = originals[s]
        prep = prep_gates(*PAIRS[s], n) if s in PAIRS else []
        mg, _ = gates_of(os.path.join(EXT, a["mutant_path"]))
        sva, svb = sv(prep + og, n), sv(prep + mg, n)
        pa, pb = np.abs(sva) ** 2, np.abs(svb) ** 2
        k, sep, mgn, gap = witness_separation(sva, svb, n)
        rows.append({"mutant_id": mid, "subject": s, "group": a["group"], "n": n,
                     "R_O_recomputed": bool(np.max(np.abs(pa - pb)) < 1e-9),
                     "R_O_frozen": rel[mid]["R_O"], "witness_cuts": k,
                     "witness_separating_cuts": len(sep), "witness_min_margin": mgn,
                     "witness_max_entropy_gap": gap})
    with open(os.path.join(OUT, "R2_EXTERNAL_CL3.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    json.dump(audit, open(os.path.join(OUT, "R2_EXTERNAL_RECONSTRUCTION.json"), "w"), indent=1)
    print("reconstruction", audit); print("CL3 rows", len(rows))

if __name__ == "__main__":
    main()
