"""Finite-shot decision bound, Eq. (4), evaluated per case.

Round 0.75 correction.  The grid analysis of Round 0.5 evaluated Eq. (4) at
delta = theta, which is a property of the grid and not of any case.  Section III
defines the analytic margin as

    delta = | d_a - theta |

for the assertion, case and configuration actually being decided.  Every record
this module emits therefore carries d_a, theta, delta, the family, N, R, the
applicable bound, and whether that bound supports the finite-shot conclusion the
report needs.

Eq. (5) rows, verbatim from canonical Section III, eq:conc:
    marginal, probability      B~ = 2 exp(-2 N delta^2)
    Z product                  B~ = 2 exp(-N delta^2 / 2)
    distribution               B~ = exp(-N eps_D^2 / 2)
    entropy                    B~ = 2 exp(-N eps_H^2 / (2 log2(N)^2))
with
    eps_D = 2 delta - sqrt((|Omega| - 1) / N)
    eps_H = delta - log2(1 + (|Omega| - 1) / N)
"each read as zero where it is not positive", and the clipping convention
    B_a(N, delta) = min{1, B~_a(N, delta)}
preserved unchanged.  Agreement across R repetitions follows with probability at
least max{0, 1 - R B_a}.

CORRECTION 7 (conformance category 7).  The superseded row computed
2^|Omega| exp(-N delta^2 / 2) for the distribution family and compared a
total-variation margin against an L1-form exponent.  The row above is the
bounded-difference (McDiarmid) form the canonical section prints.  CORRECTION 8:
the entropy family now carries a row of its own, so no family lacks one; Stage 2
must not consult this table at all -- see qsurvdiag_confirmatory.exists_above.
"""
import math

EQ4_ROW = {
    "marginal":     "2*exp(-2N d^2)",
    "probability":  "2*exp(-2N d^2)",
    "observable":   "2*exp(-N d^2 / 2)",     # Pauli-Z product
    "correlation":  "2*exp(-N d^2 / 2)",     # Pauli-Z product of two qubits
    "distribution": "exp(-N eps_D^2 / 2), eps_D = 2d - sqrt((|Omega|-1)/N)",
    "entropy":      "2*exp(-N eps_H^2 / (2 log2(N)^2)), "
                    "eps_H = d - log2(1 + (|Omega|-1)/N)",
}
NOT_COVERED = "NOT_COVERED_BY_EQ4"
SUPPORTED, UNSUPPORTED, DEGENERATE = "SUPPORTED", "UNSUPPORTED", "DEGENERATE_MARGIN"

# the unanimity failure probability a report may tolerate over R repetitions
DEFAULT_ALPHA = 0.05


def _alphabet(omega_bits):
    """|Omega| from the qubit count the caller records."""
    return 2 ** omega_bits


def eps_D(delta, N, omega_bits):
    """Usable total-variation deviation: 2 delta minus the sampling floor.

    Section III: eps_D = 2 delta - sqrt((|Omega| - 1) / N), read as zero where it
    is not positive.
    """
    e = 2.0 * delta - math.sqrt((_alphabet(omega_bits) - 1) / N)
    return e if e > 0.0 else 0.0


def eps_H(delta, N, omega_bits):
    """Usable entropy deviation: delta minus the Paninski bias term.

    Section III: eps_H = delta - log2(1 + (|Omega| - 1) / N), read as zero where it
    is not positive.
    """
    e = delta - math.log2(1.0 + (_alphabet(omega_bits) - 1) / N)
    return e if e > 0.0 else 0.0


def single_repetition_bound(family, N, delta, omega_bits=None):
    """B_a(N, delta) for one repetition, or None when Eq. (4) does not apply."""
    row = EQ4_ROW.get(family)
    if row is None:
        return None
    if delta <= 0:
        return 1.0
    if family in ("marginal", "probability"):
        return min(1.0, 2.0 * math.exp(-2.0 * N * delta ** 2))
    if family in ("observable", "correlation"):
        return min(1.0, 2.0 * math.exp(-N * delta ** 2 / 2.0))
    if family == "distribution":
        if omega_bits is None:
            raise ValueError("the distribution row needs |Omega|; pass omega_bits = n")
        eps = eps_D(delta, N, omega_bits)
        return min(1.0, math.exp(-N * eps ** 2 / 2.0))
    if family == "entropy":
        if omega_bits is None:
            raise ValueError("the entropy row needs |Omega|; pass omega_bits = n")
        eps = eps_H(delta, N, omega_bits)
        lg = math.log2(N)
        if lg <= 0.0:                       # N = 1 carries no repetition structure
            return 1.0
        return min(1.0, 2.0 * math.exp(-N * eps ** 2 / (2.0 * lg ** 2)))
    raise ValueError(family)


def bound_record(case_id, family, d_a, theta, N, R, omega_bits=None,
                 alpha=DEFAULT_ALPHA):
    """The full per-case decision-bound record the protocol requires."""
    delta = abs(d_a - theta)
    B = single_repetition_bound(family, N, delta, omega_bits)
    rec = {"case_id": case_id, "assertion_family": family,
           "d_a": d_a, "theta": theta, "delta": delta, "N": N, "R": R,
           "omega_bits": omega_bits,
           "eq4_row": EQ4_ROW.get(family),
           "single_repetition_bound": B,
           "unanimity_failure_bound": None if B is None else min(1.0, R * B),
           "alpha": alpha}
    if B is None:
        rec["bound_status"] = NOT_COVERED
        rec["supports_conclusion"] = None
    elif delta == 0.0:
        rec["bound_status"] = DEGENERATE
        rec["supports_conclusion"] = False
    else:
        ok = rec["unanimity_failure_bound"] <= alpha
        rec["bound_status"] = SUPPORTED if ok else UNSUPPORTED
        rec["supports_conclusion"] = ok
    return rec


def required_N(family, delta, R, alpha=DEFAULT_ALPHA, omega_bits=None):
    """Smallest N in the frozen grid whose bound supports the conclusion."""
    for N in (500, 2000, 8000):
        r = bound_record("probe", family, delta + 0.0, 0.0, N, R, omega_bits, alpha)
        if r["supports_conclusion"]:
            return N
    return None
