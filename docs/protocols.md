# Protocols and settings

This document gives the settings and protocols behind Sections 4 and 5 of the article. Section, table and figure
numbers refer to the article.

## 1. Execution settings of the experiments

| Experiment | Shots N | References | Original-validity rule |
|---|---|---|---|
| Baseline diagnosis, native confirmation | 2,000 | ideal | passes 3 guard runs |
| Suite experiments | 8,000 | ideal | passes all 12 guard runs |
| Tolerance and budget experiment | 500, 2,000, 8,000 | sampled at 2,000 | as the baseline |
| MQT Bench validation | 2,000 | ideal | fails at most 1 of 12 runs |
| Repair comparison | 8,000 | ideal | fails at most 1 of 12 runs |
| QED-C workflow | 2,000 | P's ideal distribution | fails at most 1 of 12 runs |
| Separating settings | 8,000 | ideal, rounded to 4 decimals | fails at most 1 of 12 runs |
| Later positions | 2,000 | as the first sample of each population | as the first sample (`data/position/OPERATIONAL.md`) |
| QuCheck case studies | as each test is written; property tests 2,500 with 20 inputs | the tests' own | 12 guard runs, recorded |
| Native QuCheck on the 20 circuits | 2,000, alpha 0.05 | QuCheck's two-sample tests | control: the original against itself |

Every experiment runs the suite 12 times on each mutant. All experiments use theta = 0.05 except the tolerance and
budget experiment, which varies theta over {0.01, 0.025, 0.05, 0.10, 0.25, 0.50} and N. Guard runs check the original
before mutant verdicts are read. In the rows that allow one failure, the 12 runs of the original decide support. Ideal
references are the original's simulated probabilities. With 2,000-shot references, the factor 1 + N/N_0 of the
sampling bound (Section 3.4) is 1.25, 2 and 5 at the three budgets of the tolerance and budget experiment.

## 2. Testing tools (RQ1)

- **Structural-assertion trials.** Of the 546 mutants executed before the R_xx and R_zz rewriting, 85 are
  contract-equivalent to their original: 52 of development circuits and 33 of the other circuits. QUTest's gate-set
  check, with the original's gate names as the allowed set, flags 19 of the 33 and 19 of the 52 in every recorded
  trial. These flags come from five programs whose original always passes. In six other development circuits the
  transpilation varies and the original sometimes fails the check, so their 23 flags are unreliable (optimization
  level: section 9). A recorded prediction stated that the gate-set assertion would separate more than 80 % of the
  contract-equivalent mutants of the five other circuits, and the depth assertion fewer. The prediction failed: with
  both programs transpiled to the same basis-gate set, the audit separated none of the 33 by gate set and 11 by depth.
  A check of whether two programs transpile to the same circuit identifies 1 to 3 of the 85 contract-equivalent pairs
  across 36 transpiler configurations.
- **Developer-written tests.** In Qibo, Mitiq and Qualtran, tests run through pytest and can read the full state
  vector (Qibo, Mitiq) or the full unitary (Qualtran). Of 51 assertion occurrences, 30 check circuit structure,
  resources or set-up, 16 compare full state vectors or unitaries, and five read only computational-basis
  quantities. The check runs no mutants and estimates no prevalence (`data/external/developer_tests/`).

## 3. Semantic contracts (RQ2)

| Semantic relation of the 295 reported survivors | Development | Other | All | Unitary contract | Declared contracts |
|---|---:|---:|---:|---|---|
| Equivalent on all valid inputs | 4 | 0 | 4 | contract equivalence | contract equivalence |
| Same final state on the executed input, distinct on some valid input | 95 | 81 | 176 | executed-input equality | contract equivalence for 89; executed-input equality for 87 |
| Different final state on the executed input | 94 | 21 | 115 | later outcomes | later outcomes |

No recorded decision of the decision-diagram checker contradicts the simulator-based comparison.

Output-register contracts (`data/reanalysis/register_contracts.py`) require equal reduced states on the declared
output register. They make 13 observation limitations (GHZ 7, Bernstein-Vazirani and Deutsch-Jozsa 6) and 59 suite
omissions (GHZ 46, Toffoli 8, Simon 4, QPE 1) contract-equivalent. The below-tolerance difference keeps its outcome.

## 4. Causes of survival (RQ3)

- **Predictions about the five other circuits.** Twelve predictions were committed before the mutants of these
  circuits were sampled. Five failed (`history.md`, section 4).
- **Measurement settings.** Measuring the output register in the XYZ bases gives 60 observation limitations among
  the 193 pairs. XYZ on the output register and Z on every qubit are incomparable: each distinguishes pairs the
  other does not.
