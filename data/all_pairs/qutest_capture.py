"""Run one QUTest test file twice: through the pinned qutest CLI (the native verdict of record, as in every earlier
experiment) and through QUTest's own discover_tests/run_test in this process, with the ideal backend's run() wrapped
so that the counts of that execution are kept. Nothing in QUTest's evaluation is replaced: the wrapper only records
the counts object QUTest itself receives. Returns the CLI verdict, the in-process status, every assertion's status
and measured value, and the histogram.
"""
import subprocess, tempfile, time
from pathlib import Path
import qutest.runner as _R
from qutest.discovery import discover_tests
from qutest.models import AssertionStatus, TestStatus

_CAP = []
_orig_resolve = _R.resolve_backend
def _resolve(name, seed=None):
    be = _orig_resolve(name, seed); run0 = be.run
    def run(*a, **k):
        job = run0(*a, **k); _CAP.append({kk.replace(" ", ""): v for kk, v in job.result().get_counts().items()}); return job
    be.run = run
    return be
_R.resolve_backend = _resolve

def cli_verdict(qutest_bin, path):
    r = subprocess.run([qutest_bin, "run", path], capture_output=True, text=True, timeout=600)
    out = (r.stdout + r.stderr).strip(); summ = out.splitlines()[-1] if out else ""
    if "error" in summ: return "UNSUPPORTED"
    if "failed" in summ: return "KILLED"
    if "passed" in summ: return "SURVIVED"
    return "UNSUPPORTED"

def run_both(qutest_bin, text):
    with tempfile.NamedTemporaryFile("w", suffix=".qasm", delete=False) as f:
        f.write(text); p = f.name
    try:
        t0 = time.perf_counter(); cli = cli_verdict(qutest_bin, p); t_cli = time.perf_counter() - t0
        tcs = discover_tests(p); assert len(tcs) == 1
        _CAP.clear(); t1 = time.perf_counter(); res = _R.run_test(tcs[0]); t_in = time.perf_counter() - t1
        assert len(_CAP) == 1, len(_CAP)
        st = {TestStatus.PASS: "SURVIVED", TestStatus.FAIL: "KILLED", TestStatus.ERROR: "UNSUPPORTED"}[res.status]
        per = [(a.status.value if hasattr(a.status, "value") else str(a.status), a.actual) for a in res.assertions]
        return {"cli": cli, "inproc": st, "assertions": per, "counts": dict(_CAP[0]), "cli_seconds": round(t_cli, 3), "inproc_seconds": round(t_in, 4)}
    finally:
        Path(p).unlink(missing_ok=True)

def rescore(tc, counts):
    """Re-evaluate a test's result assertions on a recorded histogram with QUTest's own evaluate_* functions, in the
    dispatch order of qutest.runner.run_test (the assertion kinds this study uses). Returns (statuses, seconds)."""
    from qutest.models import PragmaKind as K
    from qutest.assertions.marginal import evaluate_marginal
    from qutest.assertions.observable import evaluate_observable
    from qutest.assertions.entropy import evaluate_entropy
    from qutest.assertions.distribution import evaluate_distribution
    from qutest.assertions.probability import evaluate_probability
    ref = next((p.params["ref"] for p in tc.result_pragmas if p.kind == K.EXPECT_DISTRIBUTION_REF), None)
    t0 = time.perf_counter(); out = []
    for p in tc.result_pragmas:
        if p.kind == K.EXPECT_MARGINAL: a = evaluate_marginal(p, counts)
        elif p.kind == K.EXPECT_OBSERVABLE: a = evaluate_observable(p, counts)
        elif p.kind == K.EXPECT_ENTROPY: a = evaluate_entropy(p, counts)
        elif p.kind == K.EXPECT_DISTRIBUTION: a = evaluate_distribution(p, counts, ref)
        elif p.kind == K.EXPECT_PROBABILITY: a = evaluate_probability(p, counts)
        elif p.kind == K.EXPECT_DISTRIBUTION_REF: continue
        else: raise ValueError(f"assertion kind not used in this study: {p.kind}")
        out.append({"pass": "P", "fail": "F", "error": "E"}[a.status.value])
    return "".join(out), time.perf_counter() - t0
