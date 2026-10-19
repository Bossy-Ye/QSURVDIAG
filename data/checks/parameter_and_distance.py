"""Deterministic checks against the pinned QUTest 0.1.0 evaluators and the study's difference functions.

Usage: python -I parameter_and_distance.py <path to scripts/analytic/r2v_lib.py>
No sampling: counts are constructed so that the empirical distribution equals the stated ideal one.
"""
import ast, sys
import numpy as np
from qutest.models import Pragma, PragmaKind
from qutest.assertions.marginal import evaluate_marginal
from qutest.assertions.distribution import _compute_metric
from qutest.assertions.entropy import evaluate_entropy


# the study's difference functions, extracted verbatim from r2v_lib.py (the module itself needs the study tree)
src = open(sys.argv[1]).read(); tree = ast.parse(src)
ns = {"np": np}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in ("marg", "tvd", "hellinger", "kl", "shannon_bits"):
        exec(compile(ast.Module([node], []), "r2v_lib", "exec"), ns)

def counts_1q(p1, total=10000):
    return {"1": round(p1 * total), "0": total - round(p1 * total)}

print("parameter policy, marginal on one qubit; theta = 0.05")
orig, mut = counts_1q(0.50), counts_1q(0.52)
for ref, label in ((0.50, "original-centred reference (the study's universe)"), (0.46, "off-centre reference admitted by the QUTest grammar")):
    pr = Pragma(kind=PragmaKind.EXPECT_MARGINAL, raw="", params={"register": "m", "index": 0, "outcome": 1, "value": ref, "atol": 0.05})
    vo, vm = (evaluate_marginal(pr, orig).status.value == "pass"), (evaluate_marginal(pr, mut).status.value == "pass")
    print(f"  ref {ref:.2f} ({label}): original {'passes' if vo else 'fails'}, mutant {'passes' if vm else 'fails'}")
d = abs(ns["marg"](np.array([0.5, 0.5]), 1, 0) - ns["marg"](np.array([0.48, 0.52]), 1, 0))
print(f"  study difference d = {d:.2f} <= theta, so the study's universe holds no distinguishing instance")

print("\ndistance conventions at support-zero and small-probability boundaries")
cases = {
    "mutant has support where the original has none": (np.array([0.5, 0.5, 0.0, 0.0]), np.array([0.5, 0.49, 0.01, 0.0])),
    "original has support where the mutant has none": (np.array([0.5, 0.49, 0.01, 0.0]), np.array([0.5, 0.5, 0.0, 0.0])),
    "difference at the 1e-10 equality margin": (np.array([0.5, 0.5 - 1e-10, 1e-10, 0.0]), np.array([0.5, 0.5, 0.0, 0.0])),
}
for name, (pp, pm) in cases.items():
    for metric, f in (("total_variation_distance", "tvd"), ("hellinger", "hellinger"), ("kl", "kl")):
        qut = _compute_metric(metric, pm, pp)          # QUTest: p = measured (mutant), q = reference (original)
        study = ns[f](pm, pp)                           # study: distance of p_M from p_P
        assert abs(qut - study) < 1e-15, (name, metric, qut, study)
    print(f"  {name}: TV {ns['tvd'](pm, pp):.3g}, Hellinger {ns['hellinger'](pm, pp):.3g}, KL(M||P) {ns['kl'](pm, pp):.3g}, "
          f"|dH| {abs(ns['shannon_bits'](pp) - ns['shannon_bits'](pm)):.3g}  (QUTest and study agree)")
print("  KL direction: QUTest computes D(measured || reference); the study computes D(p_M || p_P), the same direction.")
print("  A KL instance is not symmetric: D(p_P || p_M) would differ, but no admitted instance uses that direction.")