- **Output-condition suite by family.** Of its 65 suite-omission kills, 54 are GHZ, 9 Simon and 2 QFT.
- **Separating settings** (`data/observation_change/`). `find_settings.py` enumerates settings by the number of
  qubits outside Z, then by qubit subset, then with X before Y. The first setting with an instance above theta gives
  the setting and its witness (`separating_settings.csv`). `run_settings.py` runs the witness of each pair alone
  under its setting: 12 runs on the mutant (seeds 13042-13053) and 12 on the original (seeds 14042-14053). The
  control is the same instance without the setting's gates. The QED-C constructed pair used seeds 19042-19053 and
  20042-20053 (`qedc_setting.py`, `qedc_run.py`). The 65 later-position observation limitations used seeds
  21042-21053 and 22042-22053 (`later_positions.py`); their final states come from the executed inputs that
  `data/position/select_mutants.py` writes. `analyze.py` derives the decisions and summaries from the per-run records.
- **Settings read off the original** (`data/observation_change/two_basis_states.py`). For each of the 100 observation
  limitations, the script counts the basis states in the original's final state on the executed input. It forms the
  setting with X on every qubit in superposition in that state, compares it with the named setting and evaluates the
  declared universe under it.
- **Rotated profile** (`data/observation_change/rotated_profile.py`). The rotated profile evaluates every qubit
  under each of the 3^n XYZ settings; the baseline suite stays in the all-Z setting. The witness order is all-Z
  first, then the settings in search order, with the closed witness order within each setting. Stage 2 takes R_C
  and R_S from the declared diagnosis and evaluates R_O, R_A and R_T over the rotated universe and the suite. The
  witness runs are those of the separating settings. The negative control is the first instance outside the suite
  decided below theta. It ran alone at N = 8,000 on the mutant at the witness seeds and on the original at the first
  three original seeds. Stage 2 takes about 4 CPU hours, almost all of it for the twelve-qubit multipliers. The
  analytic tier reruns it on the 35 pairs of the 20 circuits.
- **Native QuCheck** (`data/developer_suites/qucheck_on_20_circuits.py`). One property per pair asserts equal
  distributions of every qubit in the X, Y and Z bases, at seeds 15542-15553. The controls compare the original with
  itself at seeds 16542-16553. QuCheck 0.0.2's Holm correction does not stop at the first retained hypothesis. The
  step-down procedure, applied to the recorded p-values, rejects exactly when the smallest p-value is at most
  alpha/m (`compare_with_predictions.py`).
- **Device noise** (`data/reanalysis/noise.py`). The median errors of the IBM Torino calibration in
  qiskit-ibm-runtime 0.40.1 serve as depolarizing gate errors and a symmetric readout error. Each circuit is
  transpiled to a line of qubits and simulated as a density matrix. Suite-omission witnesses keep a median 0.90 of
  their difference.
- **Tolerance and budget experiment.** The sampling bound covers decisions most often for Z products and marginals,
  least often for the entropy and the total-variation distance, and never for the Hellinger and Kullback-Leibler
  distances (`data/certification/outcomes/R2V_BOUND.json`).

## 5. Repairs (RQ4)

- **All-pairs comparison by witness location.** The all-pairs suite contains the witness for 197 of the 210
  candidates. The 13 witnesses outside it are Z products of weight three (3), four (1) and nine (2), five entropies
  and two Hellinger distances. The repairs support two weight-three and one weight-nine Z product, two entropies and
  one Hellinger distance. Where the all-pairs suite contains the witness, every run in which the repair killed the
  mutant was also an all-pairs kill on the same histogram.
- **Derived adjacent-pair suite.** Read from the all-pairs runs, the marginals and adjacent pairs alone reliably kill
  165 candidates, so the non-adjacent pairs add 27.
- **Execution accounting.** Both suites need the same 3,276 histograms of 8,000 shots (2,520 mutant, 756 original).
  The implementation ran 3,924 command-line executions for the repairs and 3,276 for the all-pairs suites, 7,200
  executions and 57.6 million shots. An in-process verification added 7,200 executions and 57.6 million simulator
  shots. The repairs hold 1,762 assertions and the all-pairs suites 7,174. Assertion evaluation took 4 s and 33 s,
  and diagnosis 10 s for the 210 candidates.
- **MQT Bench validation.** The withheld candidate is a walk mutant whose witness killed it in 9 of 12 confirmation
  runs and 11 of 12 validation runs. In 18 of the 22 certified cases the mutation replaces the first gate of a
  multiplier, a Hadamard gate, or inserts a gate before it, and the two-qubit Z product differs by 1. One group lies
  near theta: three deletions in the eight-qubit multiplier with difference 0.076, certified although the sampling
  bound does not cover their kill. The bound covers the mutant's kill for 19 of the 23 candidates and the original's
  guard runs for none. For all seven observation limitations, the largest suite in the sequence that their original
  passes is the baseline suite.
