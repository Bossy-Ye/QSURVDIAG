"""PLAN.md, sections 3-4, with OPERATIONAL.md (X2_CLARIFICATIONS, X2_OPERATIONAL): native runs of both suites on
every mutant and the paired semantic record of each run.

Per (suite, program, mutant, seed): the suite runs on the original at that seed with capture (its verdict is not
used), then on the mutant at that seed with capture (native verdict of record). The record holds the verdict, program
equality on every distinct argument tuple, context alignment, observation equality and the first witness.
Original guard runs use seeds 16042-16053.

Usage: X2_SRC=<QuCheck checkout> <QuCheck environment python> -B x2_run.py <inputs for suite B> [workers]
"""
import base64, io, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", HERE.parents[1] / "output")) / "developer_suites"; OUT.mkdir(parents=True, exist_ok=True)
MUT_SEEDS = list(range(15042, 15054))
ORIG_SEEDS = list(range(16042, 16054))
THETA, RES, EQ = 0.05, 5e-9, 1e-9
MEAS_B = 2500


def _walsh(p):
    w = p.astype(float).copy(); h = 1
    while h < len(w):
        for i in range(0, len(w), 2 * h):
            a = w[i:i + h].copy(); b = w[i + h:i + 2 * h].copy(); w[i:i + h] = a + b; w[i + h:i + 2 * h] = a - b
        h *= 2
    return w


def ordered_a(pp, pm, n):
    """Declared QUTest universe on one context, in the closed witness order (v3)."""
    idx = np.arange(len(pp)); out = []
    for q in range(n):
        a = pp[((idx >> q) & 1) == 1].sum(); b = pm[((idx >> q) & 1) == 1].sum(); out.append(("marginal", q, abs(a - b), a))
    wp, wm = _walsh(pp), _walsh(pm)
    pairs = sorted(((i, j) for i in range(n) for j in range(i + 1, n)), key=lambda t: (t[1] - t[0], t[0], t[1]))
    out += [("zmask", (1 << i) | (1 << j), abs(wp[(1 << i) | (1 << j)] - wm[(1 << i) | (1 << j)]), wp[(1 << i) | (1 << j)]) for i, j in pairs]
    out += [("zmask", m, abs(wp[m] - wm[m]), wp[m]) for m in sorted((m for m in range(1, 2 ** n) if bin(m).count("1") >= 3), key=lambda m: (bin(m).count("1"), m))]
    out += [("prob", x, abs(pp[x] - pm[x]), pp[x]) for x in range(2 ** n)]
    def H_(p): q = p[p > 1e-300]; return float(-(q * np.log2(q)).sum())
    dp = np.abs(pp - pm)
    out.append(("entropy", None, abs(H_(pp) - H_(pm)), H_(pp)))
    out.append(("tvd", None, 0.5 * dp.sum(), None))
    out.append(("hellinger", None, float(np.sqrt(0.5 * np.sum((np.sqrt(pm) - np.sqrt(pp)) ** 2))), None))
    a, b = np.clip(pm, 1e-12, None), np.clip(pp, 1e-12, None)
    out.append(("kl", None, float(np.sum(a * np.log(a / b))), None))
    out += [("zmask", 1 << q, abs(wp[1 << q] - wm[1 << q]), wp[1 << q]) for q in range(n)]
    return out


def ordered_b(pp, pm, n):
    idx = np.arange(len(pp)); out = []
    for q in range(n):
        a = pp[((idx >> q) & 1) == 1].sum(); b = pm[((idx >> q) & 1) == 1].sum(); out.append(("marginal", q, abs(a - b), a))
    return out


def _qpy(qc):
    from qiskit import qpy
    b = io.BytesIO(); qpy.dump(qc, b); return base64.b64encode(b.getvalue()).decode()


CACHE = OUT / "cache"


def _key(suite, program, seed): return CACHE / f"{suite}_{program}_{seed}.pkl"


def orig_job(a):
    """Capture of the original at one seed, shared by every mutant run at that seed."""
    import pickle, x2_capture as X
    from qiskit_aer.backends.aerbackend import AerBackend as AerSimulator
    suite, program, seed, ninp = a
    held = []
    run0 = AerSimulator.run
    def keep(self, circuits, *aa, **kk):
        held.extend(circuits if isinstance(circuits, (list, tuple)) else [circuits]); return run0(self, circuits, *aa, **kk)
    AerSimulator.run = keep
    rec, ctx, calls = X.run_capture(suite, program, "original", seed, ninp, MEAS_B)
    AerSimulator.run = run0
    CACHE.mkdir(exist_ok=True)
    pickle.dump({"rec": rec, "ctx": ctx, "circ": held, "calls": calls}, open(_key(suite, program, seed), "wb"))
    return {"kind": "orig_capture", "suite": suite, "program": program, "seed": seed, "passed": rec["passed"], "contexts": len(ctx)}


EQCACHE = OUT / "eqcache"


def _equal_cached(X, program, version, fp, fm, sig, aa, kk):
    """Program equality depends only on the program versions and the call, not on the seed: computed once per call."""
    import hashlib, os
    f = EQCACHE / program / version / (hashlib.sha256(sig.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())["equal"]
    r = X.program_equal(fp, fm, aa, kk)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f".{os.getpid()}.tmp"); tmp.write_text(json.dumps({"sig": sig, "equal": r})); os.replace(tmp, f)
    return r


