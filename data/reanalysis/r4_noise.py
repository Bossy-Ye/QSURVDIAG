"""R4: the 115 survivors of the 20 circuits whose final state differs, compared under device noise.

Noise: the median calibrated errors of the IBM Torino snapshot in qiskit-ibm-runtime 0.40.1 (FakeTorino):
depolarizing error on sx and x, depolarizing error on cz, symmetric readout error; rz is virtual. Each circuit is
transpiled to {rz, sx, x, cz} on a line of n qubits (optimization level 1, seed 42) and simulated as a density
matrix; distributions are exact, with the readout error applied per measured bit. The declared QUTest universe is
then evaluated on the noisy distributions of original and mutant, with the noisy original as reference.
"""
import collections, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_ibm_runtime.fake_provider import FakeTorino
import counts as C

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "reanalysis"; OUT.mkdir(parents=True, exist_ok=True)
orig, nq, outreg, mut = C.load_population()
fin = C.final_reports()

be = FakeTorino(); tg = be.target
med = lambda op: float(np.median([p.error for p in tg[op].values() if p is not None and p.error is not None]))
E1, E2, ER = med("sx"), med("cz"), med("measure")
nm = NoiseModel(basis_gates=["rz", "sx", "x", "cz"])
nm.add_all_qubit_quantum_error(depolarizing_error(E1 * 3 / 2, 1), ["sx", "x"])    # average gate infidelity -> depolarizing
nm.add_all_qubit_quantum_error(depolarizing_error(E2 * 5 / 4, 2), ["cz"])
SIM = AerSimulator(method="density_matrix", noise_model=nm); SIM.set_options(max_parallel_threads=1)
RO = np.array([[1 - ER, ER], [ER, 1 - ER]])


def circuit(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", []); q = [int(x) for x in g["q"]]
        getattr(qc, g["gate"])(*a, *q) if a else getattr(qc, g["gate"])(*q)
    return qc


def noisy(gates, n):
    qc = circuit(gates, n); qc.measure_all()
    t = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], coupling_map=CouplingMap.from_line(n), optimization_level=1, seed_transpiler=42)
    phys = {t.find_bit(ci.clbits[0]).index: t.find_bit(ci.qubits[0]).index for ci in t.data if ci.operation.name == "measure"}
    t.remove_final_measurements(inplace=True)
    qs = [phys[c] for c in range(n)]            # clbit c holds logical qubit c
    t.save_probabilities(qs)
    p = np.asarray(SIM.run(t).result().data()["probabilities"])
    p = p.reshape([2] * n)                       # readout error on every measured bit
    for ax in range(n):
        p = np.moveaxis(np.tensordot(RO, np.moveaxis(p, ax, 0), axes=([1], [0])), 0, ax)
    return p.reshape(-1), t.count_ops().get("cz", 0)


rows = []
for k, r in sorted(fin.items()):
    if r["v2_report"] not in ("CL3", "CL4", "CL5"):
        continue
    m = mut[k]; p = m["subject"]; n = nq[p]
    po, czo = noisy(orig[p], n); pm, czm = noisy(m["gates"], n)
    ideal_o, ideal_m = np.abs(C.sv(orig[p], n)) ** 2, np.abs(C.sv(m["gates"], n)) ** 2
    wi = C.first_witness(ideal_o, ideal_m, n)
    u = {(x[0], x[1]): x[2] for x in C.universe(po, pm, n)}
    best = max(C.universe(po, pm, n), key=lambda x: x[2])
    rows.append({"pair": k, "program": p, "n": n, "report": r["v2_report"], "cz_original": czo, "cz_mutant": czm,
                 "noisy_max_kind": best[0], "noisy_max_key": best[1], "noisy_max_d": best[2],
                 "ideal_witness": None if wi is None else [wi[0], wi[1], wi[2]],
                 "witness_noisy_d": None if wi is None else u[(wi[0], wi[1])],
                 "noisy_first_witness": (lambda w: None if w is None else [w[0], w[1], w[2]])(C.first_witness(po, pm, n))})
    print(k, r["v2_report"], round(best[2], 4), None if wi is None else round(u[(wi[0], wi[1])], 4), flush=True)

g = lambda o: [x for x in rows if x["report"] == o]
summ = {"noise": {"backend": be.name, "sx_x_error": E1, "cz_error": E2, "readout_error": ER},
        "observation_limitations": {"pairs": len(g("CL3")), "separated_under_noise": sum(x["noisy_first_witness"] is not None for x in g("CL3")),
                                    "largest_noisy_difference": max(x["noisy_max_d"] for x in g("CL3"))},
        "suite_omissions": {"pairs": len(g("CL4")), "witness_still_above_theta": sum(x["witness_noisy_d"] > C.THETA + C.RES for x in g("CL4")),
                            "some_instance_above_theta": sum(x["noisy_first_witness"] is not None for x in g("CL4")),
                            "witness_ratio_median": float(np.median([x["witness_noisy_d"] / x["ideal_witness"][2] for x in g("CL4")]))},
        "below_tolerance": {"pairs": len(g("CL5")), "separated_under_noise": sum(x["noisy_first_witness"] is not None for x in g("CL5"))}}
json.dump({"summary": summ, "pairs": rows}, open(OUT / "R4_NOISE.json", "w"), indent=1, default=lambda o: o.item())
print(json.dumps(summ, indent=1, default=lambda o: o.item()))
