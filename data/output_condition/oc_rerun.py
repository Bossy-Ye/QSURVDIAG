"""Native rerun of the corrected output-condition suites (plan: data/output_condition/PLAN.md).

Usage (analytic-tier environment, QUTest 0.1.0 on PATH as the adapter expects):
  python -I oc_rerun.py <package root> <run tree> <out dir> [workers]
<run tree> is a copy of the input tree that scripts/reproduce_analytic.py assembles (<out>/analytic/r2v_root),
with study/.venv-qutest-audit/bin/qutest pointing at the pinned QUTest 0.1.0 binary. The frozen study code is imported
read-only from the package; nothing in the package is written.
"""
import csv, json, os, sys, time, platform
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

PKG, TREE, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 else 4
FROZEN = PKG / "data/prospective/mqt_bench/frozen_deps"
os.environ["QSD_ROOT"] = str(TREE / "study")
sys.path[:0] = [str(TREE / "study/cross_tool_stage/qutest"), str(FROZEN), str(PKG / "data/primary/implementation")]
os.chdir(FROZEN)                       # e1_lib reads SSPEC_PROVENANCE.json from the working directory
import qutest_adapter as QA            # noqa: E402
from e1_lib import MUT, orig, nq       # noqa: E402
from e1_seed_schedule import seed_for  # noqa: E402
from qutest_execution_adapter import adapt  # noqa: E402
from serialization_adapter import emit_name  # noqa: E402

N, R, THETA = 8000, 12, 0.05           # suite-experiment settings: analytic references, N = 8,000, R = 12
GUARD_SEEDS = [42 + r for r in range(R)]
assert Path(QA.QUTEST).resolve().is_file(), QA.QUTEST

SSPEC = {m["subject"]: m["assertions"] for m in json.load(open(FROZEN / "SSPEC_PROVENANCE.json"))["subjects"]
         if m["status"] == "S_SPEC_GROUNDED"}

def corrected(sub):
    """The corrected suite: the recorded assertions plus those the specified condition needs (plan section 2)."""
    n = nq[sub]; A = list(SSPEC[sub])
    if sub.startswith("simon"):
        A.append(f'//% expect observable "Z0 Z1" ~= 1.0 atol={THETA}')
    elif sub.startswith("qft"):
        ref = {format(x, f"0{n}b"): 1 / 2 ** n for x in range(2 ** n)}
        A += ["//% expect distribution ref " + json.dumps(ref, separators=(",", ":")),
              f"//% expect distribution total_variation_distance <= {THETA}"]
    elif sub.startswith("wstate"):
        ref = {format(1 << q, f"0{n}b"): 1 / n for q in range(n)}
        A += ["//% expect distribution ref " + json.dumps(ref, separators=(",", ":")),
              f"//% expect distribution total_variation_distance <= {THETA}"]
    return A

def lowered(gates):
    return [{**x, "gate": emit_name(x["gate"])} for x in adapt(gates)]

def cell(job):
    kind, key, sub, seeds = job
    gates = orig[sub] if kind == "guard" else MUT[key]["gates"]
    A = corrected(sub); out = []
    for s in seeds:
        t0 = time.perf_counter()
        v, msg = QA.run_qutest(QA.make_test(lowered(gates), nq[sub], A, N, s))
        out.append((s, v, round(time.perf_counter() - t0, 3), msg[:80]))
    return kind, key, sub, len(A), out

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    aff = list(csv.DictReader(open(PKG / "data/output_condition/AFFECTED_PAIRS.csv")))
    subs = sorted({a["subject"] for a in aff})
    jobs = [("guard", sub, sub, GUARD_SEEDS) for sub in subs]
    jobs += [("mutant", a["mutant_id"], a["subject"], [seed_for(MUT[a["mutant_id"]]["population"], a["mutant_id"], r) for r in range(R)])
             for a in aff]
    t0 = time.time()
    with ProcessPoolExecutor(WORKERS) as ex:
        res = list(ex.map(cell, jobs))
    wall = time.time() - t0
    with open(OUT / "OC_RUNS.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["kind", "case", "subject", "n_assertions", "seed", "verdict", "seconds", "detail"])
        for kind, key, sub, na, out in res:
            for s, v, sec, msg in out: w.writerow([kind, key, sub, na, s, v, sec, msg])
    summary = {"settings": {"N": N, "R": R, "theta": THETA, "guard_seeds": GUARD_SEEDS,
                            "mutant_seeds": "e1_seed_schedule.seed_for(population, case, rep)"},
               "corrected_suites": {s: corrected(s) for s in subs},
               "executions": sum(len(o) for *_, o in res), "shots": N * sum(len(o) for *_, o in res),
               "wall_seconds": round(wall, 1), "workers": WORKERS,
               "cpu_seconds_in_runs": round(sum(x[2] for *_, o in res for x in o), 1),
               "machine": platform.platform(), "python": platform.python_version()}
    json.dump(summary, open(OUT / "OC_RUN_SUMMARY.json", "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("executions", "wall_seconds", "cpu_seconds_in_runs")}))

if __name__ == "__main__":
    main()
