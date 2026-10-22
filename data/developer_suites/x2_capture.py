"""Capture (OPERATIONAL.md, X2_OPERATIONAL): one suite run with the program calls and every submitted circuit recorded.

The simulator still samples as usual, so the verdict of the run is native; the wrapper only records each submitted
circuit and computes its exact distribution of measured bits.
"""
import copy, hashlib, os, pickle, sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import x2_harness as H

EPS = 1e-9
from qiskit_aer.backends.aerbackend import AerBackend as _AB
_RAW_RUN = _AB.run          # unpatched; exact probabilities of wide contexts are computed through it


_SIM = []


def _sv_sim():
    from qiskit_aer import AerSimulator
    if not _SIM:
        _SIM.append(AerSimulator(method="statevector", precision="double")); _SIM[0].set_options(max_parallel_threads=1)
    return _SIM[0]


XCACHE = Path(os.environ.get("QSD_OUT", Path(__file__).resolve().parents[2] / "output")) / "developer_suites" / "xcache"


def _ckey(qc):
    """Content key of a circuit at full precision: identical circuits, identical key."""
    h = hashlib.sha256(f"{qc.num_qubits};{qc.num_clbits}".encode())
    for ci in qc.data:
        ps = [hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() if isinstance(v, np.ndarray) else repr(v) for v in ci.operation.params]
        h.update(f"|{ci.operation.name}{ps}{[qc.find_bit(q).index for q in ci.qubits]}{[qc.find_bit(c).index for c in ci.clbits]}".encode())
    return h.hexdigest()


def _cached(kind, qc, compute):
    """Results for circuits wider than 14 qubits are stored by content and reused (OPERATIONAL.md, X2_EQUALITY_METHOD)."""
    if qc.num_qubits <= 14:
        return compute(qc)
    f = XCACHE / kind / (_ckey(qc) + ".pkl")
    if f.exists():
        return pickle.load(open(f, "rb"))
    r = compute(qc)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f".{os.getpid()}.tmp"); pickle.dump(r, open(tmp, "wb")); os.replace(tmp, f)
    return r


def _exact(qc):
    return _cached("exact", qc, _exact_compute)


def _exact_compute(qc):
    """Exact distribution of the measured bits (OPERATIONAL.md, X2_EXACT_METHOD): Aer statevector, outside the seeded path."""
    from qiskit import QuantumCircuit, transpile
    meas = sorted([(qc.find_bit(ci.qubits[0]).index, qc.find_bit(ci.clbits[0]).index) for ci in qc.data if ci.operation.name == "measure"], key=lambda t: t[1])
    qs = [q for q, _ in meas]
    body = QuantumCircuit(qc.num_qubits)
    for ci in qc.data:
        if ci.operation.name in ("measure", "barrier"): continue
        body.append(ci.operation, [body.qubits[qc.find_bit(q).index] for q in ci.qubits])
    b = transpile(body, _sv_sim(), optimization_level=0); b.save_probabilities(qs)
    return {"width": qc.num_qubits, "measured": qs, "dist": np.asarray(_RAW_RUN(_sv_sim(), b).result().data()["probabilities"])}


def _sig(x):
    from qiskit import QuantumCircuit
    if isinstance(x, QuantumCircuit):
        return "QC(" + str(x.num_qubits) + ";" + ";".join(f"{ci.operation.name}{[round(float(v), 12) if isinstance(v, (int, float, np.floating)) else str(v) for v in ci.operation.params]}{[x.find_bit(q).index for q in ci.qubits]}" for ci in x.data) + ")"
    if isinstance(x, (list, tuple)): return "[" + ",".join(_sig(y) for y in x) + "]"
    if isinstance(x, np.ndarray): return "A" + str(np.round(x, 12).tolist())
    return repr(x)


