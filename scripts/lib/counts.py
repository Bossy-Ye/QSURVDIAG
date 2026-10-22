"""Count-profile helpers shared by the observation-change, position and re-analysis experiments.

Gate lists of the 20 circuits and their mutants, statevectors, measurement-basis rotations, the
2^(n+1)+n+3 instances of the declared QUTest universe in the closed witness order, and QUTest test files run
through the qutest CLI (analytic environment of environment/setup.sh; override with $QUTEST).
"""
import sys as _s; _s.dont_write_bytecode = True
import ast, csv, itertools, json, os, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT
FROZEN = ROOT / "data/prospective/mqt_bench/frozen_deps"
OUTC = ROOT / "data/certification/outcomes"
QUTEST = os.environ.get("QUTEST", str(Path(sys.executable).parent / "qutest"))
THETA, RES = 0.05, 5e-9
os.environ.setdefault("QISKIT_SETTINGS", str(ROOT / "environment/qiskit_settings.conf"))

sys.path.insert(0, str(FROZEN))
from qutest_execution_adapter import adapt          # noqa: E402  (rzz/rxx lowering of the study)
from serialization_adapter import emit_name         # noqa: E402  (u -> u3)
from qiskit import QuantumCircuit                   # noqa: E402
from qiskit.quantum_info import Statevector         # noqa: E402


def _gl(s):
    if isinstance(s, list): return s
    try: return json.loads(s)
    except Exception: return ast.literal_eval(s)


def load_population():
    orig, nq, outreg = {}, {}, {}
    for r in csv.DictReader(open(FROZEN / "PROGRAM_MANIFEST.csv")):
        orig[r["program"]] = _gl(r["base_gates"]); nq[r["program"]] = int(r["n"])
        outreg[r["program"]] = _gl(r["output_register_qubits"])
    for s in json.load(open(FROZEN / "S1_SUBJECTS.json")):
        orig[s["subject"]] = _gl(s["base_gates"]); nq[s["subject"]] = int(s["n"])
        outreg[s["subject"]] = _gl(s["output_register_qubits"])
    mut = {}
    for r in csv.DictReader(open(FROZEN / "MUTANT_POPULATION.csv")):
        mut[r["mutant_id"]] = {"subject": r["program"], "gates": _gl(r["mutated_gates"]), "location": r["location"],
                               "operator": r["operator"]}
    for r in csv.DictReader(open(FROZEN / "S2_GENERATED_MUTANTS.csv")):
        g = r.get("mutated_gates")
        if g: mut[r["mutant_id"]] = {"subject": r["subject"], "gates": _gl(g), "location": r["location"],
                                     "operator": r["operator"]}
    return orig, nq, outreg, mut


def final_reports():
    return {x["case_key"]: x for x in csv.DictReader(open(OUTC / "R2V_FINAL_PRIMARY.csv"))}


