"""X4, section 3 (OPERATIONAL.md): native baseline, v2 diagnosis with witness order v3, native confirmation and
negative control, and the v2 report of every selected mutation, with the packaged implementation.

Usage: <analytic python> -B x4_run.py [--parse-only]
"""
import csv, json, multiprocessing as mp, os, sys, time, types
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]; OUTD = Path(os.environ.get("QSD_OUT", PKG / "output")) / "position"; OUTD.mkdir(parents=True, exist_ok=True)
TREE = OUTD / "tree"                                  # built by build_tree.py <package> <tree>
os.environ["R2V_PA"] = str(TREE / "artifact") + "/"
os.environ["QSD_ROOT"] = str(TREE / "study")
os.environ["QISKIT_SETTINGS"] = str(PKG / "environment/qiskit_settings.conf")
MUT_SEEDS = list(range(17042, 17054)); ORIG_SEEDS = list(range(18042, 18054)); GUARD3 = ORIG_SEEDS[:3]
N, REPS, ATOL = 2000, 12, 0.05


def setup():
    sys.path.insert(0, str(PKG / "data/primary/implementation"))
    sys.path.insert(0, str(TREE / "artifact/outcomes"))
    import r2v_lib as V
    V.MUT_SEEDS, V.GUARD_SEEDS = MUT_SEEDS, GUARD3
    if getattr(V, "_x4_v3", False):                   # patch once per process
        import r2v_arms as A, r2v_finalize as Fz, qutest_adapter as QA
        return V, A, Fz, QA
    V._x4_v3 = True
    _o = V.ordered_universe
    def closed_order(pp, pm, n):                     # data/certification/witness_order/native.py
        ordered, alld = _o(pp, pm, n)
        for q in range(n):
            m = 1 << q; a = V.zexp(pp, n, m)
            ordered.append({"kind": "zmask", "key": m, "d": abs(a - V.zexp(pm, n, m)), "ref": a})
        assert len(ordered) == len(alld) == 2 ** (n + 1) + n + 3
        return ordered, alld
    V.ordered_universe = closed_order
    sys.modules["r2_external"] = types.ModuleType("r2_external")      # only external() of r2v_arms uses it
    sys.path.append(str(PKG / "data/prospective/mqt_bench/frozen_deps"))
    import r2v_arms as A, r2v_finalize as Fz
    import qutest_adapter as QA
    return V, A, Fz, QA


def refs(QA, s, og):
    import numpy as np
    n = s["n"]
    if s["population"] == "external":
        return {q: QA.reference_marginal(og, n, q) for q in s["outreg"]}
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    qc = QuantumCircuit(n)
    for g in og:
        a = g.get("angles", []); getattr(qc, g["gate"])(*a, *[int(i) for i in g["q"]]) if a else getattr(qc, g["gate"])(*[int(i) for i in g["q"]])
    p = np.abs(Statevector.from_int(0, dims=(2,) * n).evolve(qc).data) ** 2; idx = np.arange(2 ** n)
    return {q: round(float(p[((idx >> q) & 1) == 1].sum()), 4) for q in s["outreg"]}


def guard_job(a):
    sid, s = a
    V, A, Fz, QA = setup()
    og = s["prep"] + s["gates"]; r = refs(QA, s, og)
    lines = [QA.marginal_assertion(q, r[q]) for q in s["outreg"]]
    v = [QA.run_qutest(QA.make_test(V.to_text(og), s["n"], lines, N, sd))[0] for sd in ORIG_SEEDS]
    fails = v.count("KILLED"); uns = v.count("UNSUPPORTED")
    ok = (fails == 0) if s["population"] == "other" else (fails <= 1 and uns == 0)
    return sid, {"refs": r, "verdicts": v, "fails": fails, "unsupported": uns, "guard_ok": ok}


