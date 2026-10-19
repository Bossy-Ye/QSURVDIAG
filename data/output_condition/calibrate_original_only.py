"""Original-only calibration for the corrected output-condition suites (no mutant information).
Monte Carlo of the sampled statistic each corrected assertion computes on the ORIGINAL's ideal distribution,
at N = 8,000 shots, to obtain the per-run and 12-run false-failure probabilities at tolerance 0.05."""
import numpy as np
rng = np.random.default_rng(20261017); N, R, TH, T = 8000, 12, 0.05, 20000
def run(name, p, stat):
    x = rng.multinomial(N, p, size=T) / N; s = np.array([stat(r) for r in x]); f = (s > TH).mean()
    print(f"{name:34s} mean {s.mean():.4f}  p95 {np.quantile(s, .95):.4f}  per-run fail {f:.4f}  P(any of {R} fails) {1-(1-f)**R:.4f}")
for n in (4, 5, 6):
    u = np.full(2 ** n, 1 / 2 ** n)
    run(f"QFT n={n}: TV to uniform", u, lambda r: 0.5 * np.abs(r - u).sum())
    run(f"QFT n={n}: Hellinger to uniform", u, lambda r: np.sqrt(0.5 * np.sum((np.sqrt(r) - np.sqrt(u)) ** 2)))
w = np.zeros(16); w[[1, 2, 4, 8]] = 0.25
run("W n=4: TV to weight-one", w, lambda r: 0.5 * np.abs(r - w).sum())
# Simon output register (q0, q1) distribution {00: .5, 11: .5}; Z0Z1 = P(00)+P(11)-P(01)-P(10)
s = np.array([0.5, 0, 0, 0.5])
run("Simon: |<Z0Z1> - 1|", s, lambda r: abs((r[0] + r[3] - r[1] - r[2]) - 1))
run("Simon: |p1(q0) - 0.5|", s, lambda r: abs(r[1] + r[3] - 0.5))
