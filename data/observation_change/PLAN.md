# X1. Changing the observation: plan (fixed before its native runs)

## 0. Selection history

Not blind. The 35 observation limitations of the 20 circuits and the simulated measurement comparison (every qubit
in the X, Y and Z bases separates all 35) are known. A feasibility run before this plan executed, on all 35 pairs, one
all-X test per program at seeds 42-53 and N = 2,000: every mutant was killed in 12 of 12 runs; the bv_4 and bv_7
originals each failed 1 of 12 runs of a full-register parity assertion with reference 0. Those runs are not results
of this plan. The rule below, the budget and the seeds are fixed before any run under this plan.

## 1. Question and population

For each observation limitation, does the separating setting that QSurvDiag reports kill the mutant natively,
without failing the original?

Population: the 35 pairs with `v2_report == CL3` in `data/certification/outcomes/R2V_FINAL_PRIMARY.csv`. Contract,
executed input (all-zero), measured register (every qubit), gate lists and the execution adapter are those of the
baseline diagnosis.

## 2. Separating setting (method output, computed from ideal states before any run)

- A setting assigns a basis to each qubit: Z (no gate), X (H before measurement) or Y (S-dagger, then H).
- Settings are enumerated by the number k of non-Z qubits, k = 1..n; within k, by qubit subset in lexicographic
  order, then by basis tuple with X before Y.
- For each setting, the declared QUTest universe (marginals, Z products, basis-state probabilities, entropy, three
  distances; original-centred ideal references) is evaluated on the rotated joint distribution of every qubit.
  The witness is the first instance in the closed witness order (v3) whose difference exceeds theta = 0.05.
- The separating setting is the first setting that has a witness. Its setting, witness and difference are recorded
  in `X1_SETTINGS.csv` before any native run.
- The pair is excluded from native execution only if no setting has a witness; this is not expected (the all-X
  setting separates all 35 in simulation) and would be reported.

## 3. Native execution

- QUTest 0.1.0 through the pinned CLI, `environment/qiskit_settings.conf`, the validated execution adapter.
- Test per pair: the program inlined as a subroutine, the setting's gates, measurement of every qubit, one assertion:
  the witness, with the original's ideal value rounded to 4 decimals as reference and tolerance 0.05.
- Budget N = 8,000 for every pair. For a Z product the per-run standard error at N = 2,000 is up to 0.022, which
  explains the feasibility guard failures; at 8,000 it is at most 0.011.
- Seeds: mutant runs 13042-13053, original runs 14042-14053 (not used before).
- Control: the same witness instance without the setting's gates (computational basis), 12 runs on the mutant at the
  mutant seeds. Its ideal difference is 0 by the definition of observation limitation.
- Every execution records the CLI verdict, the assertion value and the histogram.

## 4. Decision and analysis

- Supported: the mutant is killed in 12 of 12 runs and the original fails in at most 1 of 12 (the rule of the
  repair comparison).
- Reported: number supported out of 35; settings by k; number of distinct settings per program; witness types;
  control kills (expected 0 of 12 per pair).
- Prediction recorded here: 35 of 35 supported; 28 settings with k = 1 and a marginal witness; 7 GHZ pairs with
  k = n and a full-register Z-product witness.
- No rerun, no change of budget and no reselection of settings after the first run. A failed execution of
  infrastructure (before any test body runs) is rerun once at the same seed and reported.

## 5. Outputs

`X1_SETTINGS.csv`, `X1_NATIVE_RUNS.csv`, `X1_SUMMARY.json`, the runner and the analysis script.
