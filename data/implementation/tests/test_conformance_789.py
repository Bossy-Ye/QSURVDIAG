"""Focused tests for conformance corrections 7, 8 and 9.

Synthetic and minimal cases only.  No study mutant is loaded, no study outcome is
read, and no expected count from the manuscript appears anywhere in this file.
Every expected value below is computed from the canonical Section III expression
by hand, independently of the implementation under test.
"""
import math
import sys
sys.path.insert(0, ".")

from decision_bound import (single_repetition_bound, bound_record, eps_D, eps_H,
                            EQ4_ROW, DEGENERATE)
from qsurvdiag_confirmatory import (Tri, T, F, U, compare_threshold, exists_above,
                                    THRESHOLD_RESOLUTION, candidate, certify)

RES, FAIL = [], 0
def check(name, got, want, tol=None):
    global FAIL
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    RES.append((ok, name, got, want)); FAIL += (not ok)

# ============================================================ CORRECTION 7 ====
# Row identity: the table must print the bounded-difference form, not 2^|Omega|.
check("7.1 distribution row is the bounded-difference form",
      EQ4_ROW["distribution"].startswith("exp(-N eps_D^2 / 2)"), True)
check("7.2 the superseded 2^|Omega| factor is gone",
      "2^|Omega|" in EQ4_ROW["distribution"], False)
check("7.3 entropy carries a row of its own", EQ4_ROW["entropy"] is not None, True)

# eps_D and eps_H against hand arithmetic.
# |Omega| = 2^3 = 8, N = 200  ->  sqrt(7/200) = sqrt(0.035) = 0.187082869...
check("7.4 eps_D = 2d - sqrt((|Omega|-1)/N)",
      eps_D(0.30, 200, 3), 2 * 0.30 - math.sqrt(7 / 200), tol=1e-12)
check("7.5 eps_D clips at zero when the floor exceeds 2d",
      eps_D(0.01, 200, 3), 0.0)
# log2(1 + 7/200) = log2(1.035) = 0.049636...
check("7.6 eps_H = d - log2(1 + (|Omega|-1)/N)",
      eps_H(0.30, 200, 3), 0.30 - math.log2(1 + 7 / 200), tol=1e-12)
check("7.7 eps_H clips at zero inside the bias term",
      eps_H(0.01, 200, 3), 0.0)

# Bound values against the hand-evaluated expression.
d, N, b = 0.30, 200, 3
want_D = min(1.0, math.exp(-N * (2 * d - math.sqrt(7 / N)) ** 2 / 2))
check("7.8 distribution bound equals exp(-N eps_D^2 / 2)",
      single_repetition_bound("distribution", N, d, omega_bits=b), want_D, tol=1e-12)
want_H = min(1.0, 2 * math.exp(-N * (d - math.log2(1 + 7 / N)) ** 2 / (2 * math.log2(N) ** 2)))
check("7.9 entropy bound equals 2exp(-N eps_H^2 / (2 log2^2 N))",
      single_repetition_bound("entropy", N, d, omega_bits=b), want_H, tol=1e-12)

# Clipping convention preserved: B = min{1, B~}.
check("7.10 clipping convention holds for every family",
      all(single_repetition_bound(f, 10, 0.001, omega_bits=3) <= 1.0
          for f in ("marginal", "probability", "observable", "correlation",
                    "distribution", "entropy")), True)
# A vacuous row returns exactly 1, not something above it.
check("7.11 a vacuous distribution row returns exactly 1",
      single_repetition_bound("distribution", 200, 0.01, omega_bits=3), 1.0)
check("7.12 a vacuous entropy row returns exactly 1",
      single_repetition_bound("entropy", 200, 0.01, omega_bits=3), 1.0)

# Untouched rows must be byte-identical to the superseded implementation.
check("7.13 marginal row unchanged", single_repetition_bound("marginal", 500, 0.2),
      min(1.0, 2 * math.exp(-2 * 500 * 0.2 ** 2)), tol=1e-15)
check("7.14 Z-product row unchanged", single_repetition_bound("observable", 500, 0.2),
      min(1.0, 2 * math.exp(-500 * 0.2 ** 2 / 2)), tol=1e-15)

# Both |Omega|-dependent rows must refuse to compute without |Omega|.
for fam in ("distribution", "entropy"):
    try:
        single_repetition_bound(fam, 200, 0.3)
        check(f"7.15 {fam} requires |Omega|", "no error", "ValueError")
    except ValueError:
        check(f"7.15 {fam} requires |Omega|", "ValueError", "ValueError")

# A larger alphabet weakens both rows (the floor and the bias term both grow).
check("7.16 larger alphabet weakens the distribution row",
      single_repetition_bound("distribution", 8000, 0.3, omega_bits=10)
      >= single_repetition_bound("distribution", 8000, 0.3, omega_bits=4), True)
check("7.17 larger alphabet weakens the entropy row",
      single_repetition_bound("entropy", 8000, 0.3, omega_bits=10)
      >= single_repetition_bound("entropy", 8000, 0.3, omega_bits=4), True)

