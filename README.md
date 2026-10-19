# QSurvDiag replication package

Records and verification scripts for *Why Quantum Mutants Survive: Separating Observation Limitations from Suite
Omissions*. Native QUTest executions are archived, not rerun; the scripts recompute every checked value from the
archived records.

## Verify

Python 3.9+, standard library only; `--tsr` needs `openssl`.

```sh
python3 scripts/verify_integrity.py --tsr
python3 scripts/reproduce.py --out ../out
python3 scripts/run_conformance_tests.py --out ../out
python3 scripts/reproduce_experiments.py --out ../out/experiments
```

```text
verify_integrity        0 problems; RFC 3161 Freeze A and B OK; Freeze A 69 of 70 matching, 1 redacted
reproduce               399 checks   MATCH 297   PARTIAL 100   analytic tier 2
conformance             3 of 3 pass
reproduce_experiments    53 checks   MATCH 49    PARTIAL 2     analytic tier 2
```

MATCH: recomputed from per-case or per-run records. PARTIAL: equal to an archived aggregate, protocol record or git
record. Any mismatch exits non-zero. `expected/` lists every checked value, its inputs and whether the article
prints it.

## Analytic tier

Recomputes the transpilation- and statevector-based values. Python 3.12 and QUTest 0.1.0:

```sh
git clone https://github.com/QBugs/qutest.git ../qutest-0.1.0
git -C ../qutest-0.1.0 checkout c56e5a83f3b600a893e0d897ed86c705d25eb104
QUTEST_SRC=$PWD/../qutest-0.1.0 sh environment/setup.sh ../env
../env/analytic/bin/python scripts/reproduce_analytic.py --out ../out
git clone --depth 1 -b v2.0.8 https://github.com/SRI-International/QC-App-Oriented-Benchmarks.git ../qedc
python3 scripts/reproduce_experiments.py --out ../out/experiments --analytic ../env/analytic/bin/python \
  ../out/analytic/r2v_root ../qedc/qedcbench/hamiltonian_simulation/_common/precalculated_data.json
```

The QED-C reference file is checked by its SHA-256. All checks match; merged with the record tier, 407 checks: MATCH
342, PARTIAL 65. A02 is one fresh trial of QUTest's gate-set check, compared on the programs whose flags the article
treats as reliable. A06 compares `R2V_BOUND.json` without its unprinted witness-surface counts, which depend on the
order of ties (`data/checks/tie_check.py`); A07 compares margins to 1e-12.

## Article to records

| Article | Records |
|---|---|
| Table 1 | `data/prospective/mqt_bench/frozen_deps/V2_SPECIFICATION.md` (section 6), `data/prospective/registration/EVIDENCE_OBLIGATION_REGISTRY.yaml` |
| 3.1, Table 4, 5.1 | `data/profiles/`, `data/structural/`, `data/external/developer_tests/`; `data/checks/parameter_and_distance.py`, `observation_limited_universe.py` |
| 3.2 | `data/certification/witness_order/`; `data/certification/outcomes/R2V_FINAL_PRIMARY.csv`, `R2_MARGINS*.csv` |
| 3.4 | `data/certification/outcomes/R2V_BOUND.json`, `r2v_bound.py`; `data/implementation/tests/` |
| 4.2, Tables 2 and 3 | `data/primary/`, `data/external/`, `data/prospective/`, `data/scalability/`, `data/inventory/out/` |
| 4.3 | `docs/protocols.md`; the plan of each experiment |
| 5.2 | `data/certification/equivalence/`; `data/output_condition/OC_SIMON_MOVERS.out` |
| 5.3, Figs. 3 and 4, Table 5 | `data/certification/outcomes/` (`R2V_FINAL_*.csv`, `R2V_TABLE_X.json`, `R2V_DECISION_GRID.csv`, `r2v_stats.py`), `data/output_condition/`, `data/checks/circuit_level.py` |
| 5.4, Table 6 | `data/all_pairs/`; `data/prospective/mqt_bench/`; `data/interventions/transfer/` |
| 5.5, Table 7 | `data/qedc/`; `data/certification/witness_order/QEDC_X_RUNS.csv` |
| 5.6, Fig. 5 | `R2V_FINAL_*.csv` with `data/certification/witness_order/`; `data/scalability/`, `data/external/defects/`, `data/inventory/out/` |
| 7 | `docs/history.md`; `data/certification/outcomes/R2V_RULE_CHANGES.csv`; `data/combined_suite/`; `data/checks/circuit_level.py`; `data/inventory/out/concentration.json`, `data/inventory/POSITION_CROSSTAB.txt` |

## Codes

Records and `expected/` use the study's codes. Outcomes: CL1 contract equivalence, CL2 executed-input equality, CL3
observation limitation, CL4 suite omission, CL5 below-tolerance difference. Suites: S_MIN baseline, S_FAMILY
adjacent-pair, S_COVER all-qubit, S_BOTH combined, S_SPEC output-condition. Populations: construction = the 15
development circuits, prospective = the five other circuits. OB01-OB19: evidence requirements (Table 1). v1, v2,
v3: initial rules, revised rules (`V2_SPECIFICATION.md`), witness-order amendment (`docs/history.md`).

## Layout

| Path | Contents |
|---|---|
| `data/` | records, plans, runners and analysis code of each experiment |
| `expected/` | expected value of every check |
| `scripts/` | verification |
| `docs/` | `protocols.md` settings, protocols and record limits; `history.md` when each rule was fixed |
| `provenance/` | checksums, source manifest, commit records, redactions, license map |
| `environment/` | pinned environment of the analytic tier |

Archived files are byte-identical to their sources (`provenance/source_manifest.csv`), except four redacted files
(`provenance/REDACTIONS.csv`) and replaced quotations (`provenance/DERIVED_FILES.csv`). QMutBench programs, external
programs and tool sources are not redistributed (`docs/protocols.md`, section 9).

## License

Mixed; `provenance/LICENSE_MAP.csv` assigns each file. Code MIT (`LICENSE`), records CC BY 4.0 (`LICENSE-DATA`), one
QMutBench gate-list file GPL-3.0-only, MQT Bench circuits MIT, quoted Qibo and Qualtran test lines Apache-2.0, Free TSA
certificates and receipts as issued. Notices: `LICENSES/NOTICE.txt`.
