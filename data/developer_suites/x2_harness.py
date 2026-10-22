"""X2 harness: one execution of suite A (MITRE unit tests) or suite B (QuCheck properties) on one program version.

The source repository (QuCheck case studies, commit 74c27570) is put first on sys.path so that its own `qucheck`
package and `case_studies` are used. A program version is the original function or a mutant file, substituted with
unittest.mock.patch as in the source's runners. Per run, Python's random, NumPy's global generator, QuCheck's
random_seed and every Aer simulation are seeded with the run seed.
"""
import importlib, importlib.util, io, os, random, sys, time, contextlib
from pathlib import Path
from unittest.mock import patch

SRC = Path(os.environ["X2_SRC"])                # checkout of the QuCheck repository at commit 74c27570
CS = SRC / "case_studies"
MITRE = CS / "MITRE_unit_test_baseline"
SUITE_A = {  # program folder -> (module, test class, test methods, takes the runner's shot value)
    "deutsch_jozsa": ("deutsch_jozsa", "DeutschJozsa", ["test_constant_one", "test_constant_zero", "test_nth_qubit_parity", "test_odd_number_of_ones"], None),
    "grovers_algorithm": ("grover_tests", "GroverTests", ["test_5_bits", "test_10_bits", "test_12_bits"], None),
    "quantum_fourier_transform": ("qft_tests", "QftTests", ["test_period_6", "test_sine", "test_1hz_sine_8_samples", "test_1hz_cosine_8_samples", "test_2hz_sine_8_samples", "test_2hz_cosine_8_samples"], None),
    "quantum_teleportation": ("teleportation", "TeleportationTests", ["test_minus", "test_one", "test_plus", "test_zero", "test_i_minus", "test_i_plus", "test_weird_rotation"], 100),
}
PROGRAMS = ["deutsch_jozsa", "grovers_algorithm", "quantum_fourier_transform", "quantum_phase_estimation",
            "quantum_teleportation", "superdense_coding"]


def _paths():
    for p in (str(MITRE), str(SRC)):
        if p in sys.path: sys.path.remove(p)
        sys.path.insert(0, p)


def _seed_all(seed):
    import numpy as np
    from qiskit_aer.backends.aerbackend import AerBackend
    random.seed(seed); np.random.seed(seed)
    run0 = AerBackend.run; calls = [0]
    def run(self, *a, **k):                      # one deterministic seed per simulation call
        k.setdefault("seed_simulator", seed * 1000003 + calls[0]); calls[0] += 1
        return run0(self, *a, **k)
    AerBackend.run = run


def load_version(program, version):
    """version: 'original' or a mutant stem such as 'm3' / 'em0'."""
    if version == "original":
        mod = importlib.import_module(f"case_studies.{program}.{program}")
        return getattr(mod, program)
    name = f"{program}_{version}"; path = CS / program / "mutants" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod; spec.loader.exec_module(mod)
    return getattr(mod, program)


def _reload_folder(folder):
    sys.path.insert(0, str(folder))
    for f in sorted(os.listdir(folder)):
        if f.endswith(".py"):
            m = importlib.import_module(f[:-3]); importlib.reload(m)
    sys.path.pop(0)


def run_suite_a(program, version, seed):
    _paths(); _seed_all(seed)
    modname, cls, methods, shots = SUITE_A[program]
    fn = load_version(program, version)
    mod = importlib.import_module(modname)
    t0 = time.time(); res = {}
    with patch.object(mod, program, fn), contextlib.redirect_stdout(io.StringIO()):
        for m in methods:
            obj = getattr(mod, cls)()
            try:
                ok = getattr(obj, m)(shots) if shots else getattr(obj, m)()
                res[m] = bool(ok)
            except Exception as e:
                res[m] = f"error:{type(e).__name__}"
            if res[m] is not True:                # the suite has failed: its verdict is decided (OPERATIONAL.md, X2_EQUALITY_METHOD)
                break
    passed = len(res) == len(methods) and all(v is True for v in res.values())
    return {"suite": "A", "program": program, "version": version, "seed": seed, "passed": passed, "tests": res,
            "seconds": round(time.time() - t0, 3)}


def _ordered_optimizer():
    """Submission order of QuCheck's merged circuits: insertion order instead of a hash-ordered set
    (OPERATIONAL.md, X2_OPERATIONAL_ADDENDUM). Merging and circuits are unchanged."""
    from qucheck.stats.circuit_generator import CircuitGenerator
    def _optimize(self):
        for unique_circuit in list(self.unoptimized_measurement_info.keys()):
            self._get_full_circuits(unique_circuit)
        return list(self.measurement_info_for_unique_circuits.keys())
    CircuitGenerator._optimize = _optimize


def run_suite_b(program, version, seed, num_inputs, measurements, run_optimization=True):
    _paths(); _seed_all(seed); _ordered_optimizer()
    from qiskit_aer import AerSimulator
    from qucheck.coordinator import Coordinator
    fn = load_version(program, version)
    t0 = time.time()
    with patch(f"case_studies.{program}.{program}.{program}", fn), contextlib.redirect_stdout(io.StringIO()):
        _reload_folder(CS / program)
        backend = AerSimulator(method="statevector", seed_simulator=seed)
        backend.set_options(max_parallel_threads=1, max_parallel_experiments=1, max_parallel_shots=1)
        co = Coordinator(num_inputs, random_seed=seed, backend=backend)
        r = co.test(str(CS / program), measurements, run_optimization=run_optimization, number_of_properties=-1)
    failed = sorted({type(p).__name__ if not isinstance(p, type) else p.__name__ for p in r.failed_property})
    seeds = {f"{k}": [list(s) for s in v] for k, v in co.test_runner.seeds_list_dict.items()}
    return {"suite": "B", "program": program, "version": version, "seed": seed, "passed": not failed,
            "failed_properties": failed, "circuits": r.number_circuits_executed, "input_seeds": seeds,
            "seconds": round(time.time() - t0, 3)}
