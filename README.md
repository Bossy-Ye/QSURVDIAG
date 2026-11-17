# QSurvDiag replication package

This package holds the records and verification scripts of *Measure Differently or Assert More? Diagnosing Surviving
Quantum Mutants*. The native QUTest and QuCheck executions are archived and are not rerun. The scripts recompute every
checked value from the archived records.

Version 1.3.1.

## Verify

The package has two tiers of checks. The record tier recomputes every checked value from the archived records. It
needs Python 3.9 or later and the standard library, `openssl` for the RFC 3161 receipts, and a few seconds. The
analytic tier (next section) also reruns transpilation and simulation.

```sh
python3 scripts/verify.py --out ../out
```

`verify.py` runs the four scripts below in order and then repeats the integrity check. Each script also runs alone.

```sh
python3 scripts/verify_integrity.py --tsr
python3 scripts/reproduce.py --out ../out
python3 scripts/run_conformance_tests.py --out ../out
python3 scripts/reproduce_experiments.py --out ../out/experiments
```

`verify.py` ends with the summary below, which `expected/verify_summary.txt` holds; a different summary gives a
non-zero exit status.

```text
integrity     759 files, 0 problems; 549 archived files identical, 4 redacted; Freezes A to D verified
values        399 checks: MATCH 297, PARTIAL 100, ANALYTIC TIER 2
conformance   3 of 3 tests pass
experiments   90 checks: MATCH 74, PARTIAL 7, ANALYTIC TIER 9
```

MATCH means the value is recomputed from per-case or per-run records. PARTIAL means it equals an archived aggregate,
protocol record or git record. Any mismatch gives a non-zero exit status. `expected/` lists every checked value with
its inputs or article location and whether the article prints it.

## Analytic tier

The analytic tier recomputes the values that depend on transpilation and statevector simulation. It needs Python 3.12
and QUTest 0.1.0:

```sh
git clone https://github.com/QBugs/qutest.git ../qutest-0.1.0
git -C ../qutest-0.1.0 checkout c56e5a83f3b600a893e0d897ed86c705d25eb104
QUTEST_SRC=$PWD/../qutest-0.1.0 sh environment/setup.sh ../env
../env/analytic/bin/python scripts/reproduce_analytic.py --out ../out
git clone --depth 1 -b v2.0.8 https://github.com/SRI-International/QC-App-Oriented-Benchmarks.git ../qedc
python3 scripts/reproduce_experiments.py --out ../out/experiments --analytic ../env/analytic/bin/python \
  ../out/analytic/r2v_root ../qedc/qedcbench/hamiltonian_simulation/_common/precalculated_data.json
```

The three arguments of `--analytic` are the Python of the analytic environment, the input tree that
`reproduce_analytic.py` writes, and the QED-C reference file.

```text
reproduce_analytic      merged with the record tier: 407 checks   MATCH 342   PARTIAL 65
reproduce_experiments   with --analytic: 90 checks   MATCH 83    PARTIAL 7
```

The scripts check the QED-C reference file by its SHA-256. In the study environment, every analytic check matches.
With `--analytic`, the experiment checks also rerun the separating-setting searches and the three analyses of
`data/analyses/`. A02 is one fresh trial of QUTest's gate-set check, compared on the programs whose flags the article
treats as reliable. A06 compares `R2V_BOUND.json` except its witness counts, which the article does not print and
which depend on the order of ties (`data/checks/tie_check.py`). A07 compares margins to 1e-12.

## Article to records