def job(a):
    import pickle, x2_capture as X, x2_harness as H
    from qiskit_aer.backends.aerbackend import AerBackend as AerSimulator
    kind, suite, program, version, seed, ninp = a
    t0 = time.time()
    if kind == "guard":
        rec = H.run_suite_a(program, "original", seed) if suite == "A" else H.run_suite_b(program, "original", seed, ninp, MEAS_B)
        rec.pop("input_seeds", None)
        return {"kind": kind, **rec}
    o = pickle.load(open(_key(suite, program, seed), "rb"))
    ctx_o, circ_o, calls_o = o["ctx"], o["circ"], o["calls"]
    held = []
    run0 = AerSimulator.run
    def keep(self, circuits, *aa, **kk):
        held.extend(circuits if isinstance(circuits, (list, tuple)) else [circuits]); return run0(self, circuits, *aa, **kk)
    AerSimulator.run = keep
    rec, ctx_m, calls_m = X.run_capture(suite, program, version, seed, ninp, MEAS_B); circ_m = held
    AerSimulator.run = run0

    H._paths()
    fp, fm = H.load_version(program, "original"), H.load_version(program, version)
    eq = {}
    for sig, aa, kk in calls_o:
        if sig not in eq: eq[sig] = _equal_cached(X, program, version, fp, fm, sig, aa, kk)
    aligned = len(ctx_o) == len(ctx_m) and all(c1["width"] == c2["width"] and c1["measured"] == c2["measured"] for c1, c2 in zip(ctx_o, ctx_m))
    out = {"kind": kind, "suite": suite, "program": program, "version": version, "seed": seed,
           "passed": rec["passed"], "detail": rec.get("tests") or rec.get("failed_properties"),
           "program_equal": eq, "contexts": len(ctx_o), "contexts_mutant": len(ctx_m), "aligned": aligned}
    if aligned:
        maxd, wit = 0.0, None
        for i, (c1, c2) in enumerate(zip(ctx_o, ctx_m)):
            d = float(np.max(np.abs(c1["dist"] - c2["dist"]))) if len(c1["dist"]) else 0.0
            maxd = max(maxd, d)
            if wit is None and d > EQ:
                n = len(c1["measured"])
                inst = (ordered_a if suite == "A" else ordered_b)(c1["dist"], c2["dist"], n)
                w = next((x for x in inst if x[2] > THETA + RES), None)
                if w is not None:
                    wit = {"context": i, "kind": w[0], "key": w[1], "d": float(w[2]), "ref": None if w[3] is None else float(w[3]),
                           "n_measured": n, "circ_o": _qpy(circ_o[i]), "circ_m": _qpy(circ_m[i]),
                           "ref_dist": c1["dist"].tolist() if w[0] in ("tvd", "hellinger", "kl") else None}
        out.update({"observation_equal": maxd <= EQ, "max_context_diff": maxd, "witness": wit})
    out["seconds"] = round(time.time() - t0, 2)
    return out


def _fresh(fn, a):                                   # one interpreter per job (module names differ between suites)
    p = subprocess.run([sys.executable, "-B", __file__, "--one", fn, json.dumps(a)], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"{fn}{a}: {p.stderr[-2000:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


if __name__ == "__main__" and sys.argv[1] == "--one":
    print("\n" + json.dumps({"orig_job": orig_job, "job": job}[sys.argv[2]](tuple(json.loads(sys.argv[3])))))
elif __name__ == "__main__":
    import x2_harness as H
    ninp = int(sys.argv[1]); workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    plan = [(s_, p) for p in H.PROGRAMS for s_ in "AB" if not (s_ == "A" and p not in H.SUITE_A)]
    done = set()
    path = OUT / "X2_NATIVE_RUNS.jsonl"
    if path.exists():
        for l in open(path):
            r = json.loads(l); done.add((r["kind"], r["suite"], r["program"], r.get("version", ""), r["seed"]))
    caps = [(s_, p, sd, ninp) for s_, p in plan for sd in MUT_SEEDS if not _key(s_, p, sd).exists()]
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex, open(OUT / "X2_ORIGINAL_CAPTURES.jsonl", "a") as f:
        for r in ex.map(lambda a: _fresh("orig_job", a), caps): f.write(json.dumps(r) + "\n"); f.flush()
    jobs = []
    for s_, p in plan:
        muts = sorted(f.stem.split(p + "_")[1] for f in (H.CS / p / "mutants").glob(f"{p}_*m*.py"))
        jobs += [("guard", s_, p, "original", sd, ninp) for sd in ORIG_SEEDS]
        jobs += [("pair", s_, p, v, sd, ninp) for v in muts for sd in MUT_SEEDS]
    jobs = [j for j in jobs if (j[0], j[1], j[2], j[3] if j[0] == "pair" else "original", j[4]) not in done]
    with open(path, "a") as f, ThreadPoolExecutor(workers) as ex:
        for r in ex.map(lambda a: _fresh("job", a), jobs):
            if r["kind"] == "guard": r["version"] = "original"
            f.write(json.dumps(r, separators=(",", ":")) + "\n"); f.flush()
    print("captures", len(caps), "jobs", len(jobs), "seconds", round(time.time() - t0, 1))
