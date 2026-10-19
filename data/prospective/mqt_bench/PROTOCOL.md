# Prospective MQT Bench cohort: frozen protocol (Pass 3B)

Status: **FROZEN at Freeze A.** The commit identifier and RFC 3161 timestamp are recorded in `freeze/FREEZE_LOG.md`.
Approved design: `PASS3A2_SCIENTIFIC_DECISION.md`. Manuscript baseline: pass 44 (unchanged).
After Freeze A, any change to any rule, file or seed is a protocol deviation (§8).

## 1. Question and scope

**The question.** When the final revised QSurvDiag procedure is frozen before any outcome of this cohort exists, does it produce evidence-supported diagnoses and testing recommendations on independently sourced programs, and do the recommendations hold in independent native executions?

**The experiment can establish:**
- the application of the unchanged revised procedure (v2, OB01–OB19, the declared QUTest profile) to new subjects;
- independent native confirmation of its recommendations under fresh execution randomness.

**The experiment cannot establish:**
- effectiveness for developer-written suites;
- behavior on hardware;
- behavior for arbitrary program families;
- behavior under a different testing tool;
- prevalence.

**Reporting.** Results are reported per subject, per family and overall. The mutants form 4 clusters of 30 and are never treated as independent program-level observations. The cohort is reported separately from every historical population and denominator.

## 2. Population

**Source.** MQT Bench v2.3.0: PyPI `mqt.bench==2.3.0`, with Qiskit 2.5.2, in `.venv-mqt-bench-230`, locked in `env/requirements-mqt.lock`.

| Subject | Family | MQT module (args) | n | Converted body gates | Body SHA-256 (prefix) | Contract | Declared executed input | Output register |
|---|---|---|---|---|---|---|---|---|
| `qwalk_4` | quantum walk | `qwalk` (num_qubits = 4; depth 3; for_loop False) | 4 | 303 | c10788f13063b67e | C_FIXED_INPUT_STATE | \|0000⟩ | all qubits |
| `qwalk_5` | quantum walk | `qwalk` (num_qubits = 5) | 5 | 723 | 63a21e49fea63ce1 | C_FIXED_INPUT_STATE | \|00000⟩ | all qubits |
| `rg_mult_8` | multiplication | `rg_qft_multiplier` (num_qubits = 8) | 8 | 196 | e2e3b67af55f3bbb | C_ARBITRARY_INPUT_UNITARY | (\|a=1, b=1, out=0⟩ + \|a=3, b=3, out=0⟩)/√2 | all qubits |
| `rg_mult_12` | multiplication | `rg_qft_multiplier` (num_qubits = 12) | 12 | 636 | fca3a26292aeb386 | C_ARBITRARY_INPUT_UNITARY | (\|a=1, b=1, out=0⟩ + \|a=7, b=7, out=0⟩)/√2 | all qubits |

Records: `subjects/SUBJECTS.json` (gate lists, preparation, analytic marginals, hashes) and `subjects/SUBJECT_MANIFEST.csv`.

**Excluded, before outcomes (PASS3A–3A2):** graph states, HHL and every other family. No subject is added or replaced in response to any count.

**Conversion.** The external-cohort convention:
- `qiskit.transpile` to the enumerator vocabulary (x, y, h, sx, rx, ry, z, s, t, p, rz, cx, cz, cp, rxx, rzz), `optimization_level=0`, `seed_transpiler=0`, final measurements removed;
- at execution, the frozen `adapt` (rzz and rxx only) and `emit_name`.

**Declared input.** The external-cohort preparation `r2_external.prep_gates(x_a, x_b, n)`, prepended at execution and never mutated:
- x_a = (a = 1, b = 1, out = 0) and x_b = (a = 2^k − 1, b = 2^k − 1, out = 0);
- correctness is claimed only for this declared input and for the basis inputs checked in Stage A.

## 3. Original-program verification (pre-freeze information)