| Article | Records |
|---|---|
| Table 1 | `data/prospective/mqt_bench/frozen_deps/V2_SPECIFICATION.md` (section 6), `data/prospective/registration/EVIDENCE_OBLIGATION_REGISTRY.yaml` |
| 3.1, Table 4, 5.1 | `data/profiles/`, `data/structural/`, `data/external/developer_tests/`; `data/checks/parameter_and_distance.py`, `observation_limited_universe.py` |
| 3.2 | `data/certification/witness_order/`; `data/certification/outcomes/R2V_FINAL_PRIMARY.csv`, `R2_MARGINS*.csv` |
| 3.4 | `data/certification/outcomes/R2V_BOUND.json`, `r2v_bound.py`; `data/implementation/tests/` |
| 4.2, Table 2; Table 3 | `data/primary/`, `data/external/`, `data/prospective/`, `data/scalability/`, `data/inventory/out/`; outcomes: `data/certification/outcomes/R2V_FINAL_*.csv`, `data/position/outcomes.csv`, `data/developer_suites/diagnosis.csv` |
| 4.3 | `docs/protocols.md`; the `PLAN.md` of each experiment |
| 5.2 | `data/certification/equivalence/`; `data/output_condition/simon_movers.out`; `data/analyses/register_contracts.json` |
| 5.3, Figs. 3 and 4, Table 5 | `data/certification/outcomes/` (`R2V_FINAL_*.csv`, `R2V_TABLE_X.json`, `R2V_DECISION_GRID.csv`, `r2v_stats.py`), `data/output_condition/`, `data/checks/circuit_level.py`; `data/analyses/requirements_scores_states.json` (distinct states and sites) |
| 5.3.2, 5.5, 7.2: separating settings, rotated profile | `data/observation_change/` (`separating_settings.csv`, `later_positions_settings.csv`, `two_basis_states.csv`, `rotated_profile.csv`) |
| 5.3.3, 5.4, 5.6, Table 3: native QuCheck and the QuCheck case studies | `data/developer_suites/` |
| 5.4, Table 6 | `data/all_pairs/`; `data/combined_suite/`; `data/prospective/mqt_bench/`; `data/interventions/transfer/`; `data/analyses/requirements_scores_states.json` (evidence requirements) |
| 5.5, Table 7 | `data/qedc/`; `data/certification/witness_order/QEDC_X_RUNS.csv` |
| 5.6, Fig. 5, Table 3 | `R2V_FINAL_*.csv` with `data/certification/witness_order/`; `data/scalability/`, `data/external/defects/`, `data/inventory/out/`; `data/position/` (later positions) |
| 6 | `data/analyses/requirements_scores_states.json` (mutation scores) |
| 7 | `docs/protocols.md`, section 11; `R2V_FINAL_*.csv` and `data/certification/witness_order/CHANGES.csv` (negative controls); `provenance/FREEZE_C.*`, `FREEZE_D.*`; `data/profiles/FINAL_PROFILE_RECONSTRUCTION_DIFF.csv`; `data/position/`; `data/analyses/noise.json`; `data/certification/outcomes/R2V_RULE_CHANGES.csv`; `data/combined_suite/`; `data/checks/circuit_level.py`; `data/inventory/out/concentration.json`, `data/inventory/POSITION_CROSSTAB.txt` |
| 8 | `data/certification/outcomes/R2V_FINAL_PRIMARY.csv` (state margins of the inverse test) |

The diagnosis code is archived with the records that use it: the driver in `data/implementation/qsurvdiag/`, the
comparisons, candidate selection and evidence check in `data/prospective/mqt_bench/frozen_deps/` (`e1_relations.py`,
`qsurvdiag_confirmatory.py`, `decision_bound.py`), and the tests in `data/implementation/tests/`. The package has no
command that diagnoses a new pair; `scripts/` reruns the archived analyses.

## Codes

The records and `expected/` use the study's codes.