- **Evidence requirements as a classifier** (`data/reanalysis/requirements_scores_states.py`). Of the 165 issued
  repairs, 164 are supported in the repair comparison. Of the 23 unsupported repairs, 22 were withheld.
- **Transfer.** Every difference by which an admissible QuCheck assertion distinguishes a transferred pair exceeds
  theta by at least 0.45. `history.md`, section 3, describes an earlier exercise with QuCheck-style tests.

## 6. The QED-C case (RQ5)

| n | Fidelity of P to the exact evolution | of P_ship | Largest Z difference (shipped-coupling pair) | X statistic | Kills of P_ship (cert., valid.) | P fails baseline (cert., valid.) | Diagnosed | Shipped-coupling pair | Constructed pair | Parity kills of P_Z |
|---:|---:|---:|---:|---:|---|---|---|---|---|---:|
| 2 | 0.9998 | 0.9958 | 0.0071 | 0.0945 | 12, 12 | 0, 0 | yes | below tolerance | observation limitation | 12 |
| 3 | 0.9997 | 0.9936 | 0.0095 | 0.0835 | 11, 12 | 0, 0 | yes | below tolerance | observation limitation | 12 |
| 4 | 0.9995 | 0.9895 | 0.0316 | 0.0725 | 11, 11 | 0, 0 | yes | below tolerance | observation limitation | 12 |
| 5 | 0.9993 | 0.9856 | 0.0444 | 0.0722 | 10, 11 | 10, 9 | no | — | — | 12 |
| 6 | 0.9991 | 0.9816 | 0.0579 | 0.0722 | 10, 11 | 12, 12 | no | — | — | 12 |
| 7 | 0.9989 | 0.9776 | 0.0708 | 0.0722 | 10, 11 | 12, 12 | no | — | — | 12 |
| 8 | 0.9987 | 0.9736 | 0.0837 | 0.0722 | 10, 11 | 12, 12 | no | — | — | 12 |

At n = 2 the X statistic is the X expectation of qubit 0, the first X-basis instance of the closed witness order above
theta. Every instance before it differs by at most 0.0473 (`data/certification/witness_order/`). At n = 6 to 8, which
are not diagnosed, the entropy difference on the Z counts exceeds theta. P failed the supplementary statistics in none
of its runs. On the 672 recorded histograms, the stored-reference acceptance rule and the diagnostic baseline
referenced to P gave the same verdict on every one, with measured distances differing by at most 1.8e-4. At the
benchmark's default of 100 shots, the benchmark's normalized Hellinger fidelity of either program ranges over about
0.1 across 12 noiseless runs (`data/qedc/QEDC_METRICS.json`). The ideal fidelities of P and P_ship differ by at most
3.6e-4 and their computational-basis probabilities by at most 7.1e-3. The acceptance rule passes a run when the
Hellinger distance is at most theta, a Hellinger fidelity of at least (1 - theta^2)^2 = 0.99500625. Records:
`data/qedc/`.

## 7. Other programs (RQ6)

- **Q# and QASMBench programs.** Of 270 mutants, 111 are killed. The 159 survivors receive 28 contract
  equivalences, 94 executed-input equalities, 30 observation limitations (27 in the seven Q# operations, 3 in the two
  QASMBench circuits), 5 suite omissions, no below-tolerance difference and 2 unresolved outcomes. The selection rule
  placed 244 of the 270 mutants at the first gate.
- **MQT Bench programs.** Of 120 mutants, 64 are killed. The 56 survivors receive 14 contract equivalences, 10
  executed-input equalities, 7 observation limitations, 22 suite omissions and 3 unresolved outcomes. The walks give
  every contract equivalence and every unresolved case; the multipliers give every executed-input equality and
  observation limitation and 21 of the 22 suite omissions. The selection rule placed 68 of the 120 mutants at the
  first gate.
- **Later positions** (`data/position/`). For each of the 18 programs, the sample takes 10 mutations from the middle
  and 10 from the last third of the gates, under the strata of the first sample. `select_mutants.py` regenerates the
  selection from the pinned sources (Qolumbina archive, QASMBench commit `357b9423`) and writes the runner inputs
  `programs.json` and `mutant_gates.json`. These hold third-party gate lists and are not archived. The selection and
  pool checks it writes equal the archived `selection.csv` and `pool_checks.json`. `run_mutants.py` runs the
  baseline, diagnosis, native confirmation and negative control, and `analyze.py` writes `outcomes.csv`.
  `replay_check.py` reruns Stage 2 of the run driver on the 419 archived first-sample pairs of the five other circuits
  and the Q# and QASMBench programs; every relation and candidate agrees (`replay_check.out`).
