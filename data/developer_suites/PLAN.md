# X2. Suites written outside this study and native QuCheck: plan (fixed before its native runs)

## 0. Selection history

The population and both suites were chosen after the earlier results of this study were known. None of their
mutants has been diagnosed or executed. A feasibility run before this plan executed QuCheck 0.0.2 natively on four
pairs of the 20 circuits (dj_3#e19, simon_4#h00, ghz_4#e04, simon_4#h04); those runs are not results of this plan.

## 1. Questions

Q1. Which outcomes do the survivors of suites written outside this study receive, and do they differ between a
    count-based suite and a property-based suite on the same mutants?
Q2. Does contract equivalence agree with independent labels of semantics-preserving mutants?
Q3. Do the simulated differences between the declared QUTest and QuCheck profiles hold under QuCheck's own
    statistical decisions?

## 2. Population and suites (Q1, Q2)

- Source: QuCheck repository, commit `74c275709c59749870d885889bf9994cfdd46786` (MIT; MITRE-derived files Apache-2.0).
- Programs: Deutsch-Jozsa, Grover, quantum Fourier transform, phase estimation, teleportation, superdense coding
  (`case_studies/<program>/<program>.py`).
- Mutants: `case_studies/<program>/mutants/<program>_m0..m19.py` and `_em0..em9.py` as present at the commit; the
  `em` files are labelled semantics-preserving by their authors. `translated_circuits/` (Q#) is excluded. Missing or
  non-importable files are listed, not replaced.
- Suite A, unit tests: `case_studies/MITRE_unit_test_baseline` (Deutsch-Jozsa, Grover, QFT, teleportation,
  superdense coding; phase estimation has none), run as published with 7,500 measurements, the smaller of the two
  budgets in the source.
- Suite B, property tests: every property of the program at the commit (`*_property.py`), run by the QuCheck code
  of the same commit (its Coordinator differs from the audited 0.0.2 release) as published: default alpha 0.01,
  100 inputs and 2,500 measurements (the source's main configuration), statevector Aer backend seeded per run.
- Environment for both suites: qiskit 1.1.1, qiskit-aer 0.17.2, numpy 1.26.4 (QuCheck requires qiskit < 1.1.2), as
  in the study's QuCheck records.
- Runtime check before any mutant runs: suites A and B on the six originals only, 12 runs each. If the projected
  serial time of suite B on all mutants exceeds 48 hours, suite B uses 20 inputs instead of 100; nothing else
  changes. The check also records the original's failure rate per suite.

## 3. Native execution

- Mutant substitution as in the source (`unittest.mock.patch` of the program function).
- 12 runs per (mutant, suite). Seeds: mutant runs 15042-15053, original runs 16042-16053, used as QuCheck's
  `random_seed` and as the simulator seed; the inputs generated in each run are recorded.
- Killed: the suite fails in 12 of 12 runs; survivor: not killed; split verdicts are reported and stay unresolved.

## 4. Diagnosis

- Executed inputs X: for suite A, the inputs its tests construct (oracles, prepared states); for suite B, the union of
  inputs generated over the 12 runs.
- Contract C, declared per program from its specification before diagnosis: arbitrary-input equivalence over the
  input family F, the union of the inputs of both suites. Contract equivalence: the two programs agree, up to global
  phase, on every input of F.
- Profiles, from an audit of each suite before diagnosis:
  - suite A: counts in the computational basis after the test's own fixed preparation and un-computation gates;
    admissible types those of the declared QUTest profile on those counts;
  - suite B: the declared QuCheck profile restricted to the bases and assertion methods its properties use.
- Relations over X: executed-input equality when the final states agree on every input of X but not on F;
  observation limitation when the observations agree on every input of X while some state differs; suite omission
  when an admissible instance differs by more than theta = 0.05 on some input of X; the five outcomes and the evidence
  requirements are otherwise unchanged.
- Native confirmation of a suite omission: the suite with the witness added, 12 runs on the mutant and on the
  original (rule: 12 of 12 kills, at most 1 of 12 original failures).

## 5. Native QuCheck on the 20 circuits (Q3)

- Pairs: the 28 pairs distinguishable only under the declared QuCheck profile and the 25 only under the declared
  QUTest profile (`R2V_TABLE_X_DECISIONS.csv`, part `interface`), and the 21 transfer cases
  (`data/interventions/transfer/B5_A4B_REPAIR_TRANSFER.csv`).
- Test: the audited QuCheck 0.0.2 release (source hash as recorded in the study), `assert_equal` over every qubit in
  x, y and z, 2,000 measurements, alpha 0.05, transpiler level
  0; original versus mutant. Control: original versus original (with a barrier), 12 runs per pair.
- Seeds: 15542-15553 (pairs) and 16542-16553 (controls).
- Detected: rejected in 12 of 12 runs. Predicted: the 28 detected, the 25 not; transfer cases with a witness (15)
  detected, those without (6) not.
- QuCheck's multiple-testing step as shipped decides; the recorded p-values are re-evaluated with a step-down Holm
  procedure as a sensitivity analysis.

## 6. Analysis

- Q1: outcomes per suite; survivors of one suite killed by the other, with the outcome under the surviving suite.
- Q2: contract equivalence against the `em` labels, as a two-by-two table per program.
- Q3: detection counts against the predictions, control false-detection rate.
- No change of rules after the first mutant run; deviations are reported as such.

## 7. Outputs

`X2_RUNTIME_CHECK.json`, `X2_NATIVE_RUNS.csv`, `X2_INPUTS.jsonl`, `X2_DIAGNOSIS.csv`, `X2_QUCHECK_20.csv`,
`X2_SUMMARY.json`, profile audit notes, runners and analysis scripts.
