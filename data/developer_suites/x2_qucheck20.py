"""PLAN.md, section 5: native QuCheck 0.0.2 (audited release) on pairs of the 20 circuits.

Pairs: the 28 pairs that only the declared QuCheck profile distinguishes, the 25 that only the declared QUTest profile
distinguishes (R2V_TABLE_X_DECISIONS.csv, part interface) and the 21 evaluable transfer cases
(B5_A4B_REPAIR_TRANSFER.csv). Per pair, a Property calls assert_equal over every qubit in bases x, y, z
(2,000 measurements, alpha 0.05, run_optimization False). 12 runs at seeds 15542-15553; the control compares the
original with a copy carrying a trailing barrier, 12 runs at seeds 16542-16553. QuCheck's shipped correction decides;
every p-value is recorded so that a step-down Holm procedure can be applied as a sensitivity analysis.
Run with the QuCheck environment (qiskit 1.1.1).
"""
import ast, contextlib, csv, io, json, multiprocessing as mp, os, sys, tempfile, textwrap, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
PKG = Path(__file__).resolve().parents[2]
FROZEN = PKG / "data/prospective/mqt_bench/frozen_deps"
OUT = Path(os.environ.get("QSD_OUT", PKG / "output")) / "developer_suites"; OUT.mkdir(parents=True, exist_ok=True)
PAIR_SEEDS = list(range(15542, 15554))
CTRL_SEEDS = list(range(16542, 16554))

PROP = textwrap.dedent('''
    import json
    from qiskit import QuantumCircuit
    from qucheck.property import Property
    G1 = json.loads({g1!r}); G2 = json.loads({g2!r}); N = {n}; BARRIER = {barrier}
    def build(gates, barrier=False):
        qc = QuantumCircuit(N, N)
        for g in gates:
            a = g.get("angles", []); q = [int(x) for x in g["q"]]
            getattr(qc, g["gate"])(*a, *q) if a else getattr(qc, g["gate"])(*q)
        if barrier: qc.barrier()
        return qc
    class PairProperty(Property):
        def get_input_generators(self): return []
        def preconditions(self): return True
        def operations(self):
            p, m = build(G1), build(G2, BARRIER)
            self.statistical_analysis.assert_equal(self, list(range(N)), p, list(range(N)), m, basis=["x", "y", "z"])
''')


def load():
    """Gate lists of the 20 circuits and their mutants."""
    def gl(s):
        try: return json.loads(s)
        except ValueError: return ast.literal_eval(s)
    orig, nq, mut = {}, {}, {}
    for r in csv.DictReader(open(FROZEN / "PROGRAM_MANIFEST.csv")):
        orig[r["program"]] = gl(r["base_gates"]); nq[r["program"]] = int(r["n"])
    for s in json.load(open(FROZEN / "S1_SUBJECTS.json")):
        orig[s["subject"]] = s["base_gates"] if isinstance(s["base_gates"], list) else gl(s["base_gates"]); nq[s["subject"]] = int(s["n"])
    for r in csv.DictReader(open(FROZEN / "MUTANT_POPULATION.csv")):
        mut[r["mutant_id"]] = {"subject": r["program"], "gates": gl(r["mutated_gates"])}
    for r in csv.DictReader(open(FROZEN / "S2_GENERATED_MUTANTS.csv")):
        if r.get("mutated_gates"): mut[r["mutant_id"]] = {"subject": r["subject"], "gates": gl(r["mutated_gates"])}
    return orig, nq, mut


_HB0 = None
_REC = []


def run_one(a):
    pair, role, g1, g2, n, seed, barrier = a
    import qucheck.stats.statistical_analysis_coordinator as SAC
    from qiskit_aer import AerSimulator
    from qucheck.coordinator import Coordinator
    global _HB0
    rec = _REC; rec.clear()
    if _HB0 is None:                              # record every p-value once per process
        _HB0 = SAC.holm_bonferroni_correction
        def hb(assertions, pvals, alpha=0.05):
            for prop, d in pvals.items():
                for asr, lst in d.items(): _REC.extend(float(x) for x in lst)
            return _HB0(assertions, pvals, alpha)
        SAC.holm_bonferroni_correction = hb
    name = f"prop_{pair.replace('#', '_').replace('/', '_')}_{role}_{seed}"     # one module per run: QuCheck imports by name
    with tempfile.TemporaryDirectory() as d:
        Path(d, name + ".py").write_text(PROP.format(g1=json.dumps(g1), g2=json.dumps(g2), n=n, barrier=barrier))
        co = Coordinator(num_inputs=1, random_seed=seed, alpha=0.05, backend=AerSimulator(seed_simulator=seed))
        t0 = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            co.test(d, measurements=2000, run_optimization=False)
        failing = co.test_runner.list_failing_properties()
    return {"pair": pair, "role": role, "seed": seed, "detected": bool(failing), "p_values": list(rec),
            "seconds": round(time.perf_counter() - t0, 3)}


if __name__ == "__main__":
    orig, nq, mut = load()
    dec = [x for x in csv.DictReader(open(PKG / "data/certification/outcomes/R2V_TABLE_X_DECISIONS.csv")) if x["part"] == "interface"]
    only_qc = sorted(x["mutant_id"] for x in dec if x["R_O_v2_QUTest"] == "true" and x["R_O_v2_QuCheck"] == "false")
    only_qt = sorted(x["mutant_id"] for x in dec if x["R_O_v2_QUTest"] == "false" and x["R_O_v2_QuCheck"] == "true")
    tr = [x for x in csv.DictReader(open(PKG / "data/interventions/transfer/B5_A4B_REPAIR_TRANSFER.csv")) if x["outcome"] != "NOT_EVALUABLE"]
    assert (len(only_qc), len(only_qt), len(tr)) == (28, 25, 21)
    labels = {}
    for k in only_qc: labels.setdefault(k, []).append("only_qucheck")
    for k in only_qt: labels.setdefault(k, []).append("only_qutest")
    for x in tr: labels.setdefault(x["case"], []).append("transfer_" + x["outcome"])
    jobs = []
    for k in sorted(labels):
        s = mut[k]["subject"]; n = nq[s]
        jobs += [(k, "mutant", orig[s], mut[k]["gates"], n, sd, False) for sd in PAIR_SEEDS]
        jobs += [(k, "control", orig[s], orig[s], n, sd, True) for sd in CTRL_SEEDS]
    t0 = time.time()
    with ProcessPoolExecutor(2, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(run_one, jobs, chunksize=6))
    json.dump({"labels": labels, "runs": res, "wall_seconds": round(time.time() - t0, 1)},
              open(OUT / "X2_QUCHECK_20_RUNS.json", "w"))
    print("pairs", len(labels), "executions", len(res), "seconds", round(time.time() - t0, 1))
