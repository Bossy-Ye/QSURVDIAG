"""The 100 observation limitations (35 of the 20 circuits, 65 at later positions) under the rotated profile.

Rotated profile: the declared QUTest types on the joint distribution of every qubit under each of the 3^n XYZ
settings; the all-Z setting is the declared profile and holds the baseline suite (output-register marginals).
Witness order: all-Z, then the settings in the X1 search order, the closed witness order (v3) within each.

stage2:  candidate (packaged rule; R_C, R_S, R_T as recorded), first witness outside the suite, undecided instances
         up to it, and the negative control (first instance outside the suite decided below theta);
         writes X1_TRANSITION_STAGE2.csv.
run:     the control alone at N = 8,000 on the mutant at the witness seeds (13042-13053; later positions
         21042-21053) and on the original at 14042-14044 (22042-22044); writes X1_TRANSITION_RUNS.jsonl.gz.
analyze: Stage 3 from the archived stage2 and run records and the recorded witness runs; writes X1_TRANSITION.csv
         and X1_TRANSITION_SUMMARY.json. Standard library only.

Usage: QSD_OUT=<dir with position/ from x4_select.py> <analytic python> -B x1_transition.py stage2|run|analyze
"""
import os, csv, gzip, json, collections, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "observation_change"; OUT.mkdir(parents=True, exist_ok=True)
N = 8000
SEEDS = {"primary": (list(range(13042, 13054)), list(range(14042, 14045))),
         "position": (list(range(21042, 21054)), list(range(22042, 22045)))}
if sys.argv[1:2] != ["analyze"]:
    sys.path.insert(0, str(DIR.parents[1] / "scripts/lib"))
    import numpy as np
    import counts as C
    import x1_position as XP
    undecided = lambda d: abs(d - C.THETA) <= C.RES
    below = lambda d: d < C.THETA - C.RES


def population():
    orig, nq, outreg, mut = C.load_population()
    R = {r["mutant_id"]: r for r in csv.DictReader(open(C.OUTC / "R2V_FINAL_PRIMARY.csv"))}
    out = []
    for r in csv.DictReader(open(DIR / "X1_SETTINGS.csv")):
        p, n = r["program"], int(r["n"]); x = R[r["pair"]]
        assert x["v2_report"] == "CL3"
        out.append({"pair": r["pair"], "arm": "primary", "population": "20 circuits", "program": p, "n": n,
                    "og": orig[p], "mg": mut[r["pair"]]["gates"], "suite": [int(q) for q in outreg[p]],
                    "R_C": x["R_C"], "R_S": x["R_S"], "R_T": x["R_T"], "rec": r})
    S = json.load(open(XP.ROOT / "position/X4_SUBJECTS.json"))
    D = {}
    for l in gzip.open(DIR.parent / "position/X4_NATIVE_RUNS.jsonl.gz", "rt"):
        x = json.loads(l)
        if x.get("final"): D[x["mutant_id"]] = x["diagnosis"]
    rec = {r["pair"]: r for r in csv.DictReader(open(DIR / "X1_POSITION_SETTINGS.csv"))}
    for pair, pop, subj, n, og, mg in XP.population():
        d = D[pair]; assert d["v2_candidate"] == "CL3"
        out.append({"pair": pair, "arm": "position", "population": pop, "program": subj, "n": n, "og": og, "mg": mg,
                    "suite": [int(q) for q in C._gl(S[subj]["outreg"])],
                    "R_C": d["R_C"], "R_S": d["R_S"], "R_T": d["R_T"], "rec": rec[pair]})
    assert len(out) == 100
    return out


def control(po, pmu, n, suite):
    """First all-Z instance outside the suite decided below theta, with the original's ideal reference."""
    for kind, key, d, ref in C.ordered(np.abs(po) ** 2, np.abs(pmu) ** 2, n):
        if not (kind == "marginal" and key in suite) and below(d):
            return kind, key, d, ref


