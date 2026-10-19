"""Revision 2, step 3: analytic rerun for the published-corpus frame and the width set.

Same universes as r2_primary.py. Only pairs whose frozen report is CL5 (closure) or CL3
(entanglement witness) are recomputed; adding assertion kinds cannot move any other
report, because it can only turn R_A from false to true and R_A is already true for CL4.
Circuits are the frozen QASM files under zenodo/inputs/programs; the realized input is
|0...0> and the observation is the joint Z distribution over all qubits, as in the arms.
"""
import csv, json, os, sys, glob, time
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Statevector
sys.path.insert(0, "/Users/mac/Desktop/ZX-STUDY/paper-artifact/github/code/qsurvdiag")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_relations as REL
from qsurvdiag_confirmatory import exists_above, T, F, U
from r2_primary import hellinger, kl, pearson_all, most_frequent_sep, witness_separation, tri

PA = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/"
PROG = PA + "zenodo/inputs/programs/"
OUT = os.path.dirname(os.path.abspath(__file__))
THETA = 0.05

def find(pid, kind):
    hits = glob.glob(PROG + f"*/{pid}_{kind}.qasm")
    return sorted(hits)[0] if hits else None

def state(path):
    qc = qasm2.loads(open(path).read(), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    qc = qc.remove_final_measurements(inplace=False)
    return np.asarray(Statevector.from_instruction(qc).data), qc.num_qubits

def evaluate(pid, report, case_set=None):
    po = (PROG + f"{case_set}/{pid}_origin.qasm") if case_set else find(pid, "origin")
    pm = (PROG + f"{case_set}/{pid}_mutant.qasm") if case_set else find(pid, "mutant")
    sva, n = state(po); svb, _ = state(pm)
    pa, pb = np.abs(sva) ** 2, np.abs(svb) ** 2
    ud5 = REL.universe_diffs(pa, pb, n)
    extra = [hellinger(pb, pa), kl(pb, pa)]
    ca, cb = pearson_all(pa, n), pearson_all(pb, n)
    corr = [abs(ca[k] - cb[k]) for k in ca]
    mf = most_frequent_sep(pa, pb)
    row = {"pair_id": pid, "n": n, "report": report, "max_U5": max(ud5),
           "hellinger": extra[0], "kl": extra[1], "max_corr": max(corr) if corr else 0.0,
           "most_frequent_sep": mf, "R_O_recomputed": bool(np.max(np.abs(pa - pb)) < 1e-9),
           "RA5": tri(exists_above(ud5, THETA)), "RAcert": tri(exists_above(ud5 + extra, THETA)),
           "RAcond": tri(exists_above(ud5 + extra + corr + ([mf] if mf is not None else []), THETA))}
    if report == "CL3":
        k, sep, mg, gap = witness_separation(sva, svb, n)
        row.update({"witness_cuts": k, "witness_separating_cuts": len(sep),
                    "witness_min_margin": mg, "witness_max_entropy_gap": gap})
    return row

def main():
    t0 = time.time()
    corpus = [json.loads(l) for l in open(PA + "github/results/corpus/T2A_STRATIFIED_RAW.jsonl")]
    out = []
    for r in corpus:
        if r["diagnostic_outcome"] in ("CL3", "CL5"):
            row = evaluate(r["pair_id"], r["diagnostic_outcome"], r["case_set"])
            row.update({"arm": "corpus", "case_set": r["case_set"],
                        "frozen_max_U5": r["max_universe_separation"], "frozen_R_A": r["R_A"]})
            out.append(row)
    print("corpus done", len(out), round(time.time() - t0, 1), "s", flush=True)
    for r in csv.DictReader(open(PA + "github/results/scale/B2_SCALE_FRESH.csv")):
        if r["report"] in ("CL3", "CL5"):
            row = evaluate(r["pair_id"], r["report"])
            row.update({"arm": "width", "case_set": r["source"], "frozen_max_U5": "",
                        "frozen_R_A": r["R_A"]})
            out.append(row)
    keys = sorted({k for r in out for k in r})
    with open(os.path.join(OUT, "R2_CORPUS_WIDTH_PAIRS.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
    print("all done", len(out), round(time.time() - t0, 1), "s")

if __name__ == "__main__":
    main()