- **QuCheck case studies** (`data/developer_suites/`). The QuCheck repository is pinned at commit `74c27570`. The
  harness (`harness.py`) needs `QUCHECK_SRC` set to that checkout and the environment of
  `environment/records/QUCHECK_CASE_STUDIES_pip_freeze.txt`. Each run of the original and a mutant at one seed
  generates the same inputs. Every circuit submitted to the simulator is a context, paired in submission order.
  `native_runs.jsonl.gz` keeps one record per suite, program, version and seed, with the arguments of every program
  call (the generated inputs) as the keys of `program_equal`. It keeps the witness circuit where native confirmation
  replays it. `native_runs.csv` is its flat view. `OPERATIONAL.md`, section X2_RUNTIME_DECISION, records the runtime
  check of the plan.
- **Width set.** The four unresolved cases are a split verdict, an undecided margin and two suite-omission candidates
  that fail native confirmation. The runtimes of Fig. 5 were measured under the rules of the first analysis
  (`history.md`, section 1). At fourteen qubits the median universe-evaluation time grows by a factor of 3.8 per added
  qubit. The extrapolated limit of nineteen qubits is an upper bound, because it holds state acquisition at its
  measured median.
- **Corpus.** Of the 562 survivors, 158 are contract equivalences. The 98 unresolved cases are 51 split verdicts, 3
  undecided margins and 44 suite-omission candidates. All ten widths with at least ten of the 1,569 pairs contain
  observation-limited pairs, at 9.4 % for n <= 7 and 9.9 % for n >= 8 (semantic comparisons). The 151st pair found by
  the comparisons has nineteen qubits and was not tested natively.
- **Released defects.** Each Bugs4Q defect was reproduced in three locked Qiskit versions (0.45.3, 1.1.1, 2.5.0) and
  assigned the deepest of five evidence levels: 10 not reproducible, 8 reproduced in the tool, 10 with the testing
  profile also known, 12 with semantic comparisons computed and 2 with full evaluation completed. Thirty-two defects
  reproduce in at least one version. The software-output comparison is decided for 12 defects. Under the declared
  QUTest profile the suite kills two of the four eligible defects. One survivor is an executed-input equality that
  differs only in the classical output mapping. The other is a suite omission, natively confirmed with the negative
  control of the closed witness order (`data/certification/witness_order/`). The six eligibility conditions are a run
  that reaches a final state, a contract with a recorded source, a declared output register, a supported circuit
  representation, a translation that preserves the final state, and an original that passes the suite. Qiskit issue
  16164, found by the screening of external workflows (`data/qedc/SCREENING.md`), is compared on the uniform
  superposition of its recorded reproduction (`R2V_RELEASED_CL3.json`); it has no suite and no native runs.

## 8. Numerical policy

Equality comparisons are decided on margins computed by noiseless simulation in double precision: the deviation
|<psi_P|psi_M>| from one for final states, |Tr(U_P^dagger U_M)|/2^n from one for unitaries, and the largest
difference between observation vectors. A margin below 1e-10 is equal, one above 1e-8 different, and one in between
undecided, which ends the case unresolved. A comparison d_a > theta is true when d_a exceeds theta by more than 5e-9,
the resolution at which differences are recorded. It is false when d_a falls below theta by more than that, and
undecided otherwise. An outcome that follows from an algebraic identity holds exactly. An outcome decided on a margin
holds to that margin, and its record states the margin. The margins of every decision are in
`data/certification/outcomes/R2_MARGINS.csv` and `R2_MARGINS_EXT.csv`.

## 9. Records, limits and material not redistributed

- **Decision-diagram check** (`data/certification/equivalence/`): one pinned run (mqt-qcec 3.9.0, mqt-core 3.9.2)
  over the 295 reported survivors of the 20 circuits; N01-N03 recount its ledger. The producing script and its
  exported inputs are not in the study records.
- **Developer-written tests** (`data/external/developer_tests/`): two raters labeled the 12 assertion families
  independently and agreed on all 12. Each occurrence is pinned by repository, commit, file and line. The 13 Mitiq
  quotations are replaced by descriptions (`provenance/DERIVED_FILES.csv`). The classification script needs the
  pinned checkouts.
