"""POSITION_EXTENSION.md: the separating settings of the 65 later-position observation limitations, and their native
runs.

settings: the X1 rule (x1_settings.py) on the final states of each pair's executed input (preparation and gates
          written by data/position/x4_select.py to $QSD_OUT/position); writes X1_POSITION_SETTINGS.csv with the number
          of settings evaluated and the search time.
run:      X1 section 3 on these settings at N = 8,000: mutant seeds 21042-21053, original seeds 22042-22053, control
          without the setting's gates on the mutant; writes X1_POSITION_NATIVE_RUNS.jsonl.gz.

Usage: <analytic python> -B x1_position.py settings|run
"""
import os, csv, gzip, itertools, json, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C

DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output"))
OUT = ROOT / "observation_change"; OUT.mkdir(parents=True, exist_ok=True)
N = 8000
MUT_SEEDS = list(range(21042, 21054))
ORIG_SEEDS = list(range(22042, 22054))
CAP = C.PKG / "data/all_pairs"


def population():
    S = json.load(open(ROOT / "position/X4_SUBJECTS.json")); G = json.load(open(ROOT / "position/X4_MUTANT_GATES.json"))
    rows = [r for r in csv.DictReader(open(DIR.parent / "position/X4_FINAL.csv")) if r["report"] == "CL3"]
    assert len(rows) == 65
    return [(r["mutant_id"], r["population"], r["subject"], S[r["subject"]]["n"], S[r["subject"]]["prep"] + S[r["subject"]]["gates"],
             S[r["subject"]]["prep"] + G[r["mutant_id"]]) for r in rows]


def settings(n):
    for k in range(1, n + 1):
        for qs in itertools.combinations(range(n), k):
            for bs in itertools.product("XY", repeat=k):
                s = ["Z"] * n
                for q, b in zip(qs, bs): s[q] = b
                yield "".join(s), k


def find(og, mg, n):
    po, pmu = C.sv(og, n), C.sv(mg, n)
    assert C.first_witness(np.abs(po) ** 2, np.abs(pmu) ** 2, n) is None     # nothing above theta unrotated
    t0 = time.perf_counter(); evaluated = 0
    for s, k in settings(n):
        evaluated += 1
        w = C.first_witness(np.abs(C.rotate(po, n, s)) ** 2, np.abs(C.rotate(pmu, n, s)) ** 2, n)
        if w is not None:
            return s, k, w, evaluated, time.perf_counter() - t0
    return None, None, None, evaluated, time.perf_counter() - t0


def run_job(a):
    sys.path.insert(0, str(CAP))
    import qutest_capture as Q
    pair, role, arm, gates, n, setting, lines, seed = a
    r = Q.run_both(C.QUTEST, C.wrapped_test(gates, n, lines, N, seed, setting if arm == "rotated" else None, "test_x1"))
    return {"pair": pair, "role": role, "arm": arm, "seed": seed, "cli": r["cli"], "inproc": r["inproc"],
            "assertions": r["assertions"], "counts": r["counts"], "cli_seconds": r["cli_seconds"]}


def setting_job(a):
    pair, pop, subj, n, og, mg = a
    s, k, w, ev, sec = find(og, mg, n)
    return {"pair": pair, "population": pop, "program": subj, "n": n, "setting_q0_first": s or "", "rotated_qubits": k or "",
            "witness_kind": w[0] if w else "", "witness_key": "" if not w or w[1] is None else w[1],
            "witness_d": f"{w[2]:.6f}" if w else "", "reference": "" if not w or w[3] is None else f"{w[3]:.6f}",
            "settings_evaluated": ev, "search_seconds": f"{sec:.3f}"}


if __name__ == "__main__" and sys.argv[1] == "settings":
    pop = population(); part = OUT / "X1_POSITION_SETTINGS.partial.jsonl"      # one line per finished pair, so the search resumes
    done = {json.loads(l)["pair"]: json.loads(l) for l in open(part)} if part.exists() else {}
    with ProcessPoolExecutor(int(os.environ.get("WORKERS", "4"))) as ex, open(part, "a") as f:
        for fu in as_completed([ex.submit(setting_job, a) for a in pop if a[0] not in done]):
            r = fu.result(); done[r["pair"]] = r; f.write(json.dumps(r) + "\n"); f.flush(); print(r["pair"], r["setting_q0_first"], r["settings_evaluated"], r["search_seconds"], flush=True)
    rows = [done[a[0]] for a in pop]
    with open(OUT / "X1_POSITION_SETTINGS.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

elif __name__ == "__main__" and sys.argv[1] == "run":
    pop = {p: (n, og, mg) for p, _, _, n, og, mg in population()}
    jobs = []
    for r in csv.DictReader(open(OUT / "X1_POSITION_SETTINGS.csv")):
        if not r["setting_q0_first"]: continue
        n, og, mg = pop[r["pair"]]; po = C.sv(og, n)
        kind = r["witness_kind"]; key = int(r["witness_key"]) if r["witness_key"] != "" else None
        pp = np.abs(C.rotate(po, n, r["setting_q0_first"])) ** 2
        lines = C.pragma_lines(kind, key, n, next(x[3] for x in C.universe(pp, pp, n) if x[0] == kind and x[1] == key), pp)
        pz = np.abs(po) ** 2
        clines = C.pragma_lines(kind, key, n, next(x[3] for x in C.universe(pz, pz, n) if x[0] == kind and x[1] == key), pz)
        jobs += [(r["pair"], "original", "rotated", og, n, r["setting_q0_first"], lines, sd) for sd in ORIG_SEEDS]
        jobs += [(r["pair"], "mutant", "rotated", mg, n, r["setting_q0_first"], lines, sd) for sd in MUT_SEEDS]
        jobs += [(r["pair"], "mutant", "control", mg, n, None, clines, sd) for sd in MUT_SEEDS]
    part = OUT / "X1_POSITION_NATIVE_RUNS.partial.jsonl"                      # one line per execution, so the runs resume
    key = lambda x: (x[0], x[1], x[2], x[7]) if isinstance(x, tuple) else (x["pair"], x["role"], x["arm"], x["seed"])
    done = {key(json.loads(l)): json.loads(l) for l in open(part)} if part.exists() else {}
    t0 = time.time()
    with ProcessPoolExecutor(int(os.environ.get("WORKERS", "4"))) as ex, open(part, "a") as f:
        for fu in as_completed([ex.submit(run_job, j) for j in jobs if key(j) not in done]):
            x = fu.result(); done[key(x)] = x; f.write(json.dumps(x, separators=(",", ":")) + "\n"); f.flush()
    with gzip.open(OUT / "X1_POSITION_NATIVE_RUNS.jsonl.gz", "wt") as f:
        for j in jobs: f.write(json.dumps(done[key(j)], separators=(",", ":")) + "\n")
    print("executions", len(jobs), "seconds", round(time.time() - t0, 1))
