"""Rebuild the seven Qolumbina programs from the archive and compare with the frozen circuit hashes."""
import hashlib, importlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = Path(sys.argv[1])               # qolumbina-infrastructure-main of 10.5281/zenodo.20987327 (archive MD5 in OPERATIONAL.md)
sys.path.insert(0, str(SRC))
from qiskit.qasm3 import dumps as q3dumps
import qiskit
V1 = json.load(open(ROOT / "data/external/protocol/EXTERNAL_COHORT_FREEZE.json"))
MODS = {"ParityPhase": "qolumbina.programs.parity.parity_phase", "Is2PowerPhase": "qolumbina.programs.is_two_power.is_two_power_phase",
        "LessThanPhase": "qolumbina.programs.comparator.less_than_phase", "DiagonalZHamiltonian": "qolumbina.programs.hamiltonian.diagonal_hamiltonian",
        "IsingEvolution": "qolumbina.programs.ising.ising", "DraperAdder": "qolumbina.programs.quantum_adder.draper_adder",
        "AdderHamiltonianMixture": "qolumbina.programs.hamiltonian.adder_hamiltonian_mixture"}
print("qiskit", qiskit.__version__)
ok = True
for s in V1["subjects"]:
    if s["group"] != "MgcosA": continue
    qc = getattr(importlib.import_module(MODS[s["subject"]]), s["subject"])(**s["parameters"])
    h = hashlib.sha256(q3dumps(qc).encode()).hexdigest()
    print(s["subject"], h == s["circuit_sha256"], h[:16], s["circuit_sha256"][:16]); ok &= h == s["circuit_sha256"]
print("ALL MATCH" if ok else "MISMATCH")