def _prep(qc):
    """initialize at the start acts on |0...0>: replace it by the equivalent StatePreparation."""
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import StatePreparation
    if not any(ci.operation.name == "initialize" for ci in qc.data): return qc
    out = QuantumCircuit(qc.num_qubits)
    for ci in qc.data:
        op = StatePreparation(ci.operation.params) if ci.operation.name == "initialize" else ci.operation
        out.append(op, [out.qubits[qc.find_bit(q).index] for q in ci.qubits])
    return out


_USIM = []


def _unitary(qc):
    """Exact unitary with Aer's unitary method (OPERATIONAL.md, X2_EXACT_METHOD); None when the method does not apply."""
    if qc.num_qubits > 12 or any(ci.operation.name in ("state_preparation", "initialize", "reset", "measure") for ci in qc.data):
        return None
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    if not _USIM:
        _USIM.append(AerSimulator(method="unitary", precision="double")); _USIM[0].set_options(max_parallel_threads=1)
    try:
        b = transpile(qc, _USIM[0], optimization_level=0); b.save_unitary()
        return np.asarray(_RAW_RUN(_USIM[0], b).result().data()["unitary"])
    except Exception:
        return None


def _state(qc):
    """Final state from |0...0> with Aer's statevector method; None when the method does not apply."""
    if any(ci.operation.name in ("state_preparation", "initialize", "reset", "measure") for ci in qc.data):
        return None
    from qiskit import transpile
    try:
        b = transpile(qc, _sv_sim(), optimization_level=0); b.save_statevector()
        return np.asarray(_RAW_RUN(_sv_sim(), b).result().data()["statevector"])
    except Exception:
        return None


def program_equal(fp, fm, args, kwargs):
    from qiskit.quantum_info import Operator, Statevector
    a1, k1 = copy.deepcopy(args), copy.deepcopy(kwargs); a2, k2 = copy.deepcopy(args), copy.deepcopy(kwargs)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        cp, cm = fp(*a1, **k1), fm(*a2, **k2)
    cp = _prep(cp.remove_final_measurements(inplace=False)); cm = _prep(cm.remove_final_measurements(inplace=False))
    if cp.num_qubits != cm.num_qubits: return False
    if cp.num_qubits > 14:                     # the operator does not fit in memory: final states from |0...0>
        sp, sm = _cached("state", cp, _state), _state(cm)      # the original's state is shared by every mutant
        if sp is not None and sm is not None:
            return bool(Statevector(sp).equiv(Statevector(sm), atol=1e-9))
    up, um = _unitary(cp), _unitary(cm)
    if up is not None and um is not None:
        return bool(Operator(up).equiv(Operator(um), atol=1e-9))
    try:
        return bool(Operator(cp).equiv(Operator(cm), atol=1e-9))
    except Exception:
        return bool(Statevector(cp).equiv(Statevector(cm), atol=1e-9))


def run_capture(suite, program, version, seed, num_inputs=100, measurements=2500):
    """Returns (record of the run, contexts, calls). calls: list of (signature, args, kwargs)."""
    from qiskit_aer.backends.aerbackend import AerBackend as AerSimulator
    contexts, calls = [], []
    run0 = AerSimulator.run
    def run(self, circuits, *a, **k):
        cs = circuits if isinstance(circuits, (list, tuple)) else [circuits]
        for c in cs: contexts.append(_exact(c))
        return run0(self, circuits, *a, **k)
    H._paths()
    fn = H.load_version(program, version)
    def wrapped(*a, **k):
        calls.append((_sig((a, sorted(k.items()))), copy.deepcopy(a), copy.deepcopy(k)))
        return fn(*a, **k)
    orig_load = H.load_version
    with patch.object(AerSimulator, "run", run), patch.object(H, "load_version", lambda p, v: wrapped):
        rec = H.run_suite_a(program, version, seed) if suite == "A" else H.run_suite_b(program, version, seed, num_inputs, measurements)
    H.load_version = orig_load
    return rec, contexts, calls
