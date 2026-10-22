# Protocols and settings

Detail behind Sections 4 and 5 of the article. Section, table and figure numbers refer to the article.

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

Every experiment runs the suite 12 times on each mutant and uses theta = 0.05, except the tolerance and budget
experiment, which varies theta in {0.01, 0.025, 0.05, 0.10, 0.25, 0.50} and N. Guard runs check the original before
mutant verdicts are read; in the last three rows the 12 runs of the original count toward a supported repair. Ideal
references are the original's simulated probabilities; with 2,000-shot references, the factor 1 + N/N_0 of the sampling
bound (Section 3.4) is 1.25, 2 and 5 at the three budgets of the tolerance and budget experiment.

## 2. Testing tools (RQ1)

- **Structural-assertion trials.** Of the 546 mutants executed before the R_xx and R_zz rewriting, 85 are
  contract-equivalent to their original (52 development, 33 from the other circuits). QUTest's gate-set check, with
  the original's gate names as the allowed set, flags 19 of the 33 and 19 of the 52 in every recorded trial, from five
  programs whose original always passes; in six other development circuits the transpilation varies and the original
  sometimes fails the check, so their 23 flags are not reliable (optimization level: section 9). A recorded prediction
  that the gate-set assertion would separate more than 80 % of the contract-equivalent mutants of the five other
  circuits, and the depth assertion fewer, failed: after transpiling both programs to the same basis-gate set, the
  audit separated none of the 33 by gate set and 11 by depth. Checking whether two programs transpile to the same
  circuit identifies 1 to 3 of the 85 contract-equivalent pairs across 36 transpiler configurations.
- **Developer-written tests.** In Qibo, Mitiq and Qualtran, tests run through pytest and may read the full state
  vector (Qibo, Mitiq) or the full unitary (Qualtran). Of 51 assertion occurrences, 30 check circuit structure,
  resources or set-up, 16 compare full state vectors or unitaries, and five read only computational-basis
  quantities. The check mutates nothing and estimates no prevalence (`data/external/developer_tests/`).

## 3. Semantic contracts (RQ2)

| Semantic relation of the 295 reported survivors | Development | Other | All | Unitary contract | Declared contracts |
|---|---:|---:|---:|---|---|
| Equivalent on all valid inputs | 4 | 0 | 4 | contract equivalence | contract equivalence |
| Same final state on the executed input, distinct on some valid input | 95 | 81 | 176 | executed-input equality | contract equivalence for 89; executed-input equality for 87 |
| Different final state on the executed input | 94 | 21 | 115 | later outcomes | later outcomes |

None of the decision-diagram checker's recorded decisions contradicted the simulator-based comparison.

Output-register contracts (`data/reanalysis/r3_register_contract.py`) require equal reduced states on the declared
output register. They make 13 observation limitations (GHZ 7, Bernstein-Vazirani and Deutsch-Jozsa 6) and 59 suite
omissions (GHZ 46, Toffoli 8, Simon 4, QPE 1) contract-equivalent; the below-tolerance difference stays.

## 4. Causes of survival (RQ3)

- **Predictions about the five other circuits.** Twelve were committed before their mutants were sampled; five
  failed (`history.md`, section 4).
- **Measurement settings.** Measuring the output register in the XYZ bases gives 60 observation limitations among
  the 193 pairs. XYZ on the output register and Z on every qubit are incomparable: each distinguishes pairs the
  other does not.
- **Output-condition suite by family.** Of its 65 suite-omission kills, 54 are GHZ, 9 Simon and 2 QFT.
- **Separating settings** (`data/observation_change/`). Settings are enumerated by the number of qubits outside Z,
  then by qubit subset, then with X before Y; the first setting with an instance above theta gives the setting and
  its witness. Each pair ran the witness alone under its setting, 12 runs on the mutant (seeds 13042-13053) and 12
  on the original (14042-14053); the control is the same instance without the setting's gates. The QED-C
  constructed pair used seeds 19042-19053 and 20042-20053.
