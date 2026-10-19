#!/usr/bin/env python3
"""Execution-integrity wrapper around the frozen original-program guard.

Defect this addresses. `b1_smin_runner.guard_smin` counts a repetition as a false
failure only when its verdict is KILLED. An original whose every repetition returns
UNSUPPORTED therefore scores zero false failures and is reported
ORIGINAL_GUARD_VALID. Run 001 hit exactly this: two subjects passed the guard
vacuously while no repetition had actually executed.

This is a TECHNICAL CORRECTNESS GUARD, not a new diagnostic rule. The scientific
definition of the guard is untouched: the OB02 false-failure criterion and its 0.10
threshold are the frozen ones, applied unchanged. This wrapper only refuses to let a
non-executing original be called valid.

Order is fixed:
  1. every repetition of the original must have a SUPPORTED execution status;
  2. only then is the existing guard_smin criterion applied.

Applied symmetrically to all nine external originals.
"""
GUARD_INTEGRITY_VERSION = "1.0.0"
SUPPORTED_STATUSES = ("KILLED", "SURVIVED")


def check_execution_support(subject, gates, n, assertions, reps, seed_base,
                            make_test, run_qutest, inner_shots):
    """Stage 1: every repetition must return a supported status."""
    statuses = []
    for r in range(reps):
        v, _ = run_qutest(make_test(gates, n, assertions, inner_shots, seed_base + r))
        statuses.append(v)
    unsupported = [i for i, v in enumerate(statuses) if v not in SUPPORTED_STATUSES]
    return {"subject": subject, "reps": reps, "statuses": statuses,
            "unsupported_reps": len(unsupported),
            "execution_support": "satisfied" if not unsupported else "failed",
            "first_unsupported_rep": unsupported[0] if unsupported else None}


def guarded(subject, support_record, frozen_guard_result):
    """Stage 2: combine. The frozen guard verdict stands only if stage 1 passed."""
    if support_record["execution_support"] != "satisfied":
        return {**frozen_guard_result,
                "execution_support": "failed",
                "unsupported_reps": support_record["unsupported_reps"],
                "cell_status": "INVALID_ORIGINAL_EXECUTION",
                "integrity_note": ("frozen guard reported "
                                   f"{frozen_guard_result.get('cell_status')} but no repetition "
                                   "executed; the frozen criterion was not reached")}
    return {**frozen_guard_result, "execution_support": "satisfied",
            "unsupported_reps": 0, "integrity_note": ""}