def pair_job(a):
    try:
        return _pair_job(a)
    except Exception as e:                            # recorded, not silently dropped
        import traceback
        return {"mutant_id": a[0]["mutant_id"], "subject": a[0]["subject"], "population": a[0]["population"],
                "third": a[0]["third"], "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-2000:]}


def _pair_job(a):
    row, s, gates, g, parse_only = a
    V, A, Fz, QA = setup()
    n = s["n"]; og = s["prep"] + s["gates"]; mg = s["prep"] + gates
    t0 = time.time()
    parse = QA.run_qutest(QA.make_test(V.to_text(mg), n, [], N, MUT_SEEDS[0]))[0]
    out = {"mutant_id": row["mutant_id"], "subject": row["subject"], "population": row["population"], "third": row["third"],
           "location": row["location"], "stratum": row["stratum"], "parse": parse}
    if parse_only or parse == "UNSUPPORTED":
        return out
    lines = [QA.marginal_assertion(q, g["refs"][q]) for q in s["outreg"]]
    v = [QA.run_qutest(QA.make_test(V.to_text(mg), n, lines, N, sd))[0] for sd in MUT_SEEDS]
    k = v.count("KILLED")
    rec = {"v1_report": "", "native_verdict": "KILLED" if k == REPS else ("SURVIVED" if k == 0 else "SPLIT"),
           "kills": k, "reps": REPS, "guard_ok": g["guard_ok"]}
    jobs = []
    d = A.diagnose("x4", row["mutant_id"], n, og, mg, s["outreg"], "unitary" if s["contract"] == "unitary" else "fixed",
                   rec, jobs, {}, row["subject"])
    nat = {j["job_id"]: V.native_check(j["mut_gates"], j["orig_gates"], j["n"], j["lines"]) for j in jobs}
    fin = Fz.finalize_row("x4", row["mutant_id"], d, nat)
    out.update({"baseline_verdicts": ";".join(v), "unsupported": v.count("UNSUPPORTED"), "diagnosis": {kk: (vv if not isinstance(vv, float) else round(vv, 15)) for kk, vv in d.items()},
                "native_jobs": [{"job_id": j["job_id"], "inst": j["inst"], "lines": j["lines"], **nat[j["job_id"]]} for j in jobs],
                "final": fin, "seconds": round(time.time() - t0, 1)})
    return out


if __name__ == "__main__":
    parse_only = "--parse-only" in sys.argv
    S = json.load(open(OUTD / "X4_SUBJECTS.json")); G = json.load(open(OUTD / "X4_MUTANT_GATES.json"))   # from x4_select.py
    sel = list(csv.DictReader(open(HERE / "X4_SELECTION.csv")))
    ctx = mp.get_context("spawn")
    guards = json.load(open(HERE / "X4_GUARDS.json"))
    for g in guards.values(): g["refs"] = {int(q): v for q, v in g["refs"].items()}
    if not parse_only and not guards:
        with ProcessPoolExecutor(3, mp_context=ctx) as ex:
            for sid, g in ex.map(guard_job, [(sid, S[sid]) for sid in sorted({r["subject"] for r in sel})]):
                guards[sid] = g
            json.dump(guards, open(OUTD / "X4_GUARDS.json", "w"), indent=1)
    out = OUTD / ("X4_PARSE.jsonl" if parse_only else "X4_NATIVE_RUNS.jsonl")
    done = {json.loads(l)["mutant_id"] for l in open(out)} if out.exists() else set()
    jobs = [(r, S[r["subject"]], G[r["mutant_id"]], guards.get(r["subject"]), parse_only) for r in sel if r["mutant_id"] not in done]
    t0 = time.time()
    with open(out, "a") as f, ProcessPoolExecutor(3, mp_context=ctx) as ex:
        for res in ex.map(pair_job, jobs, chunksize=1):
            f.write(json.dumps(res, separators=(",", ":"), default=str) + "\n"); f.flush()
    print("pairs", len(jobs), "seconds", round(time.time() - t0, 1))
