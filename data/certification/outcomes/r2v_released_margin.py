"""The released-Qiskit CL3 case (issue 16164) in the margins of Section III-C.

The recorded run (github/results/defects/B3_RELEASED_CL3_FRESH.json) reports a density-matrix gap
and the worst amplitude difference. This script rebuilds the two programs of that record on its
realized input, the uniform superposition: the reference circuit swap(0,1) crz(1.0,0,1) swap(0,1)
and the defective one, from which CommutativeInverseCancellation removed both SWAP gates. It
computes the state margin | |<psi_P|psi_M>| - 1 | and the observation margin max |p_P - p_M| that
Section III-C decides on, after checking that the recomputation reproduces both recorded values.
Writes R2V_RELEASED_CL3.json.
"""
import json, os, sys
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, DensityMatrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V

def main():
    assert V.spec_unchanged()
    rec = json.load(open(V.PA + "github/results/defects/B3_RELEASED_CL3_FRESH.json"))["environments"]["E5_ENV_Q241_reported_release"]
    assert rec["transpiled_ops"] == {"crz": 1} and rec["reference_ops"] == {"swap": 2, "crz": 1}
    ref = QuantumCircuit(2); ref.h(0); ref.h(1); ref.swap(0, 1); ref.crz(1.0, 0, 1); ref.swap(0, 1)
    bad = QuantumCircuit(2); bad.h(0); bad.h(1); bad.crz(1.0, 0, 1)
    a, b = np.asarray(Statevector.from_instruction(ref).data), np.asarray(Statevector.from_instruction(bad).data)
    dm = float(np.max(np.abs(np.asarray(DensityMatrix(Statevector(a)).data) - np.asarray(DensityMatrix(Statevector(b)).data))))
    amp = float(np.max(np.abs(a - b)))
    plus = rec["inputs"]["plus"]
    assert abs(dm - plus["density_matrix_gap"]) < 1e-12 and abs(amp - plus["worst_amplitude_difference"]) < 1e-12
    out = {"state_margin": abs(abs(np.vdot(a, b)) - 1.0), "obs_margin": float(np.max(np.abs(np.abs(a) ** 2 - np.abs(b) ** 2))),
           "density_matrix_gap": dm, "worst_amplitude_difference": amp,
           "state_decision": V.tri_s(V.eq_decision(abs(abs(np.vdot(a, b)) - 1.0))),
           "obs_decision": V.tri_s(V.eq_decision(float(np.max(np.abs(np.abs(a) ** 2 - np.abs(b) ** 2)))))}
    json.dump(out, open(os.path.join(V.HERE, "R2V_RELEASED_CL3.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
