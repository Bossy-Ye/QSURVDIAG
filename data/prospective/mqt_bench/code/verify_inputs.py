"""Final original-only verification (Pass 3B, before Freeze A). No mutant.

For each multiplier: the coherent output on the DECLARED executed input
(|x_a> + |x_b>)/sqrt2 -- complex amplitudes, relative phase, output encoding -- for
(1) the MQT circuit before conversion, (2) the converted gate list, (3) the converted gate
list after the frozen QUTest rewriting (adapt). Correctness is claimed for this declared input
and for the basis inputs checked in Stage A only, not for untested input states.
For each quantum walk: the Stage-A independent coined-walk check, repeated on the frozen
converted gate list and its adapted form.
Writes subjects/VERIFY_INPUTS.json.
"""
import json, os, sys, ast
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from mqt.bench.benchmarks import qwalk, rg_qft_multiplier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = os.path.join(ROOT, "frozen_deps")
sys.path.insert(0, FD)
from qutest_execution_adapter import adapt          # frozen copy (byte-identical to live; deps.py)

def build(gl, n):
    qc = QuantumCircuit(n)
    for g in gl: getattr(qc, g["gate"])(*g.get("angles", []), *g["q"])
    return qc

def walk_ref(m, steps):
    """Independent coined walk on Z_{2^m}: H coin, coin=1 -> +1, coin=0 -> -1 (Aharonov et al. 1993)."""
    psi = np.zeros((2, 2 ** m), complex); psi[0, 0] = 1
    H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    for _ in range(steps):
        psi = H @ psi; new = np.zeros_like(psi)
        new[1] = np.roll(psi[1], 1); new[0] = np.roll(psi[0], -1); psi = new
    return psi

def main():
    S = json.load(open(os.path.join(ROOT, "subjects", "SUBJECTS.json"))); res = {}
    for s in S:
        n = s["n"]; body, prep = s["body"], s["prep"]
        forms = {"converted": body, "converted_adapted": adapt(body)}
        if s["family"] == "quantum_walk":
            m = n - 1; ref = walk_ref(m, 3); vec = np.zeros(2 ** n, complex)
            for c in (0, 1):
                for x in range(2 ** m):
                    vec[(c << m) | int(format(x, f"0{m}b")[::-1], 2)] = ref[c, x]   # node register MSB-first
            r = {}
            mqt = qwalk.create_circuit(n).remove_final_measurements(inplace=False)
            r["mqt_overlap"] = float(abs(np.vdot(vec, Statevector(mqt).data)))
            for k, gl in forms.items():
                r[f"{k}_overlap"] = float(abs(np.vdot(vec, Statevector(build(gl, n)).data)))
            r["pass"] = all(abs(v - 1) < 1e-9 for k, v in r.items() if k.endswith("overlap"))
            res[s["subject"]] = r
        else:
            k = n // 4; xa, xb = s["x_a"], s["x_b"]
            a1, b1 = xa & (2 ** k - 1), (xa >> k) & (2 ** k - 1)
            a2, b2 = xb & (2 ** k - 1), (xb >> k) & (2 ** k - 1)
            ea = xa | ((a1 * b1) << (2 * k)); eb = xb | ((a2 * b2) << (2 * k))
            r = {"declared_input": s["declared_input"], "expected_outputs": [ea, eb],
                 "expected_amplitudes": "1/sqrt2 each, relative phase 0"}
            mqt = rg_qft_multiplier.create_circuit(n).remove_final_measurements(inplace=False)
            cands = {"mqt": build(prep, n).compose(mqt), **{kk: build(prep + gl, n) for kk, gl in forms.items()}}
            ok = True
            for kk, qc in cands.items():
                v = Statevector(qc).data
                amp_a, amp_b = v[ea], v[eb]
                other = float(np.sum(np.abs(v) ** 2) - abs(amp_a) ** 2 - abs(amp_b) ** 2)
                rel = float(np.angle(amp_b / amp_a)) if abs(amp_a) > 0 else None
                r[kk] = {"abs_a": float(abs(amp_a)), "abs_b": float(abs(amp_b)),
                         "relative_phase_rad": rel, "weight_outside_expected": other}
                ok &= (abs(abs(amp_a) - 2 ** -0.5) < 1e-9 and abs(abs(amp_b) - 2 ** -0.5) < 1e-9
                       and other < 1e-12 and rel is not None and abs(rel) < 1e-9)
            # the converted program on the declared input equals the MQT program on it, up to global phase
            vm = Statevector(cands["mqt"]).data
            r["converted_vs_mqt_overlap"] = float(abs(np.vdot(vm, Statevector(cands["converted"]).data)))
            r["adapted_vs_mqt_overlap"] = float(abs(np.vdot(vm, Statevector(cands["converted_adapted"]).data)))
            ok &= abs(r["converted_vs_mqt_overlap"] - 1) < 1e-9 and abs(r["adapted_vs_mqt_overlap"] - 1) < 1e-9
            r["pass"] = bool(ok); res[s["subject"]] = r
        print(s["subject"], res[s["subject"]]["pass"], flush=True)
    json.dump(res, open(os.path.join(ROOT, "subjects", "VERIFY_INPUTS.json"), "w"), indent=1)
    if not all(r["pass"] for r in res.values()):
        raise SystemExit("ESSENTIAL ORIGINAL-PROGRAM CHECK FAILED -- stop and report; no substitution")

if __name__ == "__main__":
    main()
