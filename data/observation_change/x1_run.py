"""X1, sections 3-4: native QUTest runs of the separating settings (X1_SETTINGS.csv).

Per pair: the rotated test (setting gates, measurement of every qubit, the witness with the original's ideal
reference rounded to 4 decimals, tolerance 0.05) on the original (seeds 14042-14053) and on the mutant (seeds
13042-13053), and the control: the same witness without the setting's gates on the mutant (seeds 13042-13053).
N = 8,000. Each execution runs through the pinned qutest CLI (verdict of record) and in process with the counts kept.
"""
import os, csv, gzip, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "observation_change"; OUT.mkdir(parents=True, exist_ok=True)
N = 8000
MUT_SEEDS = list(range(13042, 13054))
ORIG_SEEDS = list(range(14042, 14054))
CAP = C.PKG / "data/all_pairs"


def assertion_for(row, po, n):
    s = row["setting_q0_first"]; kind = row["witness_kind"]
    key = int(row["witness_key"]) if row["witness_key"] != "" else None
    pp = np.abs(C.rotate(po, n, s)) ** 2
    ref = next(x[3] for x in C.universe(pp, pp, n) if x[0] == kind and x[1] == key)
    return C.pragma_lines(kind, key, n, ref, pp)


def job(a):
    sys.path.insert(0, str(CAP))
    import qutest_capture as Q
    pair, role, arm, gates, n, setting, lines, seed = a
    text = C.wrapped_test(gates, n, lines, N, seed, setting if arm == "rotated" else None, "test_x1")
    r = Q.run_both(C.QUTEST, text)
    return {"pair": pair, "role": role, "arm": arm, "seed": seed, "cli": r["cli"], "inproc": r["inproc"],
            "assertions": r["assertions"], "counts": r["counts"], "cli_seconds": r["cli_seconds"]}


if __name__ == "__main__":
    orig, nq, outreg, mut = C.load_population()
    rows = list(csv.DictReader(open(DIR / "X1_SETTINGS.csv")))
    jobs = []
    for r in rows:
        p = r["program"]; n = int(r["n"]); po = C.sv(orig[p], n)
        lines = assertion_for(r, po, n)
        for sd in ORIG_SEEDS: jobs.append((r["pair"], "original", "rotated", orig[p], n, r["setting_q0_first"], lines, sd))
        for sd in MUT_SEEDS: jobs.append((r["pair"], "mutant", "rotated", mut[r["pair"]]["gates"], n, r["setting_q0_first"], lines, sd))
        # control: same witness instance, references from the unrotated original
        pz = np.abs(po) ** 2; kind = r["witness_kind"]; key = int(r["witness_key"]) if r["witness_key"] != "" else None
        refz = next(x[3] for x in C.universe(pz, pz, n) if x[0] == kind and x[1] == key)
        clines = C.pragma_lines(kind, key, n, refz, pz)
        for sd in MUT_SEEDS: jobs.append((r["pair"], "mutant", "control", mut[r["pair"]]["gates"], n, None, clines, sd))
    t0 = time.time()
    with ProcessPoolExecutor(4) as ex: res = list(ex.map(job, jobs, chunksize=4))
    with gzip.open(OUT / "X1_NATIVE_RUNS.jsonl.gz", "wt") as f:
        for x in res: f.write(json.dumps(x, separators=(",", ":")) + "\n")
    print("executions", len(res), "seconds", round(time.time() - t0, 1))