def stage2(a):
    sys.path.insert(0, str(C.FROZEN))
    import qsurvdiag_confirmatory as Q
    n, suite = a["n"], a["suite"]
    po, pmu = C.sv(a["og"], n), C.sv(a["mg"], n)
    t0 = time.perf_counter(); und = []; w = None; evaluated = 0
    for kind, key, d, ref in C.ordered(np.abs(po) ** 2, np.abs(pmu) ** 2, n):        # all-Z: the declared profile
        if kind == "marginal" and key in suite: continue
        assert not C.separates(d), (a["pair"], kind, key)
        if undecided(d): und.append(("Z" * n, kind, key, d))
    for s, k in XP.settings(n):
        evaluated += 1
        pp, pm = np.abs(C.rotate(po, n, s)) ** 2, np.abs(C.rotate(pmu, n, s)) ** 2
        for kind, key, d, ref in C.ordered(pp, pm, n):
            if undecided(d): und.append((s, kind, key, d))
            elif C.separates(d):
                w = (s, kind, key, d, ref, float(np.abs(pp - pm).max())); break
        if w: break
    sec = time.perf_counter() - t0
    tri = {"true": Q.T, "false": Q.F, "undecided": Q.U}
    rel = {"R_C": tri[a["R_C"]], "R_S": tri[a["R_S"]], "R_T": tri[a["R_T"]],
           "R_O": (Q.F if w[5] > 1e-8 else Q.U) if w else Q.U, "R_A": Q.T if w else Q.F}
    cand, _, und_rel = Q.candidate(rel)
    c = control(po, pmu, n, suite)
    r = a["rec"]
    same = bool(w) and (w[0], w[1], "" if w[2] is None else str(w[2])) == (r["setting_q0_first"], r["witness_kind"], r["witness_key"])
    return {"pair": a["pair"], "arm": a["arm"], "population": a["population"], "program": a["program"], "n": n,
            "suite": ";".join(map(str, suite)), **{k: v.value for k, v in rel.items()}, "candidate": cand or "",
            "undecided_relation": und_rel or "", "setting_q0_first": w[0] if w else "",
            "witness_kind": w[1] if w else "", "witness_key": "" if not w or w[2] is None else w[2],
            "witness_d": f"{w[3]:.6f}" if w else "", "witness_is_named": same,
            "settings_evaluated": evaluated, "undecided_instances": len(und),
            "undecided_list": " ".join(f"{s}:{k}:{key}" for s, k, key, _ in und),
            "control_kind": c[0] if c else "", "control_key": "" if not c or c[1] is None else c[1],
            "control_d": f"{c[2]:.6f}" if c else "", "control_ref": "" if not c or c[3] is None else f"{c[3]:.6f}",
            "search_seconds": f"{sec:.3f}"}


def run_job(a):
    sys.path.insert(0, str(XP.CAP))
    import qutest_capture as Q
    pair, role, gates, n, lines, seed = a
    r = Q.run_both(C.QUTEST, C.wrapped_test(gates, n, lines, N, seed, None, "test_x1"))
    return {"pair": pair, "role": role, "arm": "formal_control", "seed": seed, "cli": r["cli"], "inproc": r["inproc"],
            "assertions": r["assertions"], "counts": r["counts"], "cli_seconds": r["cli_seconds"]}


def resumable(name, jobs, fn, key):
    part = OUT / f"{name}.partial.jsonl"
    done = {}
    if part.exists():
        for l in open(part): x = json.loads(l); done[key(x)] = x
    with ProcessPoolExecutor(int(os.environ.get("WORKERS", "4"))) as ex, open(part, "a") as f:
        for fu in as_completed([ex.submit(fn, j) for j in jobs if key(j) not in done]):
            x = fu.result(); done[key(x)] = x; f.write(json.dumps(x, separators=(",", ":")) + "\n"); f.flush()
            print(*(x.get(k) for k in ("pair", "role", "seed", "cli", "candidate", "witness_is_named")), flush=True)
    return done