- **Native QuCheck** (`data/developer_suites/x2_qucheck20.py`). One property per pair asserts equal distributions of
  every qubit in the x, y and z bases; controls compare the original with itself (seeds 15542-15553 and
  16542-16553). QuCheck 0.0.2's Holm correction does not stop at the first retained hypothesis; the step-down
  procedure, applied to the recorded p-values, rejects exactly when the smallest p-value is at most alpha/m.
- **Device noise** (`data/reanalysis/r4_noise.py`). Median errors of the IBM Torino calibration in
  qiskit-ibm-runtime 0.40.1 as depolarizing gate errors and a symmetric readout error, each circuit transpiled to a
  line of qubits and simulated as a density matrix; suite-omission witnesses keep a median 0.90 of their difference.
- **Tolerance and budget experiment.** The sampling bound covers decisions most often for Z products and marginals,
  least often for the entropy and the total-variation distance, and never for the Hellinger and Kullback-Leibler
  distances (`data/certification/outcomes/R2V_BOUND.json`).

## 5. Repairs (RQ4)

- **All-pairs comparison by witness location.** The all-pairs suite contains the witness for 197 of the 210
  candidates. The 13 witnesses outside it are Z products of weight three (3), four (1) and nine (2), five entropies
  and two Hellinger distances; the witness suites support two weight-three and one weight-nine Z product, two
  entropies and one Hellinger distance. Where the all-pairs suite contains the witness, every run in which the
  witness suite killed the mutant was also an all-pairs kill on the same histogram.
- **Derived adjacent-pair suite.** Read from the all-pairs runs, the marginals and adjacent pairs alone are
  supported on 165 candidates, so the non-adjacent pairs add 27.
- **Execution accounting.** Both suites need the same 3,276 histograms of 8,000 shots (2,520 mutant, 756 original).
  The implementation ran 3,924 command-line executions for the witness suites and 3,276 for the all-pairs suites,
  7,200 executions and 57.6 million shots; an in-process verification added 7,200 executions and 57.6 million
  simulator shots. The witness suites hold 1,762 assertions and the all-pairs suites 7,174; assertion evaluation
  took 4 s and 33 s, and diagnosis 10 s for the 210 candidates.
- **MQT Bench validation.** The withheld candidate is a walk mutant whose witness killed it in 9 of 12 confirmation runs
  and 11 of 12 validation runs. In 18 of the 22 certified cases the mutation replaces the first gate of a multiplier, a
  Hadamard gate, or inserts a gate before it, and the two-qubit Z product differs by 1. One group lies near theta: three
  deletions in the eight-qubit multiplier with difference 0.076, certified although the sampling bound does not cover
  their kill. The bound covers the mutant's kill for 19 of the 23 candidates and the original's guard runs for none. For
  all seven observation limitations, the largest suite in the sequence that their original passes is the baseline suite.
- **Evidence requirements as a classifier** (`data/reanalysis/r156.py`). Of the 165 issued repairs, 164 are supported
  by the all-pairs runs of their witness suite; of the 23 unsupported, 22 were withheld.
- **Transfer.** Every difference by which an admissible QuCheck assertion distinguishes a transferred pair exceeds
  theta by at least 0.45. An earlier exercise with QuCheck-style tests is described in `history.md`, section 3.

## 6. The QED-C case (RQ5)

| n | Fidelity of P to the exact evolution | of P_ship | Largest Z difference (shipped-coupling pair) | X statistic | Kills of P_ship (cert., valid.) | P fails baseline (cert., valid.) | Admitted | Shipped-coupling pair | Constructed pair | Parity kills of P_Z |
|---:|---:|---:|---:|---:|---|---|---|---|---|---:|
| 2 | 0.9998 | 0.9958 | 0.0071 | 0.0945 | 12, 12 | 0, 0 | yes | below tolerance | observation limitation | 12 |
| 3 | 0.9997 | 0.9936 | 0.0095 | 0.0835 | 11, 12 | 0, 0 | yes | below tolerance | observation limitation | 12 |
| 4 | 0.9995 | 0.9895 | 0.0316 | 0.0725 | 11, 11 | 0, 0 | yes | below tolerance | observation limitation | 12 |
| 5 | 0.9993 | 0.9856 | 0.0444 | 0.0722 | 10, 11 | 10, 9 | no | — | — | 12 |
| 6 | 0.9991 | 0.9816 | 0.0579 | 0.0722 | 10, 11 | 12, 12 | no | — | — | 12 |
| 7 | 0.9989 | 0.9776 | 0.0708 | 0.0722 | 10, 11 | 12, 12 | no | — | — | 12 |
| 8 | 0.9987 | 0.9736 | 0.0837 | 0.0722 | 10, 11 | 12, 12 | no | — | — | 12 |

