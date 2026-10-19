# QSurvDiag v2: revision-stage specification

**Status.** This specification is fixed before any v2 reprocessing and before any v2 native execution.
Its SHA-256 is recorded in `V2_SPECIFICATION.sha256`, and it does not change afterwards; a change
would be a v3. OB19 for v2 certificates means "no rule of this specification was amended after that hash
was recorded".

## 1. Versions

**v1** is the registered evaluation. It covers the procedure and executions recorded in the definitive
layer (`github/results`, `zenodo/runs`), including:
- the prospective set;
- the width set;
- the RQ4 predictions and interventions;
- the external-cohort freeze.

v1 stays read-only and is reported in the supplement as the recorded evaluation.

**v2** is this specification. It reuses v1's recorded inputs, native verdicts, guards and intervention
executions wherever they are valid evidence under v2. It executes natively only the evidence that v1 did
not record (§9).

v2 changes five things relative to v1:
1. The admitted universe instantiates the distribution family at three distances (§2.5).
2. Equality comparisons have a numerical guard band (§3).
3. Profile restrictions are stated as such (§2.3).
4. One witness-selection rule names every suite-omission witness (§5).
5. Every evidence requirement is evaluated per case (§6).

On point 5: v1 evaluated OB02 and OB03 per case. It took OB04 and OB08–OB17 from an availability
model (`recertify.py`, `e1_07_diagnose.evidence_for`), and its arms operationalized OB13, OB15 and OB16
differently:

| Arm | OB13 (witness confirmation) | OB15 (matched-cost control) | OB16 |
|---|---|---|---|
| S3 (held-out certificates) | witness alone, 12/12 | duplicate marginals | tolerance-grid invariance |
| E13 (width) | suite + witness, 3 repetitions | not run | ε_num stability |
| Definitive run | assumed | assumed | assumed |

v2 leaves unchanged the subjects, mutants, contracts, realized inputs, executed suites, decision
configurations and seeds, the tool versions and the recorded grids.

## 2. Profile `QT_0_1_0__COUNT@v2`

2.1 **Released capabilities.** QUTest 0.1.0 implements 12 assertion-producing kinds, helper-function
inlining and configuration pragmas. The supplement's source-to-profile table gives the file and line of
each.

2.2 **Behavioral admissibility.** An admissible kind decides from the program's execution outcomes. The
gate-set and depth predicates read the transpiled circuit, so they are structural and not admissible for a
behavioral contract.

2.3 **Profile restrictions.** The certifying universe admits a behavioral kind only if it is
tolerance-defined on a difference functional of the counts and free of discontinuous fallbacks. This is
the reliability criterion of OB12 in the frozen Phase-5A registry.

Excluded, with the category the certificate records:

| Kind | Category | Reason |
|---|---|---|
| Pearson correlation | restriction | constant-bit fallback, ill-conditioned near it |
| most-frequent outcome | restriction | argmax with no tolerance |
| chi-squared option | restriction | p-value depends on N; no difference functional |
| entanglement witness | restriction | reads the statevector; fixed 1e-6 entropy threshold |
| output | inapplicable | deterministic registers only |
| fidelity | inapplicable | needs a noisy backend and a second execution |
| gate set, depth | structural | not behavioral (§2.2) |

2.4 **Observation and composition.**
- The observation is the joint computational-Z counts over every measured qubit.
- There is one context: the program as given, at the realized input.
- R_S ⇒ R_O holds because that context acts on the realized endpoint state.

2.5 **Universe and difference functionals.** U(P) is enumerated per case. On analytic distributions p_P
and p_M:

| Instance | Difference functional |
|---|---|
| marginal on qubit q | \|P_P(q=1) − P_M(q=1)\| |
| Z product on each non-empty qubit subset | \|⟨Z_S⟩_P − ⟨Z_S⟩_M\| |
| basis-state probability for each z | \|p_P(z) − p_M(z)\| |
| entropy | \|H(p_P) − H(p_M)\|, in bits |
| total variation | ½ Σ\|p_M − p_P\| |
| Hellinger | sqrt(½ Σ(√p_M − √p_P)²) |
| Kullback–Leibler | Σ p̃_M ln(p̃_M / p̃_P), where p̃ is p clipped below at 1e-12 |

The Hellinger and Kullback–Leibler forms are QUTest's own, measured against the original as
reference. |U(P)| = 2^{n+1} + n + 3.