def sv(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", []); q = [int(x) for x in g["q"]]
        getattr(qc, g["gate"])(*a, *q) if a else getattr(qc, g["gate"])(*q)
    return np.asarray(Statevector.from_int(0, dims=(2,) * n).evolve(qc).data)


H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
SDG = np.diag([1, -1j])
ROT = {"Z": np.eye(2), "X": H, "Y": H @ SDG}          # Y basis: sdg then h
ROT_GATES = {"Z": [], "X": ["h"], "Y": ["sdg", "h"]}


def rotate(psi, n, setting):
    """setting[q] in 'XYZ' for qubit q (little-endian, as Qiskit)."""
    t = psi.reshape((2,) * n)            # axis k = qubit n-1-k
    for q, b in enumerate(setting):
        if b == "Z": continue
        ax = n - 1 - q
        t = np.moveaxis(np.tensordot(ROT[b], t, axes=([1], [ax])), 0, ax)
    return t.reshape(-1)


def _walsh(p):
    """All Z-product expectations <Z^mask> for mask in 0..2^n-1."""
    w = p.astype(float).copy(); h = 1
    while h < len(w):
        for i in range(0, len(w), 2 * h):
            a = w[i:i + h].copy(); b = w[i + h:i + 2 * h].copy(); w[i:i + h] = a + b; w[i + h:i + 2 * h] = a - b
        h *= 2
    return w


def universe(pp, pm, n):
    """Every instance of the count universe U(P): list of (kind, key, d, ref)."""
    out = []; idx = np.arange(len(pp))
    for q in range(n):
        a = pp[((idx >> q) & 1) == 1].sum(); b = pm[((idx >> q) & 1) == 1].sum()
        out.append(("marginal", q, abs(a - b), a))
    wp, wm = _walsh(pp), _walsh(pm)
    for m in range(1, 2 ** n):
        out.append(("zmask", m, abs(wp[m] - wm[m]), wp[m]))
    dp = np.abs(pp - pm)
    for x in range(2 ** n): out.append(("prob", x, dp[x], pp[x]))
    def H_(p): q = p[p > 1e-300]; return float(-(q * np.log2(q)).sum())
    out.append(("entropy", None, abs(H_(pp) - H_(pm)), H_(pp)))
    out.append(("tvd", None, 0.5 * dp.sum(), None))
    out.append(("hellinger", None, float(np.sqrt(0.5 * np.sum((np.sqrt(pm) - np.sqrt(pp)) ** 2))), None))
    a, b = np.clip(pm, 1e-12, None), np.clip(pp, 1e-12, None)
    out.append(("kl", None, float(np.sum(a * np.log(a / b))), None))
    return out


def best_instance(pp, pm, n, kinds=None):
    u = [x for x in universe(pp, pm, n) if kinds is None or x[0] in kinds]
    return max(u, key=lambda x: x[2])


def separates(d): return d > THETA + RES


# ------------------------------------------------------------------ QUTest test files
def gate_line(g):
    a = ("(" + ",".join(f"{x}" for x in g.get("angles", [])) + ")") if g.get("angles") else ""
    return f"{g['gate']}{a} " + ", ".join(f"q[{i}]" for i in g["q"]) + ";"


def lowered(gates):
    return [{**x, "gate": emit_name(x["gate"])} for x in adapt(gates)]


def rotation_lines(setting):
    L = []
    for q, b in enumerate(setting):
        for gname in ROT_GATES[b]: L.append(f"{gname} q[{q}];")
    return L


def pragma_lines(kind, key, n, ref, pp=None, atol=THETA):
    if kind == "marginal": return [f"//% expect marginal m[{key}] p1 ~= {round(ref, 4)} atol={atol}"]
    if kind == "zmask":
        zs = " ".join(f"Z{i}" for i in range(n) if (key >> i) & 1)
        return [f'//% expect observable "{zs}" ~= {round(ref, 4)} atol={atol}']
    if kind == "prob": return [f'//% expect probability "{format(key, "0%db" % n)}" ~= {round(ref, 4)} atol={atol}']
    if kind == "entropy": return [f"//% expect entropy ~= {round(ref, 4)} atol={atol}"]
    ref = {format(x, "0%db" % n): float(pp[x]) for x in range(2 ** n) if pp[x] > 1e-15}
    metric = {"tvd": "total_variation_distance", "hellinger": "hellinger", "kl": "kl"}[kind]
    return ["//% expect distribution ref " + json.dumps(ref, separators=(",", ":")),
            f"//% expect distribution {metric} <= {THETA}"]


def wrapped_test(prog_gates, n, assertions, shots, seed, setting=None, name="test_rotated"):
    """Program as an unmodified helper subroutine; the test applies the basis rotation, then measures."""
    body = "\n".join("    " + gate_line(g) for g in lowered(prog_gates))
    rot = rotation_lines(setting) if setting else []
    return "\n".join(["OPENQASM 3;", 'include "stdgates.inc";', "",
                      f"def program(qubit[{n}] q) {{", body, "}", "",
                      f"def {name}() {{", f"    //% shots {shots}", f"    //% seed {seed}", "    //% backend ideal",
                      f"    qubit[{n}] q;", f"    bit[{n}] m;", "    program(q);"]
                     + ["    " + l for l in rot] + ["    m = measure q;"] + ["    " + a for a in assertions] + ["}", ""])


def run_qutest(text, keep=None):
    with tempfile.NamedTemporaryFile("w", suffix=".qasm", delete=False) as f:
        f.write(text); p = f.name
    try:
        t0 = time.perf_counter()
        r = subprocess.run([QUTEST, "run", "-v", p], capture_output=True, text=True, timeout=900)
        dt = time.perf_counter() - t0
        out = (r.stdout + r.stderr).strip(); summ = out.splitlines()[-1] if out else ""
        v = "UNSUPPORTED" if "error" in summ else ("KILLED" if "failed" in summ else ("SURVIVED" if "passed" in summ else "UNSUPPORTED"))
        if keep: Path(keep).write_text(text)
        return v, dt, out
    finally:
        Path(p).unlink(missing_ok=True)


def ordered(pp, pm, n):
    """Universe in the study's closed witness order (v3): marginals, adjacent-first pairs, weight>=3 products,
    basis-state probabilities, entropy, TVD, Hellinger, KL, then single-qubit Z products."""
    u = universe(pp, pm, n); by = {(k, key): (k, key, d, r) for k, key, d, r in u}
    o = [by[("marginal", q)] for q in range(n)]
    pairs = sorted(((i, j) for i in range(n) for j in range(i + 1, n)), key=lambda t: (t[1] - t[0], t[0], t[1]))
    o += [by[("zmask", (1 << i) | (1 << j))] for i, j in pairs]
    o += [by[("zmask", m)] for m in sorted((m for m in range(1, 2 ** n) if bin(m).count("1") >= 3), key=lambda m: (bin(m).count("1"), m))]
    o += [by[("prob", x)] for x in range(2 ** n)]
    o += [by[(k, None)] for k in ("entropy", "tvd", "hellinger", "kl")]
    o += [by[("zmask", 1 << q)] for q in range(n)]
    return o


def first_witness(pp, pm, n):
    return next((x for x in ordered(pp, pm, n) if separates(x[2])), None)
