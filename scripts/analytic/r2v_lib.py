import sys as _sys; _sys.dont_write_bytecode = True   # keep the package free of interpreter caches
# Copy of data/prospective/mqt_bench/frozen_deps/r2v_lib.py; only path handling differs.
# Copied by scripts/reproduce_analytic.py next to the archived producers r2v_stats.py, r2v_bound.py, r2v_table_x.py, r2v_numbers.py.
"""Shared implementation of V2_SPECIFICATION.md (frozen; hash in V2_SPECIFICATION.sha256).

Every function below implements one numbered clause of the specification; the clause is
named in the docstring. Frozen study code is imported read-only.
"""
import hashlib, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.environ["R2V_PA"]   # root of the input tree that scripts/reproduce_analytic.py assembles from package files
QSD = os.environ["QSD_ROOT"]
sys.path.insert(0, PA + "github/code/qsurvdiag")
sys.path.insert(0, PA + "manuscript/tse/protocol/impl")
# the study's copy of the frozen adapter (byte-identical body) resolves the QUTest binary of
# the pinned .venv-qutest-audit environment, as every recorded arm did
sys.path.insert(0, QSD + "/cross_tool_stage/qutest")
from qsurvdiag_confirmatory import compare_threshold, exists_above, certify, T, F, U, THRESHOLD_RESOLUTION
from qutest_execution_adapter import adapt
from serialization_adapter import emit_name
import qutest_adapter as QA

SPEC_SHA = "6829f1bad8203b434ddf27a4336e514b15a7e8d72a371c3eef4ebff499deb1d3"
THETA, LO, HI = 0.05, 1e-10, 1e-8
N_SHOTS, R, GUARD_REPS = 2000, 12, 3
MUT_SEEDS = [42 + r for r in range(R)]
GUARD_SEEDS = [42 + r for r in range(GUARD_REPS)]

def spec_unchanged():
    """OB19 (spec 6): this specification unchanged since its hash."""
    return hashlib.sha256(open(os.path.join(HERE, "V2_SPECIFICATION.md"), "rb").read()).hexdigest() == SPEC_SHA

def eq_decision(m):
    """Spec 3: true below 1e-10, false above 1e-8, undecided in between."""
    return T if m < LO else (F if m > HI else U)

def tri_s(v): return {T: "true", F: "false", U: "undecided"}[v]

# ---------------------------------------------------------------- distributions
def marg(p, n, q):
    idx = np.arange(len(p)); return float(p[((idx >> q) & 1) == 1].sum())
def zexp(p, n, mask):
    idx = np.arange(len(p)); par = np.zeros(len(p), dtype=int)
    for q in range(n):
        if (mask >> q) & 1: par ^= (idx >> q) & 1
    return float((p * np.where(par == 1, -1.0, 1.0)).sum())
def shannon_bits(p):
    q = p[p > 0]; return float(-(q * np.log2(q)).sum())
def tvd(pm, pp): return float(0.5 * np.abs(pm - pp).sum())
def hellinger(pm, pp): return float(np.sqrt(0.5 * np.sum((np.sqrt(pm) - np.sqrt(pp)) ** 2)))
def kl(pm, pp):
    eps = 1e-12; a, b = np.clip(pm, eps, None), np.clip(pp, eps, None)
    return float(np.sum(a * np.log(a / b)))

def ordered_universe(pp, pm, n):
    """Spec 2.5 and 5. Returns (ordered, all_diffs).
    ordered: the witness-order instances as dicts (kind, key, d, ref), in spec-5 order.
    all_diffs: every one of the 2^{n+1}+n+3 instances of U(P) (weight-1 Z products included)."""
    ordered, alld = [], []
    for q in range(n):
        a, b = marg(pp, n, q), marg(pm, n, q)
        ordered.append({"kind": "marginal", "key": q, "d": abs(a - b), "ref": a}); alld.append(abs(a - b))
    pairs = sorted(((i, j) for i in range(n) for j in range(i + 1, n)), key=lambda t: (t[1] - t[0], t[0], t[1]))
    zcache = {}
    def zd(m):
        if m not in zcache:
            a, b = zexp(pp, n, m), zexp(pm, n, m); zcache[m] = (abs(a - b), a)
        return zcache[m]
    for i, j in pairs:
        m = (1 << i) | (1 << j); d, a = zd(m)
        ordered.append({"kind": "zmask", "key": m, "d": d, "ref": a})
    for m in sorted((m for m in range(1, 2 ** n) if bin(m).count("1") >= 3), key=lambda m: (bin(m).count("1"), m)):
        d, a = zd(m); ordered.append({"kind": "zmask", "key": m, "d": d, "ref": a})
    for m in range(1, 2 ** n):                       # every Z product of U(P), weight-1 included
        alld.append(zd(m)[0])
    dp = np.abs(pp - pm)
    for x in range(2 ** n):
        ordered.append({"kind": "prob", "key": x, "d": float(dp[x]), "ref": float(pp[x])})
    alld.extend(dp.tolist())
    ha, hb = shannon_bits(pp), shannon_bits(pm)
    for kind, d, ref in (("entropy", abs(ha - hb), ha), ("tvd", tvd(pm, pp), None),
                         ("hellinger", hellinger(pm, pp), None), ("kl", kl(pm, pp), None)):
        ordered.append({"kind": kind, "key": None, "d": d, "ref": ref}); alld.append(d)
    assert len(alld) == 2 ** (n + 1) + n + 3
    return ordered, alld