At n = 2 the X statistic is the X expectation of qubit 0, the first X-basis instance of the closed witness order above
theta; every instance before it differs by at most 0.0473 (`data/certification/witness_order/`). At n = 6 to 8, which
are not admitted, the entropy difference on the Z counts exceeds theta. P failed the supplementary statistics in none of
its runs. On the 672 recorded histograms, the stored-reference acceptance rule and the diagnostic baseline referenced to
P gave the same verdict on every one, with measured distances differing by at most 1.8e-4. At the benchmark's default of
100 shots, the upstream score of either program ranges over about 0.1 across 12 noiseless runs
(`data/qedc/QEDC_METRICS.json`). The ideal upstream
scores of P and P_ship differ by at most 3.6e-4 and their computational-basis probabilities by at most 7.1e-3. The
acceptance rule passes a run when the Hellinger distance is at most theta, a Hellinger fidelity of at least (1 -
theta^2)^2 = 0.99500625. Records: `data/qedc/`.

## 7. Other programs (RQ6)

- **Q# and QASMBench programs.** Of 270 mutants, 111 are killed; the 159 survivors receive 28 contract
  equivalences, 94 executed-input equalities, 30 observation limitations (27 in the seven Q# operations, 3 in the
  two QASMBench circuits), 5 suite omissions, no below-tolerance difference and 2 unresolved outcomes. The
  selection rule placed 244 of the 270 mutants at the first gate.
- **MQT Bench programs.** Of 120 mutants, 64 are killed; the 56 survivors receive 14 contract equivalences, 10
  executed-input equalities, 7 observation limitations, 22 suite omissions and 3 unresolved outcomes. The walks
  give every contract equivalence and every unresolved case; the multipliers give every executed-input equality
  and observation limitation and 21 of the 22 suite omissions. The selection rule placed 68 of the 120 mutants at
  the first gate.
- **Later positions** (`data/position/`). For each of the 18 programs, 10 mutations from the middle and 10 from the
  last third of the gates, under the strata of the first sample. `x4_select.py` regenerates the selection from the
  pinned sources (Qolumbina archive, QASMBench commit `357b9423`) and writes the runner inputs, which hold
  third-party gate lists and are not archived; the selection and pool checks it writes equal the archived files.
  `x4_replay_check.py` reruns Stage 2 of the run driver on the 419 archived first-sample pairs of the five other
  circuits and the Q# and QASMBench programs; every relation and candidate agrees (`x4_replay_check.out`).
- **QuCheck case studies** (`data/developer_suites/`). QuCheck repository at commit `74c27570`; the harness needs
  `X2_SRC` set to that checkout and the environment of `environment/records/QUCHECK_CASE_STUDIES_pip_freeze.txt`.
  Each run of the original and a mutant at one seed generates the same inputs; every circuit submitted to the
  simulator is a context, paired in submission order. `X2_NATIVE_RUNS.jsonl.gz` keeps one record per suite, program,
  version and seed, with the arguments of every program call (the generated inputs) as the keys of `program_equal`;
  the witness circuit is kept where native confirmation replays it. `X2_NATIVE_RUNS.csv` is its flat view. The runtime
  check of the plan is recorded in `OPERATIONAL.md` (X2_RUNTIME_DECISION).