| Subject | Check | Result |
|---|---|---|
| walks | overlap with an independent coined walk (cycle Z_{2^m}, H coin, coin = 1 → +1, 3 steps), for the MQT, converted and adapted forms | 1 − 10⁻¹⁴: **pass** |
| `rg_mult_8`, `rg_mult_12` | declared input → (\|1,1,1⟩ + \|3,3,9⟩)/√2 and (\|1,1,1⟩ + \|7,7,49⟩)/√2: \|amplitudes\| = 1/√2, relative phase ≤ 6×10⁻¹⁵ rad, no other weight; converted and adapted forms equal the MQT state | **pass** |
| multipliers (Stage A) | full basis domain correct with no relative phase; random-state preservation 1.0 | **pass** |
| all (Stage A and dry run) | QUTest parses the converted original; original passes S_MIN 12/12 at seeds 42–53 | **pass** |
| D2 assumption (dry run) | each original against an original-only equivalent variant (two trailing Z gates) at the same seeds: paired agreement 12/12 in all four subjects. At independent seeds the same equivalent variant was "killed" 4/12 (walks), which is why independent-seed counts are descriptive only | recorded |

Records: `subjects/VERIFY_INPUTS.json`, `stageA_prefreeze/`, `records/dry_run_*` (original programs only).

## 4. Method (unchanged and hash-checked)

**Procedure.** The revised analysis `V2_SPECIFICATION.md` (SHA-256 6829f1ba…), implemented by:
- `r2v_lib.py`, `r2v_arms.diagnose`, `r2v_finalize.finalize_row`;
- `qsurvdiag_confirmatory.py` (relations R_C, R_S, R_O, R_A and R_T; candidate order; OB01–OB19; certification and abstention; numerical policy).

**Profile.** `QT_0_1_0__COUNT@v2`: QUTest 0.1.0, θ = atol = 0.05, N = 2,000, R = 12.
- Baseline seeds 42–53.
- OB13 and OB15 seeds 42–53, guards 42–44.

**S_MIN.** One Z marginal per output qubit, with analytic reference from the original, rounded to 4 decimals.
- The original guard is satisfied if it fails at most 1 of 12 runs (OB02).
- No suite is changed after any result.

**Frozen code.** 24 reused files are copied into `frozen_deps/`, with SHA-256 in `frozen_deps/DEPS.sha256`. Every runner calls `deps.verify()` and stops on drift. **The diagnostic and certification code is byte-identical to the study's.**

## 5. Mutant population

**5.1 Operators and allocation.** `complete_pool` with the frozen policy:
- operators: insertion, replacement and deletion;
- gate classes: local basis amplitude, phase parameterized, entangling controlled;
- inserted angle π/2;
- insertion grid: every position for L ≤ 40, 12 positions otherwise.