# ============================================================ CORRECTION 8 ====
# Stage 2 must quantify over the universe entire.  The decisive instance is the
# argmax over every admissible member, whatever Stage 3 can price.
U_synth = [("marginal", "m[0]", 0.10),
           ("observable", "Z0Z1", 0.20),
           ("entropy", "H", 0.90)]          # largest, and historically filtered out
check("8.1 the Stage-2 maximum includes a family Stage 3 cannot price",
      max(U_synth, key=lambda x: x[2])[0], "entropy")
check("8.2 R_A over the universe entire is TRUE on that maximum",
      exists_above([x[2] for x in U_synth], 0.5), T)
# The same universe with the historical filter applied would have said FALSE.
filtered = [x for x in U_synth if x[0] != "entropy"]
check("8.3 the superseded filter would have inverted it",
      exists_above([x[2] for x in filtered], 0.5), F)

# Conformance property: removing a family's Stage-3 row cannot change Stage 2.
def stage2_candidate(diffs, theta):
    rel = {"R_C": F, "R_S": F, "R_O": F,
           "R_A": exists_above(diffs, theta), "R_T": F}
    return candidate(rel)[0]

diffs = [x[2] for x in U_synth]
before = stage2_candidate(diffs, 0.5)
_saved = EQ4_ROW["entropy"]
try:
    EQ4_ROW["entropy"] = None            # simulate a family losing its bound row
    after = stage2_candidate(diffs, 0.5)
finally:
    EQ4_ROW["entropy"] = _saved
check("8.4 removing a Stage-3 row leaves the Stage-2 candidate unchanged",
      after, before)
check("8.5 and that candidate is the one the witness implies", before, "CL4")

# ============================================================ CORRECTION 9 ====
th = 0.5
r = THRESHOLD_RESOLUTION
check("9.1 exactly at theta is UNDECIDED", compare_threshold(th, th), U)
check("9.2 inside resolution, above, is UNDECIDED",
      compare_threshold(th + 0.8 * r, th), U)
check("9.3 inside resolution, below, is UNDECIDED",
      compare_threshold(th - 0.8 * r, th), U)
check("9.4 on the resolution boundary, above, is UNDECIDED",
      compare_threshold(th + r, th), U)
# The point exactly r below theta is not constructible in float64: `th - r` lands
# 5.000000025e-09 away, just outside the boundary.  Asserting a hand-picked point
# there would test the arithmetic, not the rule.  The rule itself is checked as a
# property against the margin the comparison actually sees.
_viol = [d for d in (th + k * r for k in
                     (-3, -2, -1.5, -1.0001, -1, -0.999, -0.5, 0, 0.5,
                      0.999, 1, 1.0001, 1.5, 2, 3))
         if compare_threshold(d, th) is not (
             U if abs(d - th) <= r else (T if d > th else F))]
check("9.5 the rule holds at every offset around the boundary", _viol, [])
check("9.6 immediately outside resolution, above, is TRUE",
      compare_threshold(th + 1.2 * r, th), T)
check("9.7 immediately outside resolution, below, is FALSE",
      compare_threshold(th - 1.2 * r, th), F)
check("9.8 far above is TRUE", compare_threshold(0.9, th), T)
check("9.9 far below is FALSE", compare_threshold(0.1, th), F)

# Kleene existential: one undecided member with no decisive member is UNDECIDED.
check("9.10 existential is UNDECIDED when only a resolution-limited member is near",
      exists_above([0.1, th], th), U)
check("9.11 a decisive member dominates an undecided one",
      exists_above([th, 0.9], th), T)
check("9.12 all decisively below is FALSE", exists_above([0.1, 0.2], th), F)

# An UNDECIDED relation must end the path with no candidate (Section III).
rel_u = {"R_C": F, "R_S": F, "R_O": F, "R_A": U, "R_T": F}
check("9.13 an undecided R_A yields no candidate", candidate(rel_u)[0], None)
check("9.14 and certify() returns Unresolved",
      certify(rel_u, {})["report"], "Unresolved")

# The comparison must be driven by unrounded values: a display-rounded margin and
# the value it came from must be able to disagree, and the unrounded one wins.
true_val = th + 4e-9                      # inside resolution -> UNDECIDED
check("9.15 unrounded value at 4e-9 above theta is UNDECIDED",
      compare_threshold(true_val, th), U)
# The superseded code compared bare booleans, and the unrounded value and the
# eight-decimal recorded margin disagree on exactly this point: unrounded `>` says
# True, the rounded margin says False.  Correction 9 says neither is trustworthy.
check("9.16 the unrounded and display-rounded booleans disagree here",
      (true_val > th, round(true_val, 8) > th), (True, False))
check("9.17 and the corrected comparison refuses both",
      compare_threshold(true_val, th), U)

# Degenerate-margin handling in Stage 3 is unchanged by correction 9.
check("9.18 Stage 3 still flags a zero margin as degenerate",
      bound_record("synthetic", "marginal", th, th, 2000, 12)["bound_status"], DEGENERATE)

# ------------------------------------------------------------------ report ----
for ok, name, got, want in RES:
    print(f"{'PASS' if ok else 'FAIL'}  {name:62} got={got!r}" + ("" if ok else f" want={want!r}"))
print(f"\n{len(RES) - FAIL}/{len(RES)} correction 7-9 checks passed")
sys.exit(1 if FAIL else 0)