2.6 **QuCheck (comparison only).**
- Observation: single-qubit X, Y and Z expectations, on every qubit (or on the declared register for the
  lattice).
- Contexts: the realized input with a fixed rotation after the program.
- Admitted kind: `assert_equal`.
- No QuCheck certificate is issued.

## 3. Numerical policy

Margins:

| Comparison | Margin |
|---|---|
| State | m_S = \| \|⟨ψ_P\|ψ_M⟩\| − 1 \| |
| Unitary contract | m_U = \| \|Tr(U_P† U_M)\|/2^n − 1 \| |
| Observation | m_O = L∞ distance between the observation vectors |

- An equality comparison is **true** if m < 1e-10, **false** if m > 1e-8, and **undecided** otherwise. An
  undecided comparison ends the path, the case is Unresolved, and the relation is named.
- θ-comparisons (R_A, R_T, OB11) use `compare_threshold` with resolution 5e-9, unchanged from v1.
- A certificate is **structural** when the diagonal sufficient condition holds on the gate lists, or the
  unitaries are identical as matrices before any evaluation. Otherwise it is **floating-point**, and it
  records its margins.

## 4. Candidate and report

- The candidate c(Γ) follows Eq. (3), with the path order unchanged.
- The report r(Γ, E) is c(Γ) if every requirement in Req(c) is satisfied on the evidence record E.
  Otherwise it is Unresolved, and the unmet items are named.

## 5. Witness selection

The named witness w* is the first instance in the following order whose difference is decided above θ
and that is absent from the realized suite:
1. single-qubit marginals, by qubit index;
2. two-qubit Z products, by distance |i − j|, then by i;
3. Z products of weight ≥ 3, by weight, then by mask;
4. basis-state probabilities, by index;
5. entropy;
6. total variation;
7. Hellinger;
8. Kullback–Leibler.

Items 1–4 are the pre-registered order of the single-witness repair (B4 plan, hash 838166c6). Items 5–8
extend it to the aggregate kinds.

This rule replaces v1's "largest above-tolerance difference outside the suite". That rule had no frozen
tie-break, and its choices were not persisted for construction cases (`E6_BACKFILL_RECORD.md`).

The matched-cost control c* is the first instance in the same order that is absent from the realized
suite and whose difference is decided below θ.

## 6. Evidence requirements

Req(q) is the matrix of Table III (`REQUIREMENT_MATRIX.md`). Each requirement is evaluated per case as
follows.

| Item | v2 evaluation | Evidence |
|---|---|---|
| OB01 native eligibility | the preflight passed and the recorded run completed | recorded |
| OB02 baseline health | the original's false-failure rate is ≤ 0.10 under the realized suite (recorded guard) and, for CL4, 0 of 3 under w* alone and under c* alone | recorded + §9 |
| OB03 verdict stability | recorded kills ∈ {0, 12} | recorded |
| OB04 contract grounded | the contract and its grounding source (external citation or study declaration) are recorded before diagnosis; the certificate states which | recorded |
| OB05 contract relation decided | the contract margin lies outside the guard band | rerun |
| OB06, OB07 value computed, equality decided | the state and observation margins the path reads lie outside the band | rerun |
| OB08 profile closed | this profile record (§2) and the source table | spec |
| OB09 factorization | every admitted kind is a function of the counts (§2.5) | spec |
| OB10 enumeration complete | the enumerated count equals 2^{n+1}+n+3 | rerun |
| OB11 witness above θ | `compare_threshold(d(w*), θ)` is true | rerun |
| OB12 witness reliable | w*'s kind is admitted under §2.3 | spec |
| OB13 native confirmation | w* alone, analytic reference, N = 2000, seeds 42–53, kills 12/12, with its guard clean. A recorded run of the realized suite + w* at the same settings also qualifies when the realized suite alone is recorded passing at those seeds; the 26 RQ4 repairs are such runs | §9 or recorded |
| OB14 suite membership | w* is not in the realized suite | rerun |
| OB15 matched-cost control | c* alone, same settings, kills fewer than 12 of 12 (the frozen S3 criterion) | §9 |
| OB16 decisive-margin stability | the decisive θ-comparison lies outside the resolution band, and the certificate records its margin and the grid interval over which the candidate holds | rerun |
| OB17 multiplicity stability | QUTest applies no multiplicity correction, so it holds by that fact; the certificate reports the suite-level union bound | spec |
| OB18 no structural evidence | no structural kind contributed | by construction |
| OB19 no amendment | this specification is unchanged since its hash | spec |

