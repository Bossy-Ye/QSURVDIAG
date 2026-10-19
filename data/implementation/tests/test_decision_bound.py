"""Unit tests for the per-case delta = |d_a - theta| decision bound."""
import sys, math
from decision_bound import (bound_record, single_repetition_bound, EQ4_ROW,
                            NOT_COVERED, SUPPORTED, UNSUPPORTED, DEGENERATE)

C, FAIL = [], []
def check(n, got, want):
    ok = got == want
    C.append((n, "PASS" if ok else "FAIL", got, want))
    if not ok: FAIL.append(n)

REQUIRED = {"case_id","assertion_family","d_a","theta","delta","N","R","eq4_row",
            "single_repetition_bound","unanimity_failure_bound","bound_status",
            "supports_conclusion","omega_bits","alpha"}

# every required field is present
r = bound_record("c1", "marginal", d_a=0.50, theta=0.05, N=2000, R=12)
check("record carries every required field", REQUIRED <= set(r), True)

# delta is |d_a - theta|, not theta
check("delta uses the case margin", round(r["delta"], 10), 0.45)
r2 = bound_record("c2", "marginal", d_a=0.06, theta=0.05, N=2000, R=12)
check("a near-threshold case has a small delta", round(r2["delta"], 10), 0.01)
check("delta is NOT theta", r["delta"] == r["theta"], False)

# a wide margin is supported, a narrow one is not, at the same theta and N
check("wide margin supported", r["bound_status"], SUPPORTED)
check("narrow margin unsupported", r2["bound_status"], UNSUPPORTED)
check("supports_conclusion tracks the bound", (r["supports_conclusion"],
      r2["supports_conclusion"]), (True, False))

# the Round-0.5 error would have called both identical; prove they differ
check("two cases at one grid cell get different bounds",
      r["unanimity_failure_bound"] == r2["unanimity_failure_bound"], False)

# a case exactly at theta is degenerate, not silently supported
r3 = bound_record("c3", "observable", d_a=0.05, theta=0.05, N=8000, R=12)
check("d_a == theta is degenerate", r3["bound_status"], DEGENERATE)
check("degenerate does not support a conclusion", r3["supports_conclusion"], False)

# CORRECTION 7 restated this block.  Under the superseded row entropy fell outside
# the bound and this suite asserted NOT_COVERED_BY_EQ4 with a null bound.  Canonical
# Eq. (5) now gives entropy a bounded-difference row of its own, so the corrected
# expectations are: it is priced, it needs |Omega| like the distribution row, and it
# carries a real bound.  The record fields it must still carry are unchanged.
r4 = bound_record("c4", "entropy", d_a=0.9, theta=0.05, N=8000, R=12, omega_bits=4)
check("entropy is priced by Eq. (5)", r4["bound_status"] != NOT_COVERED, True)
check("entropy carries a bound", r4["unanimity_failure_bound"] is not None, True)
check("entropy support is determined", r4["supports_conclusion"] in (True, False), True)
check("entropy record still carries d_a, theta, delta",
      (r4["d_a"], r4["theta"], round(r4["delta"], 10)), (0.9, 0.05, 0.85))

# the four Eq. (5) rows are the ones canonical Section III states
check("marginal and probability share the Hoeffding row",
      EQ4_ROW["marginal"] == EQ4_ROW["probability"], True)
check("observable uses the +/-1 interval width",
      EQ4_ROW["observable"], "2*exp(-N d^2 / 2)")
# CORRECTION 7: the superseded assertion here was the L1 alphabet factor
# "2^|Omega| * exp(-N d^2 / 2)".  Canonical Eq. (5) prints the bounded-difference
# form, so the row identity is asserted against that instead.
check("distribution carries the bounded-difference form",
      EQ4_ROW["distribution"].startswith("exp(-N eps_D^2 / 2)"), True)
check("entropy carries the bounded-difference form",
      EQ4_ROW["entropy"].startswith("2*exp(-N eps_H^2"), True)

# both |Omega|-dependent rows refuse to compute without |Omega|
for _fam in ("distribution", "entropy"):
    try:
        single_repetition_bound(_fam, 2000, 0.4)
        check(f"{_fam} requires |Omega|", "no error", "ValueError")
    except ValueError:
        check(f"{_fam} requires |Omega|", "ValueError", "ValueError")

# alphabet size makes the distribution row strictly weaker
b4 = single_repetition_bound("distribution", 8000, 0.3, omega_bits=4)
b10 = single_repetition_bound("distribution", 8000, 0.3, omega_bits=10)
check("a larger outcome alphabet weakens the bound", b10 >= b4, True)

# N monotonicity at fixed delta
bs = [single_repetition_bound("marginal", N, 0.1) for N in (500, 2000, 8000)]
check("the bound tightens with N", bs == sorted(bs, reverse=True), True)

for n, v, got, want in C:
    print(f"{v}  {n:52s} got={got!r}")
print(f"\n{len(C)-len(FAIL)}/{len(C)} decision-bound checks passed")
sys.exit(1 if FAIL else 0)
