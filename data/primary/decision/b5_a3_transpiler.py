"""A3 -- transpiler-equivalence recall across configurations.

The paper reports 3 of 85 certified at one configuration.  This sweeps
optimization levels 0-3 x three basis sets x three seeds over the same 85 pairs
the declared contracts hold equivalent.  Plan hash ac1f75d4.
"""
import csv, json, sys, itertools, time
sys.path.insert(0, "."); sys.path.insert(0, "../cross_tool_stage/qutest")
from e1_lib import orig, nq, MUT
from qiskit import QuantumCircuit, transpile, qasm2

B1 = "definitive_rerun_b1"; OUT = "definitive_rerun_b5"
BASES = {"rz_sx_x_cx": ["rz", "sx", "x", "cx"],
         "u_cx":       ["u", "cx"],
         "rz_ry_rx_cz":["rz", "ry", "rx", "cz"]}
LEVELS, SEEDS = (0, 1, 2, 3), (20260827, 7, 12345)

PAIRS = [r for r in csv.DictReader(open(f"{B1}/B1_CONTRACT_RERUN.csv"))
         if r["report_declared"] == "CL1"]
print(f"pairs the declared contracts hold equivalent: {len(PAIRS)}\n")

def build(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", [])
        (getattr(qc, g["gate"])(*a, *[int(q) for q in g["q"]]) if a
         else getattr(qc, g["gate"])(*[int(q) for q in g["q"]]))
    return qc

rows, t0 = [], time.time()
for bname, basis in BASES.items():
    for lvl in LEVELS:
        for seed in SEEDS:
            cert = 0
            for r in PAIRS:
                m = MUT[r["mutant_id"]]; sub = m["subject"]; n = nq[sub]
                a = transpile(build(orig[sub], n), basis_gates=basis,
                              optimization_level=lvl, seed_transpiler=seed)
                b = transpile(build(m["gates"], n), basis_gates=basis,
                              optimization_level=lvl, seed_transpiler=seed)
                if qasm2.dumps(a) == qasm2.dumps(b): cert += 1
            rows.append({"basis": bname, "optimization_level": lvl, "seed": seed,
                         "pairs": len(PAIRS), "certified": cert,
                         "recall_pct": round(100 * cert / len(PAIRS), 1)})
            print(f"  {bname:12} O{lvl} seed={seed:<9} certified {cert:2}/{len(PAIRS)} "
                  f"= {100*cert/len(PAIRS):4.1f}%")

rec = [r["certified"] for r in rows]
print(f"\nrecall over {len(rows)} configurations: min {min(rec)}/{len(PAIRS)} "
      f"({100*min(rec)/len(PAIRS):.1f}%), max {max(rec)}/{len(PAIRS)} "
      f"({100*max(rec)/len(PAIRS):.1f}%)")
print(f"the paper's single configuration (rz_sx_x_cx, O3, seed 20260827): "
      f"{[r['certified'] for r in rows if r['basis']=='rz_sx_x_cx' and r['optimization_level']==3 and r['seed']==20260827][0]}")
print(f"elapsed {time.time()-t0:.0f}s")
with open(f"{OUT}/B5_A3_TRANSPILER_SWEEP.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump({"pairs": len(PAIRS), "configurations": len(rows),
           "certified_min": min(rec), "certified_max": max(rec),
           "recall_min_pct": round(100*min(rec)/len(PAIRS), 1),
           "recall_max_pct": round(100*max(rec)/len(PAIRS), 1)},
          open(f"{OUT}/B5_A3_SUMMARY.json", "w"), indent=1)