- **Listing 1** (`R2V_WRAPPED_DEMO.csv`, `R2V_WRAPPED_DEMO_test.qasm`): the recorded run of 28 September 2026, at
  seeds 42-53 (N07, N08).
- **Gate-set trials**: Qiskit took optimization level 3 from the user configuration of the recording machine;
  `environment/qiskit_settings.conf` sets it for the analytic tier. QUTest's transpilation varied between repeated
  runs at levels 2 and 3.
- **Implementation** (`data/implementation/`): diagnosis driver, decision-resolution surface and tests. The modules
  they import are archived with the records that use them. `scripts/run_conformance_tests.py` runs three tests; the
  others execute QUTest.
- **Embedded paths**: archived files name the study's working folders, for example `revision2/`, the folder of the
  revised analysis of `V2_SPECIFICATION.md`. Some hold the study's absolute paths as recorded text. The package stores
  these files under `data/`; `scripts/analytic/r2v_inputs.csv` rebuilds the folder layout that the archived producers
  read.
- **Not redistributed**: QMutBench program files (GPL-3.0; their gate lists are in `R2V_NATIVE_JOBS_ARMS.jsonl`;
  per-case names and SHA-256 in `data/scalability/corpus/case_manifests/`; `data/inventory/fetch_corpus.sh` fetches
  them from the URLs, pinned to commit `01f5e770`, in `data/inventory/out/corpus_files.tsv`, and `inventory.py` checks
  every hash); the Q# and QASMBench program files (regenerated by `data/external/cohort/materialize.py` from the
  sources pinned in `data/external/protocol/EXTERNAL_COHORT_FREEZE.json`); tool sources: QUTest 0.1.0 (per-file
  SHA-256 in `environment/records/QUTEST_SOURCE_MANIFEST.json`), QuCheck 0.0.2 (GabrielPontolillo/qucheck; tree
  SHA-256 in `data/profiles/FINAL_PROFILE_SOURCE_EVIDENCE.json`), Muskit 0.0.3 (sdist SHA-256 in
  `data/profiles/MUSKIT_DOWNLOAD.json`), QMutPy (qmutpy-experiments `06cc1b29`, mutpy branch `all_gates` `13ab3845`).
  `DEPENDENCY_MANIFEST.txt` names its directory `env/`; it is `environment/records/`.
- Values that `expected/` does not list are not checked.

## 10. File names used in the plans

The plans and operational records of the separating-setting, developer-suite and later-position experiments are kept
byte-identical, so they name the experiments and files as they were named when recorded. Section labels such as
X2_OPERATIONAL name sections of `data/developer_suites/OPERATIONAL.md`.

| Name in the plans | Current name |
|---|---|
| X1 | separating-setting experiment, `data/observation_change/` |
| X2 | developer-suite experiment, `data/developer_suites/` |
| X4 | later-position experiment, `data/position/` |
| `X1_OBSERVATION_CHANGE.md` | `data/observation_change/PLAN.md` |
| `X1_POSITION_EXTENSION.md` | `data/observation_change/POSITION_EXTENSION.md` |
| `X2_DEVELOPER_SUITES.md` | `data/developer_suites/PLAN.md` |
| `X4_POSITION.md` | `data/position/PLAN.md` |
| `X1_SETTINGS.csv` | `data/observation_change/separating_settings.csv` |
| `X1_NATIVE_RUNS.csv` | `data/observation_change/native_runs.csv` |
| `X1_SUMMARY.json` | `data/observation_change/summary.json` |
| `X2_DIAGNOSIS.csv` | `data/developer_suites/diagnosis.csv` |
| `X2_NATIVE_RUNS.csv` | `data/developer_suites/native_runs.csv` |
| `X2_QUCHECK_20.csv` | `data/developer_suites/qucheck_on_20_circuits.csv` |
| `X2_SUMMARY.json` | `data/developer_suites/summary.json` |
| `X2_CONTROL.json` | `data/developer_suites/negative_controls.json` |
| `x2_control.py` | `data/developer_suites/negative_controls.py` |
| `X2_INPUTS.jsonl` | no separate file; the generated inputs are the keys of `program_equal` in `data/developer_suites/native_runs.jsonl.gz` |
| `X2_RUNTIME_CHECK.json` | no separate file; `data/developer_suites/OPERATIONAL.md`, section X2_RUNTIME_DECISION, records the check |
| `X4_SELECTION.csv` | `data/position/selection.csv` |
| `X4_NATIVE_RUNS.csv` | `data/position/native_runs.csv` |
| `X4_FINAL.csv` | `data/position/outcomes.csv` |
| `X4_SUMMARY.json` | `data/position/summary.json` |
| `x4_select.py` | `data/position/select_mutants.py` |
