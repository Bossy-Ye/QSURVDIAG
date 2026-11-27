"""Three gate-set procedures, and their depth counterparts, on the contract-equivalent mutants of the 20
circuits. Nothing is simulated or executed.

  HIST  the untranspiled gate lists differ; the depths of the source circuits differ
  P5    after transpilation to [rz, sx, x, cx] at optimization level 1, seed 20260730: the sets of gate names
        differ; the depths differ
  QT    QUTest 0.1.0's own structural assertions, evaluated without execution

Adapted from data/structural/records/structural_definitions.py. Run by scripts/reproduce_analytic.py; writes
STRUCTURAL_DEFINITIONS.csv and its summary to <out>/analytic/."""

import csv, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import archived, out_dir

OUT = out_dir("analytic")
FROZEN = "data/prospective/mqt_bench/frozen_deps/"
sys.path.insert(0, str(archived(FROZEN + "qutest_adapter.py").parent))
from qutest_adapter import make_test
from qutest.parser.qasm_parser import parse_test_source
from qutest.backends import resolve_backend
from qutest.assertions.structural import evaluate_gateset, evaluate_depth
import qiskit
from qiskit import QuantumCircuit, qasm3, transpile


def rd(path):
    with open(archived(path)) as f:
        return list(csv.DictReader(f))


def qt_transpiled(gates, n, extra=()):
    tc = parse_test_source(make_test(gates, n, list(extra)))[0]
    circ = qasm3.loads(tc.qasm_source)
    return tc, transpile(circ, backend=resolve_backend("ideal", 42))


def names(c):
    return sorted({i.operation.name for i in c.data} - {"measure", "barrier"})


def src(gates, n):
    c = QuantumCircuit(n)
    for x in gates:
        getattr(c, x["gate"])(*x.get("angles", []), *x["q"])
    return c


def p5(gates, n):
    return transpile(
        src(gates, n), basis_gates=["rz", "sx", "x", "cx"], optimization_level=1, seed_transpiler=20260730
    )


L = lambda gs: [(g["gate"], tuple(g["q"]), tuple(g.get("angles", []))) for g in gs]


def row(mid, pop, base, mut, n):
    _, tb = qt_transpiled(base, n)
    allowed = "[" + ", ".join(names(tb)) + "]"
    d0 = tb.depth()
    tc, tm = qt_transpiled(
        mut,
        n,
        [f"//% expect gateset subset_of {allowed}", f"//% expect depth <= {d0}", f"//% expect depth == {d0}"],
    )
    sp = tc.structural_pragmas
    gs, dle, deq = (
        (evaluate_gateset(sp[0], tm).status.value == "fail"),
        (evaluate_depth(sp[1], tm).status.value == "fail"),
        (evaluate_depth(sp[2], tm).status.value == "fail"),
    )
    b5, m5 = p5(base, n), p5(mut, n)
    bs, ms = src(base, n), src(mut, n)
    return {
        "mutant_id": mid,
        "population": pop,
        "HIST_gatelist": L(base) != L(mut),
        "HIST_depth": bs.depth() != ms.depth(),
        "P5_gateset": set(names(b5)) != set(names(m5)),
        "P5_depth": b5.depth() != m5.depth(),
        "QT_gateset_subset": gs,
        "QT_depth_le": dle,
        "QT_depth_eq": deq,
        "QT_allowed": allowed,
        "QT_depth_original": d0,
        "QT_depth_mutant": tm.depth(),
    }


rows = []
led = [
    r for r in rd("data/structural/CANONICAL_RESULT_LEDGER.csv") if r["final_semantic_status"] == "EQUIVALENT"
]
MP = {r["mutant_id"]: r for r in rd(FROZEN + "MUTANT_POPULATION.csv")}
PM = {r["program"]: r for r in rd(FROZEN + "PROGRAM_MANIFEST.csv")}
for r in led:
    m = MP[r["mutant_id"]]
    p = PM[m["program"]]
    rows.append(
        row(
            r["mutant_id"],
            "construction",
            json.loads(p["base_gates"]),
            json.loads(m["mutated_gates"]),
            int(p["n"]),
        )
    )
with open(archived(FROZEN + "S1_SUBJECTS.json")) as f:
    S1 = {s["subject"]: s for s in json.load(f)}
S2 = {r["mutant_id"]: r for r in rd(FROZEN + "S2_GENERATED_MUTANTS.csv")}
ADM = {r["mutant_id"]: r for r in rd("data/prospective/cross_tool/results/S3_QUTEST_ADMISSIBILITY.csv")}
for mid, a in ADM.items():
    if a["contract_equivalent"] != "True":
        continue
    s = S1[S2[mid]["subject"]]
    bg = s["base_gates"]
    bg = json.loads(bg) if isinstance(bg, str) else bg
    r_ = row(mid, "prospective", bg, json.loads(S2[mid]["mutated_gates"]), int(S2[mid]["n"]))
    r_["recorded_gateset"] = a["gateset_separates"] == "True"
    r_["recorded_depth"] = a["depth_separates"] == "True"
    rows.append(r_)
keys = [
    "HIST_gatelist",
    "HIST_depth",
    "P5_gateset",
    "P5_depth",
    "QT_gateset_subset",
    "QT_depth_le",
    "QT_depth_eq",
]
with open(OUT / "STRUCTURAL_DEFINITIONS.csv", "w", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=list(rows[0].keys()) + ["recorded_gateset", "recorded_depth"],
        extrasaction="ignore",
        restval="",
    )
    w.writeheader()
    w.writerows(rows)
S = {}
for pop in ("construction", "prospective"):
    P = [r for r in rows if r["population"] == pop]
    S[pop] = {"n": len(P), **{k: sum(r[k] for r in P) for k in keys}}
P = [r for r in rows if r["population"] == "prospective"]
S["prospective"]["P5_matches_recorded_gateset_per_case"] = all(
    r["P5_gateset"] == r["recorded_gateset"] for r in P
)
S["prospective"]["P5_matches_recorded_depth_per_case"] = all(r["P5_depth"] == r["recorded_depth"] for r in P)
S["versions"] = {"qiskit": qiskit.__version__, "qutest": "0.1.0", "python": sys.version.split()[0]}
with open(OUT / "STRUCTURAL_DEFINITIONS_SUMMARY.json", "w") as f:
    json.dump(S, f, indent=1)
print(json.dumps(S, indent=1))
