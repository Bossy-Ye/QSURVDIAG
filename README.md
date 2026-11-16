# QSurvDiag replication package

This package holds the records and verification scripts of *Measure Differently or Assert More? Diagnosing Surviving
Quantum Mutants*. The native QUTest and QuCheck executions are archived and are not rerun. The scripts recompute every
checked value from the archived records.

Version 1.3.1.

## Verify

The record tier needs Python 3.9 or later and the standard library; `--tsr` also needs `openssl`.

```sh
python3 scripts/verify_integrity.py --tsr
python3 scripts/reproduce.py --out ../out
python3 scripts/run_conformance_tests.py --out ../out
python3 scripts/reproduce_experiments.py --out ../out/experiments
```

```text
verify_integrity        0 problems; RFC 3161 Freeze A to D OK; Freeze A 69 of 70 matching, 1 redacted
reproduce               399 checks   MATCH 297   PARTIAL 100   analytic tier 2
conformance             3 of 3 pass
reproduce_experiments    90 checks   MATCH 74    PARTIAL 7     analytic tier 9
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

```text
reproduce_analytic      merged with the record tier: 407 checks   MATCH 342   PARTIAL 65
reproduce_experiments   with --analytic: 90 checks   MATCH 83    PARTIAL 7
```

The scripts check the QED-C reference file by its SHA-256. All analytic checks match. With `--analytic`, the
experiment checks also rerun the separating-setting searches and the three analyses of `data/analyses/`. A02 is one
fresh trial of QUTest's gate-set check, compared on the programs whose flags the article treats as reliable. A06
compares `R2V_BOUND.json` without its unprinted witness-surface counts, which depend on the order of ties
(`data/checks/tie_check.py`). A07 compares margins to 1e-12.

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
| D, S, A | in `expected/`: the witness suite (the article's repair), the combined suite and the all-pairs suite; a certificate is a reported outcome |
| M, C | QED-C records: P_ship (the article's P_bench) and P_Z |
| natural pair | QED-C records: the article's benchmark-coupling pair |
| T, T' | QED-C records: the stored-reference rule and the diagnostic baseline |
| upstream score | QED-C records: the benchmark's normalized Hellinger fidelity |

## Layout

| Path | Contents |
|---|---|
| `data/` | records, plans, runners and analysis code of each experiment |
| `expected/` | expected value of every check |
| `scripts/` | verification |
| `docs/` | `protocols.md`: settings, protocols, record limits, the file names used in the plans, and the rule changes and the records that date each rule |
| `provenance/` | checksums, source manifest, commit records, redactions, license map |
| `environment/` | pinned environment of the analytic tier; records of the study environments |

Files listed in `provenance/source_manifest.csv` are byte-identical to their sources. The exceptions are four redacted
files (`provenance/REDACTIONS.csv`) and one file whose quotations are replaced (`provenance/DERIVED_FILES.csv`). The
package does not redistribute the QMutBench and external program files, whose gate lists are in
`R2V_NATIVE_JOBS_ARMS.jsonl`, the gate lists of the later-position programs, or the tool sources (`docs/protocols.md`,
sections 7 and 9).

## License

Mixed; `provenance/LICENSE_MAP.csv` assigns each file. Code MIT (`LICENSE`), records CC BY 4.0 (`LICENSE-DATA`), one
QMutBench gate-list file GPL-3.0-only, MQT Bench circuits MIT, quoted Qibo and Qualtran test lines Apache-2.0, QuCheck
case-study call arguments MIT and Apache-2.0, Free TSA certificates and receipts as issued. Notices:
`LICENSES/NOTICE.txt`.
