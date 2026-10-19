"""Pass 56E: characterise the historical depth count (13/52) on untranspiled source circuits. Read-only; prints only."""
import csv, json
from qiskit import QuantumCircuit
Q = "/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot"; rd = lambda p: list(csv.DictReader(open(p)))
def src(g, n):
    c = QuantumCircuit(n)
    for x in g: getattr(c, x["gate"])(*x.get("angles", []), *x["q"])
    return c.depth()
led = [r for r in rd(f"{Q}/paper_freeze/CANONICAL_RESULT_LEDGER.csv") if r["final_semantic_status"] == "EQUIVALENT"]
MP = {r["mutant_id"]: r for r in rd(f"{Q}/final_empirical_study/MUTANT_POPULATION.csv")}
PM = {r["program"]: r for r in rd(f"{Q}/final_empirical_study/PROGRAM_MANIFEST.csv")}
ne = gt = 0
for r in led:
    m = MP[r["mutant_id"]]; p = PM[m["program"]]
    d0, d1 = src(json.loads(p["base_gates"]), int(p["n"])), src(json.loads(m["mutated_gates"]), int(p["n"]))
    ne += d0 != d1; gt += d1 > d0
print({"source_depth_differs": ne, "source_depth_exceeds_original (fails 'depth <= original')": gt})
