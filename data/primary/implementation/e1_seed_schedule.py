"""Recovered historical repetition-seed schedules.  Not invented: every line below
is traced to an immutable historical source file and line.

  construction  seed(case, rep) = 6000 + rep,   rep in 0..11
      qutest_empirical_pilot_rerun/execute_rerun.py:31  BASE_SEED = 5000
      qutest_empirical_pilot_rerun/execute_rerun.py:61-64  screen(...) uses base_seed + rep
      final_empirical_study/execute_final.py:69  screen(mut, n, conv, BASE_SEED + 1000)
      -> mutant screening base = 5000 + 1000 = 6000; no per-case offset

  prospective   seed(case, rep) = 42 + rep,     rep in 0..11
      research_repair/phase5_validation/s3_certification/s3_engine.py:91
          QA.make_test(..., seed=QA.SEED + rep)
      cross_tool_stage/qutest/qutest_adapter.py:19  SEED = 42
      s3_certify.py:162 replay_instructions records "seeds {QA.SEED}..{QA.SEED+R-1}"

  assertion-reference seed (BOTH cohorts) = 42
      qutest_adapter.py:71-73 reference_marginal(..., seed=SEED) computes the
      reference from the ORIGINAL at seed 42.  This is the reference value, not a
      repetition seed, and it is identical in both cohorts.

  20260730 is NOT a native repetition seed.  It is the transpiler seed
      (s3_engine.py:201 seed_transpiler=20260730) and the QuCheck analysis seed
      (s3_qucheck.py:30).  Recorded here so it is not mistaken for one.
"""
REPS = 12
SCHEDULE = {"construction": 6000, "prospective": 42}
REFERENCE_SEED = 42
NON_REPETITION_SEEDS = {"transpiler": 20260730, "qucheck_analysis": 20260730}

PROVENANCE = {
 "construction": [
   "qutest_empirical_pilot_rerun/execute_rerun.py:31 BASE_SEED = 5000",
   "qutest_empirical_pilot_rerun/execute_rerun.py:61-64 screen() -> base_seed + rep",
   "final_empirical_study/execute_final.py:69 screen(mut, n, conv, BASE_SEED + 1000)"],
 "prospective": [
   "research_repair/phase5_validation/s3_certification/s3_engine.py:91 seed=QA.SEED + rep",
   "cross_tool_stage/qutest/qutest_adapter.py:19 SEED = 42",
   "research_repair/phase5_validation/s3_certification/s3_certify.py:162 replay_instructions"],
 "reference": ["cross_tool_stage/qutest/qutest_adapter.py:71-73 reference_marginal(seed=SEED)"],
}

def seed_for(population, mutant_id, rep):
    """(population, case, repetition) -> seed.  No per-case offset in either cohort."""
    assert 0 <= rep < REPS, rep
    return SCHEDULE[population] + rep