- **Width set.** The four unresolved cases are a split verdict, an undecided margin and two suite-omission
  candidates that fail native confirmation. The runtimes of Fig. 5 were measured under the initial analysis. At
  fourteen qubits the median universe-evaluation time grows by a factor of 3.8 per added qubit; the extrapolated
  limit of nineteen qubits is an upper bound, because it holds state acquisition at its measured median.
- **Corpus.** Of the 562 survivors, 158 are contract equivalences; the 98 unresolved cases are 51 split verdicts,
  3 undecided margins and 44 suite-omission candidates. All ten widths with at least ten of the 1,569 pairs contain
  observation-limited pairs, at 9.4 % for n <= 7 and 9.9 % for n >= 8 (semantic comparisons). The 151st pair found
  by the comparisons has nineteen qubits and was not tested natively.
- **Released defects.** Each Bugs4Q defect was reproduced in three locked Qiskit versions (0.45.3, 1.1.1, 2.5.0)
  and assigned the deepest of five evidence levels: 10 not reproducible, 8 reproduced in the tool, 10 with the
  testing profile also known, 12 with semantic comparisons computed and 2 with full evaluation completed; 32
  reproduce in at least one version. The software-output comparison is decided for 12 defects. Under the declared
  QUTest profile the suite kills two of the 4 eligible defects; one survivor is an executed-input equality that
  differs only in the classical output mapping, and the other a suite omission, natively confirmed with the negative
  control of the closed witness order (`data/certification/witness_order/`). The six eligibility conditions are: a
  run that reaches a final state, a contract with a recorded source, a declared output register, a supported
  circuit representation, a translation that preserves the final state, and an original that passes the suite.

## 8. Numerical policy

Equality comparisons are decided on margins computed by noiseless simulation in double precision: the deviation
|<psi_P|psi_M>| from one for final states, |Tr(U_P^dagger U_M)|/2^n from one for unitaries, and the largest
difference between observation vectors. A margin below 1e-10 is equal, one above 1e-8 different, and one in
between undecided, which ends the case unresolved. A comparison d_a > theta is true when d_a exceeds theta by more
than 5e-9, the resolution at which differences are recorded, false when it falls below theta by more than that,
and undecided otherwise. An outcome that follows from an algebraic identity holds exactly; one decided on a margin
holds only to that margin, and its record states the margin. The margins of every decision are in
`data/certification/outcomes/R2_MARGINS.csv` and `R2_MARGINS_EXT.csv`.

## 9. Records, limits and material not redistributed

- **Decision-diagram check** (`data/certification/equivalence/`): one pinned run (mqt-qcec 3.9.0, mqt-core 3.9.2)
  over the 295 reported survivors of the 20 circuits; N01-N03 recount its ledger. The producing script and its
  exported inputs are not in the study records.
- **Developer-written tests** (`data/external/developer_tests/`): two raters labeled the 12 assertion families
  independently and agreed on all 12; each occurrence is pinned by repository, commit, file and line. The 13 Mitiq
  quotations are replaced by descriptions (`provenance/DERIVED_FILES.csv`). The classification script needs the pinned
  checkouts.
- **Listing 1** (`R2V_WRAPPED_DEMO.csv`, `R2V_WRAPPED_DEMO_test.qasm`): the recorded run of 28 September 2026, at
  seeds 42-53 (N07, N08).
- **Gate-set trials**: Qiskit took optimization level 3 from the user configuration of the recording machine;
  `environment/qiskit_settings.conf` sets it for the analytic tier. QUTest's transpilation varied between repeated
  runs at levels 2 and 3.
- **Implementation** (`data/implementation/`): diagnosis driver, decision-resolution surface and tests; the modules
  they import are archived with the records that use them. `scripts/run_conformance_tests.py` runs three tests; the
  others execute QUTest.
- **Embedded paths**: archived files name the study's working folders (for example `revision2/`, the folder of the
  revised analysis of `V2_SPECIFICATION.md`) and some hold the study's absolute paths as recorded text. The package
  stores these files under `data/`; `scripts/analytic/r2v_inputs.csv` rebuilds the folder layout that the archived
  producers read.
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