| Code | Meaning |
|---|---|
| CL1 to CL5 | outcomes: contract equivalence, executed-input equality, observation limitation, suite omission, below-tolerance difference; NA_KILLED is a killed mutant |
| S_MIN, S_FAMILY, S_COVER, S_BOTH, S_SPEC | suites: baseline, adjacent-pair, all-qubit, combined (a marginal on every qubit and the Z products of all neighboring qubits), output-condition |
| construction, prospective | populations: the 15 development circuits and the five other circuits |
| OB01 to OB19 | evidence requirements (Table 1) |
| v1, v2, v3 | rule sets: v1 lacks rules 1 to 6 of `docs/protocols.md`, section 11; v2 adds rules 1 to 5 (`V2_SPECIFICATION.md`); v3 adds rule 6, the closed witness order (`data/certification/witness_order/RULE.md`) |
| X1, X2, X4 | the separating-setting, developer-suite and later-position experiments in their plans and operational records (arm `x4` in the later-position records); `docs/protocols.md`, section 10, maps the file names the plans use |
| suite A, suite B, `em` | in the developer-suite experiment: the unit tests, the property tests, and the mutants their authors label semantics-preserving |
| R1, R5, R6 | keys of `data/analyses/requirements_scores_states.json`: evidence requirements as a classifier, adjusted mutation scores, distinct final states and sites |
| D, S, A | in `expected/`: the witness suite (the article's repair), the combined suite and the all-pairs suite |
| certificate, certified | a reported outcome; reported |
| M, C | QED-C records: P_ship (the article's P_bench) and P_Z |
| natural pair | QED-C records: the article's benchmark-coupling pair |
| T, T' | QED-C records: the stored-reference rule and the diagnostic baseline |
| upstream score | QED-C records: the benchmark's normalized Hellinger fidelity |

## Check IDs

| Prefix | Checks | Expected values | Computed by |
|---|---|---|---|
| `M` | values behind the article | `expected/expected_results.csv` | `scripts/checks/article_checks.py` |
| `L-` | ledger values by population and record | `expected/expected_results.csv` | `scripts/checks/ledger_checks.py` |
| `V` | registered predictions, structural trials, protocol records, commits and file times | `expected/expected_results.csv` | `scripts/checks/protocol_checks.py` |
| `N` | decision-diagram equivalence check, developer tests, released defects, Listing 1, QuCheck, environment freezes | `expected/expected_results.csv` | `scripts/checks/records_checks.py` |
| `X` | width set, corpus, output-condition pool, transpiler sweep, MQT Bench rerun, concentration of causes | `expected/expected_results.csv` | `scripts/checks/records_checks.py` |
| `A` | analytic tier | `expected/expected_results.csv` | `scripts/reproduce_analytic.py` |
| `R-OC` | output-condition suites | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-CL` | circuit-level view of the matched changes | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-CM` | combined-suite comparison | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-AP` | all-pairs comparison | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-E` | QED-C case | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-V` | rule set v3 (closed witness order) | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-X` | separating settings and rotated profile (`R-X1`), developer suites (`R-X2`), later positions (`R-X4`), analyses of `data/analyses/` (`R-X5`) | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-WX` | witnesses of the reported suite omissions | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-NC` | negative controls of the reported suite omissions | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |
| `R-A` | reruns with `--analytic` | `expected/experiments_expected.csv` | `scripts/reproduce_experiments.py` |

## Layout

| Path | Contents |
|---|---|
| `data/` | records, plans, runners and analysis code of each experiment |
| `expected/` | expected value of every check; `analytic_coverage.csv` lists the checks that the record tier leaves to an analytic check |
| `scripts/` | verification |
| `docs/` | `protocols.md`: settings and protocols of each experiment, limits of the records, earlier file names, rule changes and the records that date them |
| `provenance/` | checksums, source manifest, commit records, redactions, license map |
| `environment/` | pinned environment of the analytic tier; records of the study environments |

Files listed in `provenance/source_manifest.csv` are byte-identical to their sources, except four redacted files
(`provenance/REDACTIONS.csv`) and one file whose quotations are replaced (`provenance/DERIVED_FILES.csv`). The
package does not redistribute the QMutBench, Q# and QASMBench program files or the tool sources.
`R2V_NATIVE_JOBS_ARMS.jsonl` holds the gate lists of the QMutBench and Q# programs in the native confirmations and
negative controls of suite-omission candidates; the gate lists of the later-position programs are regenerated.
`docs/protocols.md`, sections 7 and 9, gives the retrieval of each source.

## License

The package is under several licenses, and `provenance/LICENSE_MAP.csv` assigns one to each file. Study-authored code
is under MIT (`LICENSE`) and study-authored records are under CC BY 4.0 (`LICENSE-DATA`). One file with QMutBench gate
lists is under GPL-3.0-only. MQT Bench circuits are under MIT, the quoted Qibo and Qualtran test lines under
Apache-2.0, and the call arguments of the QuCheck case studies under MIT and Apache-2.0. Free TSA certificates and
receipts are included as issued. `LICENSES/NOTICE.txt` gives the notices.