The steps are:
1. deduplicate by mutated hash;
2. sort each of the 9 strata by (location, SHA-256);
3. allocate **30 per subject** by `largest_remainder` (source hash = the external cohort's recorded `apportionment_fn_sha256` 9086b2b4…), with the external deficit rule.

No RNG. Only the converted body is mutated.

**5.2 Files.** `population/mutants/<subject>/<subject>_mNN.json` and `.qasm`, and `population/MUTANT_MANIFEST.csv`.

**5.3 Declared engineering deviation PD-1 (resolved before Freeze A).**
- **The problem.** The historical enumerator caps eligibility at `QUBIT_LIMIT = 10` (`gate_config.py`, documented as the "frozen fragment qubit cap" of the July RQ3 feasibility gate, a ≤ 6-qubit corpus).
- **Why the cap is not algorithmic.**
  - It appears only in `fragment.circuit_eligible` (`n > QUBIT_LIMIT` → ineligible).
  - Candidate generation scales with n: single-qubit instances on every qubit; two-qubit instances on neighbouring pairs plus (0, n − 1).
  - The insertion grid depends only on circuit length.
  - Neither encodes an assumption n ≤ 10.
- **The change.** A cohort-only copy, `cohort_enumerator/rq3_cohort/core/`, with **one line changed** (`QUBIT_LIMIT = 14`, the paper's certified envelope; `cohort_enumerator/PD1_QUBIT_LIMIT.diff`). `mutants.py`, `fragment.py`, `representation.py` and `__init__.py` are byte-identical to the historical files. The historical enumerator is unchanged.
- **Verification** (`cohort_enumerator/PD1_VERIFICATION.json`; enumeration only):

  | Subject | Historical pool | Cohort pool | Identical? |
  |---|---|---|---|
  | `qwalk_4` | 3,453 | 3,453 | yes |
  | `qwalk_5` | 7,395 | 7,395 | yes |
  | `rg_mult_8` | 3,264 | 3,264 | yes |
  | `rg_mult_12` | 0 | 7,908 (7,872 distinct) | — |

  For the first three subjects the ordered pools and ineligible lists are identical. For `rg_mult_12`, every one of the 9 strata has at least 8 candidates.
- **Classification.** A population-tool eligibility parameter. It does not change any diagnostic, profile, evidence or certification rule.

**5.4 Pre-outcome exclusion (C0).** A mutant that QUTest 0.1.0 cannot parse in a trial run without assertions is excluded and recorded. It is not replaced.

**5.5 Independence (Freeze B).** No original, mutant or (original, mutant) pair may be content-identical (canonical gate-list SHA-256) to any of the 2,626 earlier programs (construction, prospective, external, QMutBench width set and corpus). A static check confirms that every gate after `adapt` is QUTest-supported and n ≤ 14. Nothing is executed.

## 6. Stages

| Stage | Content | Seeds | Records |
|---|---|---|---|
| A (done) | original checks (§3) | — | `stageA_prefreeze/`, `subjects/` |
| **Freeze A** | commit, SHA-256 manifest `freeze/FREEZE_A.sha256`, RFC 3161 timestamp of its digest | — | `freeze/` |
| **Freeze B** | `materialize.py`, `independence.py`; commit, `freeze/FREEZE_B.sha256`, RFC 3161 timestamp | — | `population/`, `freeze/` |
| C0, C1 | parse trial; original guards; S_MIN on every mutant (12) | 42–53 | `records/stage_c/` |
| C2, C3 | `diagnose`; native OB13 and OB15 (`native_check`); `finalize_row` → **C**; `bprime.py` → **B** and **B′** | 42–53 / 42–44 | `records/stage_c/`, **committed before Stage D** |
| D1 | repair validation (§6.1) | mutant 2042–2053; original 6042–6053 | `records/stage_d/D1_REPAIR.csv` |
| D2 | observation-limitation consistency check (§6.2) | calibration 3042–3053; paired 5042–5053; independent 4042–4053 | `records/stage_d/D2_OBSERVATION.csv` |
| Analysis | `analyze.py` (§7) | — | `records/analysis/` |

**Validity criterion used in Stage D.** It is the existing OB02 rule: original false-failure rate ≤ 0.10, i.e. **at most 1 failure in 12 runs**. No other threshold is introduced. Stage D refuses to start unless `records/stage_c/` is committed and clean.

**6.1 D1, suite-omission repair.** Population: every v2 CL4 candidate with stable survival, certified or not.
- The repaired suite is S_MIN + w\*, with w\* as named in Stage C.
- The mutant runs 12 times (k kills) and the original runs 12 times on **separate** seeds (f false failures).

| Outcome | Condition |
|---|---|
| `void` | any UNSUPPORTED or execution error |
| `original_false_failure` | f ≥ 2 (the repaired suite is not a valid test on fresh seeds) |
| `supported_repair` | f ≤ 1 and k = 12 |
| `kill_failure` | f ≤ 1 and k < 12 |

k and f are reported with Clopper–Pearson 95 % intervals.

**6.2 D2, observation limitation.** Population: every v2 CL3 candidate with stable survival.
- **This is an implementation-consistency check, not a statistical test of equivalence.** Observation equivalence is analytic (R_O within 10⁻¹⁰) and is not re-decided natively.
- **Calibration:** the E15b ladder on the original selects the operative rung.
- **Validity:** the original at fresh seeds, f.
- **Paired check:** the mutant at the **same** fresh seeds; per-seed verdict agreement a/12.
- **Independent seeds:** mutant kills k at independent seeds are reported with an interval and **never used to classify**.

| Outcome | Condition |
|---|---|
| `void` | error, or W0 fails calibration |
| `suite_invalid_on_fresh_seeds` | f ≥ 2: **not** counted as a successful validation; the structural diagnosis is reported separately and unchanged |
| `implementation_inconsistent` | valid suite and a < 12: native discrepancy, reported in full |
| `consistent` | valid suite and a = 12 |

Fisher's test is not used: a non-significant comparison of 12 against 12 runs cannot support equivalence.

## 7. Pre-registered reporting

All tables are given per subject, per family and overall, separate from historical denominators.

| ID | Quantity | Reported as |
|---|---|---|
| R1, prospective diagnostic coverage | mutants; parse exclusions; killed; split (OB03); outcomes CL1–CL5; Unresolved with named unmet items | counts. Abstentions (Unresolved) are listed by reason and never folded into other outcomes |
| R2, certification | CL4 candidates with stable survival; certified; withheld by unmet obligation (OB13, OB02, OB15, OB16, other) | counts |
| R3, analytical screening | B′-repair and B′-full issue/abstain per candidate; bound-covered decisions | counts |
| R4, native repair | D1 outcome × issuing approach (B, B′-repair, B′-full, C), with issued and abstained recommendations kept apart: supported repairs, kill failures, original false failures, void | 4 × 2 × 4 table, with k and f intervals |
| R5, certification against validation disagreements | certified CL4 with a D1 outcome other than `supported_repair`; C abstentions with `supported_repair` (conservative); bound-covered OB13 decisions followed by `kill_failure` | each case listed with its margin and witness kind |
| R6, observation-limitation consistency | D2 outcomes; f, a and k with intervals | counts and per-case table |
| R7, cost | Stage-C native runs and seconds; runs a bound-first hybrid would have skipped | stated as **potential**, not demonstrated |

**Inconclusive rules:**
- with fewer than **10** CL4 candidates with stable survival, R4 and R5 are reported as **inconclusive** (descriptive only), with no claim about repair effectiveness;
- with no CL3 candidate, R6 is reported as absent;
- with more than 50 % of survivors Unresolved, an applicability limit is reported;
- with more than 25 % of D1 or D2 cases `void` or `suite_invalid_on_fresh_seeds`, execution stability is reported as insufficient for that check;
- the population is **never** enlarged or replaced.

**Interpretation:**

| Result | Reading |
|---|---|
| certified repairs failing D1 | negative evidence |
| C no better than B′ | certification's native step adds nothing on these programs |
| mostly killed mutants | diagnosis barely exercised |
| absent observation limitation | reported as absent |

A correct freeze is not a success.

## 8. Deviations

- **PD-1** (§5.3) is the only deviation from reused tooling. It was declared and verified **before** Freeze A.
- Any later change is logged in `freeze/DEVIATIONS.md` with date, reason and expected effect, reported, and never folded back into this protocol.

## 9. Workload (measured on original programs)

| Item | Measured or estimated |
|---|---|
| QUTest run | ≈ 0.8–1.7 s |
| Stage-C dry run (4 pairs, incl. the 12-qubit unitary) | 4.8 min |
| Stage-D dry run (4 D1 + 4 D2 ladders) | 2.3 min |
| Expected, 120 mutants | **≈ 2–4 h wall time** |