def suite_keys_marginals(qs): return {("marginal", int(q)) for q in qs}

def select(ordered, suite_keys, want):
    """Spec 5: first instance in order, absent from the realized suite, whose
    compare_threshold(d, theta) is `want` (T for the witness w*, F for the control c*)."""
    for inst in ordered:
        if (inst["kind"], inst["key"]) in suite_keys: continue
        if compare_threshold(inst["d"], THETA) is want: return inst
    return None

def pragmas(inst, n, pp):
    """Spec 9: QUTest 0.1.0 pragma lines for one instance, analytic reference from the
    original, rounded as the adapter rounds (4 decimals)."""
    k, key = inst["kind"], inst["key"]
    if k == "marginal":
        return [QA.marginal_assertion(key, round(inst["ref"], 4))]
    if k == "zmask":
        zs = " ".join(f"Z{i}" for i in range(n) if (key >> i) & 1)
        return [f'//% expect observable "{zs}" ~= {round(inst["ref"], 4)} atol={QA.ATOL}']
    if k == "prob":
        return [f'//% expect probability "{format(key, "0%db" % n)}" ~= {round(inst["ref"], 4)} atol={QA.ATOL}']
    if k == "entropy":
        return [f'//% expect entropy ~= {round(inst["ref"], 4)} atol={QA.ATOL}']
    ref = {format(x, "0%db" % n): float(pp[x]) for x in range(2 ** n) if pp[x] > 1e-15}
    metric = {"tvd": "total_variation_distance", "hellinger": "hellinger", "kl": "kl"}[k]
    return ["//% expect distribution ref " + json.dumps(ref, separators=(",", ":")),
            f"//% expect distribution {metric} <= {THETA}"]

def to_text(gates):
    """Spec 9: the validated lowering and name map, as in the recorded arms."""
    return [{**x, "gate": emit_name(x["gate"])} for x in adapt(gates)]

def native_check(mut_gates, orig_gates, n, lines):
    """Spec 6 (OB13, OB15) and 9: the assertion alone, guard on the original (3 seeds)
    then the mutant (12 seeds). Returns kills, guard fails and unsupported counts."""
    g = [QA.run_qutest(QA.make_test(to_text(orig_gates), n, lines, N_SHOTS, s))[0] for s in GUARD_SEEDS]
    m = [QA.run_qutest(QA.make_test(to_text(mut_gates), n, lines, N_SHOTS, s))[0] for s in MUT_SEEDS]
    return {"guard_fails": sum(v == "KILLED" for v in g), "guard_unsupported": sum(v == "UNSUPPORTED" for v in g),
            "kills": sum(v == "KILLED" for v in m), "unsupported": sum(v == "UNSUPPORTED" for v in m),
            "guard_verdicts": ";".join(g), "verdicts": ";".join(m)}

def ob13_status(res):
    """Spec 6: void guard or error -> unknown; 12/12 kills with a clean guard -> satisfied."""
    if res is None: return "pending"
    if res["guard_unsupported"] or res["unsupported"]: return "unknown"
    if res["guard_fails"]: return "unknown"
    return "satisfied" if res["kills"] == R else "failed"

def ob15_status(res):
    """Spec 6: the control must kill fewer than 12 of 12 (frozen S3 criterion)."""
    if res is None: return "pending"
    if res["guard_unsupported"] or res["unsupported"] or res["guard_fails"]: return "unknown"
    return "failed" if res["kills"] == R else "satisfied"

def grid_interval(d_by_theta):
    """Spec 6 (OB16): the recorded grid tolerances at which the candidate holds."""
    return ";".join(t for t, ok in d_by_theta if ok)

def v2_report(rel, ev, kills, reps):
    """Spec 4: the frozen certify() over the v2 relations and evidence record."""
    from qsurvdiag_confirmatory import empirical
    return certify(rel, ev, empirical_verdict=empirical(kills, reps))