if __name__ == "__main__" and sys.argv[1] == "stage2":
    pop = population()
    done = resumable("X1_TRANSITION_STAGE2", pop, stage2, lambda x: x["pair"])
    rows = [done[a["pair"]] for a in pop]
    with open(OUT / "X1_TRANSITION_STAGE2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

elif __name__ == "__main__" and sys.argv[1] == "run":
    jobs = []
    for a in population():
        n = a["n"]; po, pmu = C.sv(a["og"], n), C.sv(a["mg"], n)
        kind, key, d, ref = control(po, pmu, n, a["suite"])
        lines = C.pragma_lines(kind, key, n, ref, np.abs(po) ** 2)
        ms, gs = SEEDS[a["arm"]]
        jobs += [(a["pair"], "original", a["og"], n, lines, sd) for sd in gs]
        jobs += [(a["pair"], "mutant", a["mg"], n, lines, sd) for sd in ms]
    key = lambda x: (x[0], x[1], x[5]) if isinstance(x, tuple) else (x["pair"], x["role"], x["seed"])
    t0 = time.time(); done = resumable("X1_TRANSITION_RUNS", jobs, run_job, key)
    with gzip.open(OUT / "X1_TRANSITION_RUNS.jsonl.gz", "wt") as f:
        for j in jobs: f.write(json.dumps(done[key(j)], separators=(",", ":")) + "\n")
    print("executions", len(jobs), "seconds", round(time.time() - t0, 1))

elif __name__ == "__main__" and sys.argv[1] == "analyze":
    st = list(csv.DictReader(open(DIR / "X1_TRANSITION_STAGE2.csv")))
    runs = [json.loads(l) for l in gzip.open(DIR / "X1_TRANSITION_RUNS.jsonl.gz", "rt")]
    assert all(r["cli"] == r["inproc"] for r in runs) and not any(r["cli"] == "UNSUPPORTED" for r in runs)
    g = collections.defaultdict(list)
    for r in runs: g[(r["pair"], r["role"])].append(r)
    old = collections.defaultdict(list)
    for f in ("X1_NATIVE_RUNS.jsonl.gz", "X1_POSITION_NATIVE_RUNS.jsonl.gz"):
        for l in gzip.open(DIR / f, "rt"):
            x = json.loads(l); old[(x["pair"], x["role"], x["arm"])].append(x)
    rows = []
    for s in st:
        p = s["pair"]; ms, gs = SEEDS[s["arm"]]
        wm = old[(p, "mutant", "rotated")]; wo = old[(p, "original", "rotated")]
        assert sorted(int(x["seed"]) for x in wm) == ms and len(wo) == 12
        wk = sum(x["cli"] == "KILLED" for x in wm)
        wg = sum(x["cli"] == "KILLED" for x in wo if int(x["seed"]) in gs)
        wo12 = sum(x["cli"] == "KILLED" for x in wo)
        cm, co = g[(p, "mutant")], g[(p, "original")]
        assert sorted(x["seed"] for x in cm) == ms and sorted(x["seed"] for x in co) == gs
        ck = sum(x["cli"] == "KILLED" for x in cm); cg = sum(x["cli"] == "KILLED" for x in co)
        # the recorded unrotated witness, when it is the control, ran the same test at the same seeds
        uw = old[(p, "mutant", "control")]
        same_inst = (s["control_kind"], s["control_key"]) == (s["witness_kind"], s["witness_key"])
        replay = ("" if not same_inst else
                  {x["seed"]: x["cli"] for x in cm} == {int(x["seed"]): x["cli"] for x in uw})
        cert = (s["candidate"] == "CL4" and s["witness_is_named"] == "True" and wk == 12 and wg == 0
                and s["control_kind"] != "" and ck < 12 and cg == 0)
        rows.append({k: s[k] for k in ("pair", "arm", "population", "program", "n", "candidate", "setting_q0_first",
                                       "witness_kind", "witness_key", "witness_d", "witness_is_named",
                                       "undecided_instances", "control_kind", "control_key", "control_d")}
                    | {"witness_kills": wk, "witness_guard_failures": wg, "witness_original_failures_of_12": wo12,
                       "control_kills": ck, "control_guard_failures": cg, "control_replays_recorded": replay,
                       "certified": cert})
    with open(OUT / "X1_TRANSITION.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    cnt = lambda f: sum(1 for x in rows if f(x))
    summ = {"pairs": len(rows),
            "candidates": dict(collections.Counter(x["candidate"] for x in rows)),
            "witness_is_named": cnt(lambda x: x["witness_is_named"] == "True"),
            "undecided_instances_total": sum(int(x["undecided_instances"]) for x in rows),
            "controls_all_z": cnt(lambda x: x["control_kind"] != ""),
            "control_kinds": dict(collections.Counter(x["control_kind"] for x in rows)),
            "control_d_max": max(float(x["control_d"]) for x in rows),
            "control_kills_total": sum(x["control_kills"] for x in rows),
            "control_kills_max": max(x["control_kills"] for x in rows),
            "guard_failures_total": sum(x["witness_guard_failures"] + x["control_guard_failures"] for x in rows),
            "controls_replaying_recorded": f"{cnt(lambda x: x['control_replays_recorded'] is True)}/"
                                           f"{cnt(lambda x: x['control_replays_recorded'] != '')}",
            "certified": cnt(lambda x: x["certified"]),
            "certified_by_population": {p: f"{cnt(lambda x: x['population'] == p and x['certified'])}/{cnt(lambda x: x['population'] == p)}"
                                        for p in sorted({x["population"] for x in rows})},
            "executions": len(runs)}
    json.dump(summ, open(OUT / "X1_TRANSITION_SUMMARY.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))
