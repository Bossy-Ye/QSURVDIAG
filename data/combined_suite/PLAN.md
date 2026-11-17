# Matched repair comparison: plan (frozen before its native runs)

Runner: `cmp_run.py`. Outputs: `CMP_CASES.csv`, `CMP_NATIVE_RUNS.csv`, `CMP_SUMMARY.json`. Before this commit
only the records listed below and the evidence inventory (`data/inventory/`) had been read; neither policy had been run on these cases at
the settings below.

## 1. Question and population

A conditional repair comparison: on survivors for which QSurvDiag proposes a suite-omission repair, does its
baseline-plus-witness suite (Policy D) differ from the existing combined suite (Policy S) in detection, original
validity, assertion count and cost? The population is selected by QSurvDiag's own candidate rule, so the result
says nothing about overall triage.

Eligible: every pre-confirmation suite-omission candidate with a stable baseline survival, whatever its later
certification status (certified, withheld, failed confirmation):
- corpus: the 187 stable candidates (`R2V_FINAL_CORPUS.csv`, `v2_candidate = CL4`, baseline 0 of 12), identified by
  their archived OB13 jobs in `R2V_NATIVE_JOBS_ARMS.jsonl`, which carry the original and mutant gate lists; 142 of
  them were certified and 45 withheld;
- MQT Bench: the documented 23 (`records/stage_c/C3_REPORTS.csv`, `v2_candidate = CL4`, baseline survived); 22
  certified, 1 withheld.
The 25 corpus candidates with a split baseline verdict are excluded, as in MQT Bench, because a split baseline
has no stable survival to repair. Counting units are reported separately: pairs, distinct originals (by content
hash for the corpus, subject for MQT Bench), and distinct repaired-suite designs.

## 2. Policies

Both use the declared QUTest profile on the joint Z counts of every qubit (every qubit is the output register in
both populations), original-centred analytic references rounded to 4 decimals, two-sided `~=` at theta = 0.05,
and the same native settings.

- Policy D: the baseline suite (one marginal per qubit) plus QSurvDiag's distinguishing assertion w*, the first
  instance outside the baseline whose ideal difference exceeds theta in the fixed witness order. The runner
  recomputes w* from the states and stops if it differs from the archived w*.
- Policy S: the combined suite as constructed in `e1_lib.suite_terms` (`S_BOTH`): one marginal per qubit plus the
  adjacent two-qubit Z products (q_i, q_i+1) for every i. No adjustment is made to it.
- Containment: D is contained in S exactly when w* is an adjacent two-qubit Z product; then, with identical
  assertion settings and counts, S cannot distinguish less than D on that case. Cases whose w* lies outside S
  (non-adjacent or higher-weight Z products, entropy, distances) are identified explicitly.
- Information access: D needs the original and mutant programs and a simulator (diagnosis); S needs the original
  program and a simulator (references only).

## 3. Native settings and validation streams

QUTest 0.1.0, ideal backend, N = 2,000 shots (the certification and MQT Bench validation setting), gate lists
lowered with the validated execution adapter. Independent validation streams not used by any earlier run:
mutant seeds 9042-9053, original seeds 10042-10053. Each policy's complete suite runs 12 times on each mutant.
Original validity runs once per unique (original, policy suite) at the original seeds and is linked to every case
that uses it; the links are not independent replications.

A policy's action is supported on a case when its suite kills the mutant in 12 of 12 runs and fails the original
in at most 1 of 12 (the MQT Bench validation rule), with no tool error. Ties and unfavorable results are reported.
No rerun, no change of settings or suites after results.

## 4. Measures and cost

Per case: kills of 12 per policy, original failures of 12 per linked suite, supported or not, assertions per
suite, whether w* is in S, the ideal prediction for S (whether an adjacent Z product exceeds theta), D's
certification status. Cost: diagnostic analysis time for D (mutant state, universe enumeration, witness selection),
reference generation time shared by both, native executions, shots and run time per policy. Both policies read one
set of counts per run, so a smaller suite saves no shots; the number of distinct original validations differs and
is counted.