The decisive θ-comparison in OB16 is w* for CL4, and the largest admitted difference for CL5. OB16 does
not require invariance across the whole tolerance grid. CL4 and CL5 are tolerance-relative by definition,
and invariance would admit only CL5 cases whose differences fall below every grid tolerance.

For OB13 and OB15, a void guard or an execution error gives **unknown**, and the case becomes Unresolved.
A kill count other than 12/12 fails OB13. A kill count of 12/12 fails OB15.

## 7. Scope of reports by analysis

| Analysis | v2 output |
|---|---|
| Primary reference condition (N = 2000, θ = 0.05, R = 12) | full certificates |
| Width set, corpus frame, external cohort, closed-profile defects | full certificates at their reference configurations |
| Tolerance grid and decision grid | per cell: the Stage-2 candidate and its decision evidence (OB03, OB16, and the finite-shot bound of the decisive assertion). Counts are reported as *decision-supported* candidates; OB13 and OB15 are not re-executed per cell |
| Suite and specification arms | recorded native kills, read against v2 reference reports |
| Interface arm, lattice, contract arm | recomputed under §3, with invariance verified |
| Finite-shot coverage analysis | decisive assertions under §5 and §6; the bound's four derived forms. A Hellinger or KL decisive assertion is recorded as not covered |
| Evidence ablation | every applicable requirement of every v2 full certificate, ablated once as unknown and once as failed |

## 8. RQ4 invariance

The 40-case claim is retained only for cases that pass all three checks.

- **Census.** The v2 census is every prospective case, and every width-set case at 8–10 qubits, whose v2
  report is CL3 or CL4. It must equal the v1 census case by case.
- **Diagnosis.** Each census case's v2 report equals its v1 report, with every requirement in §6
  satisfied.
- **Intervention.** Each recorded intervention is the one v2 prescribes:
  - the stress suite is the maximal pointwise suite, which the aggregate distances leave unchanged;
  - the repair witness equals w*;
  - the CL3 calibrated suite is unchanged.

A case that fails any check leaves the retained claim, and the paper reports the reduced census. The
wrapped-test demonstration (`dj_3#e19`) is outside the census.

## 9. Native execution

New native execution is limited to evidence v2 requires and v1 did not record:
- OB13 for every CL4 certificate without a qualifying recorded run;
- OB15 for every CL4 certificate;
- the guards of both;
- the wrapped-test demonstration.

Settings:
- QUTest 0.1.0 through the frozen adapter (`make_test`, `run_qutest`), N = 2000.
- Mutant runs at seeds 42–53; guard runs at seeds 42–44.
- References are analytic from the original, rounded as the adapter rounds them.
- Distribution witnesses carry a reference-distribution pragma holding the original's analytic
  distribution.
- Gates QUTest 0.1.0 cannot parse (rzz, rxx, u) pass through the validated lowering and name map of
  `manuscript/tse/protocol/impl/qutest_execution_adapter.py` (`adapt`, `emit_name`), exactly as the
  definitive arms did. A pair the lowering cannot express gives OB13 and OB15 the status unknown.

Every output goes to `revision2/`, and nothing in the evidence layer is written.

## 10. Timings

Fig. 6(b) shows the v1 recorded run's measurements from `B2_SCALE_CELLS_FRESH.jsonl`: `total_seconds`,
and `B_universe` + `C_relations`. v2 does not re-measure them, and the figure is labeled as v1. The cost
of the two added distances is reported separately as analytic evaluation time; it is not v2 end-to-end
performance.

## 11. Records

Every figure and table input is generated from these v2 records:
- `R2V_REPORTS_<arm>.csv`: per case, the v1 report, the v2 candidate, the v2 report, each requirement's
  status and evidence source, w*, c* and the margins;
- `R2V_NATIVE.csv`: one row per native run, with suite, seeds, kills and guard;
- `R2V_RQ4_INVARIANCE.csv`;
- `R2V_V1_V2_REPROCESSING.csv`: every count that differs between versions;
- `manuscript/data/tse_visual_data_v2.json`, written by `r2v_figure_data.py`.
