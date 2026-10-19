# Claim-decision baseline

> **Amended at Phase 5A.1.** P7 replaced with a method-transport prediction; P11 and P12 added;
> exclusion is claim-relative. See `PHASE5A_1_AMENDMENT.md`.

Frozen at Phase 5A. Implemented in `scripts/claim_decision.py`. The function is total, deterministic, and
returns universe scope and certificate mode as **separate** fields.

## The pipeline

```
native verdict  ->  certifiability profile  ->  claim-specific evidence obligations
                ->  positive witness | scoped exclusion | configuration certificate | abstention
```

## Priority order (frozen; no adjacent-claim collapse)

| # | Claim | Substrate precondition | Profile | U | M |
|---|---|---|---|---|---|
| 1 | `CL1_CONTRACT_EQUIVALENT` | equivalent under the declared contract | `QT_0_1_0__STATE_SUBSTRATE` | `frozen_profile` | `scoped_exclusion` |
| 2 | `CL2_STATE_EQUIVALENT_UNDER_REALIZED_INPUT` | not contract-equivalent, endpoint states equal up to global phase | `QT_0_1_0__STATE_SUBSTRATE` | `frozen_profile` | `scoped_exclusion` |
| 3 | `CL3_PROFILE_INVISIBLE` | states differ, joint Z distributions equal | `QT_0_1_0__COUNT_SUBSTRATE` | `frozen_profile` | `scoped_exclusion` |
| 4 | `CL4_REALIZED_SUITE_OMISSION` | Z distributions differ, a reliable witness exists and is absent from the realized suite | `QT_0_1_0__COUNT_SUBSTRATE` | `frozen_profile` | `positive_witness` |
| 5 | `CL5_CONFIGURATION_RELATIVE` | Z distributions differ, no enumerated instance exceeds the configuration limit | `QT_0_1_0__COUNT_SUBSTRATE` | `frozen_profile` | `configuration_relative` |
| 6 | `CL6_ABSTAIN` | any gating obligation unknown | — | `frozen_profile` | `abstention` |

Resolution rules, frozen:
- a gating obligation **unknown** → immediate `CL6_ABSTAIN`, retaining the profile that was being attempted;
- a gating obligation **failed** → fall through to the next claim in priority order;
- `U` is never `tool_wide` for any claim, because `QT_0_1_0__TOOL_WIDE` is `VACUOUS_FOR_MUTANTS`. The
  52/52 `gateset` violation count is precisely *why*, and that is a derived fact, not a stipulation.

## Reconstruction check (executed at Phase 5A, on frozen data only)

`python3 scripts/claim_decision.py --reconstruct` over the frozen 158-survivor cohort:

| Claim | Reconstructed | Phase 3 |
|---|---|---|
| `CL1_CONTRACT_EQUIVALENT` | 52 | 52 |
| `CL2_STATE_EQUIVALENT_UNDER_REALIZED_INPUT` | 38 | 38 |
| `CL3_PROFILE_INVISIBLE` | 25 | 25 |
| `CL4_REALIZED_SUITE_OMISSION` | 42 | 42 |
| `CL5_CONFIGURATION_RELATIVE` | 1 | 1 |
| `CL6_ABSTAIN` | 0 | 0 |

**Agreement 158/158, with zero rule amendments.** The frozen decision function is therefore behaviourally
identical to the Phase 3 procedure while expressing it in the (U, M, O) form. No Phase 3 count is revised.

This is an in-sample reconstruction, not a validation: it shows the formalisation is faithful, not that the
procedure generalises. Generalisation is what Phase 5 tests.

## Pre-declared baseline predictions for the held-out cohort

Recorded **before** any held-out subject is compiled, mutated or executed. These are predictions, not targets;
a miss is a reportable result.

| id | Prediction | Rationale | Falsified if |
|---|---|---|---|
| P1 | `CL6_ABSTAIN` count is **0** | the frozen obligations resolved all 158 in-sample | any abstention occurs |
| P2 | Rule-amendment count is **0** | frozen rules must not need modification | any amendment applied |
| P3 | `CL1` share is **lower** than the in-sample 52/158 = 32.9%, in the interval **[10%, 30%]** | held-out contracts are externally grounded and mostly `C_ARBITRARY_INPUT_UNITARY`, a stricter relation that admits fewer equivalences | share outside [10%, 30%] |
| P4 | `CL4` share is **higher** than the in-sample 42/158 = 26.6% | the held-out realized suites assert the same narrow output-marginal set, so omissions should be at least as common | share below 26.6% |
| P5 | For the structural role-audit profile, the `gateset` negative-control violation rate is **> 0.8** on held-out contract-equivalent cases | structural assertions are substrate-mismatched by construction | rate ≤ 0.8 |
| P6 | `depth` negative-control violation rate lies strictly between 0 and the `gateset` rate | in-sample 13/52 vs 52/52; depth is transpiler-relative and therefore partially insensitive | rate is 0, or ≥ the `gateset` rate |
| P7 | **METHOD TRANSPORT.** The frozen QuCheck certifiability profile can be independently reconstructed and used to produce replayable claim certificates or principled abstentions **without modifying the shared profile schema, evidence obligations, or priority rules** | the schema, obligations and priority order were designed to be tool-agnostic; if they are, a second tool instantiates them without amendment | any of: the profile cannot be reconstructed; certificates cannot be replayed; no semantically shared claim class can be mapped; the interface architecture produces no difference in certificate scope, mode or permitted reporting decision; or a substantive shared-method rule must change after outcomes are seen |
| P8 | Every `CL3` held-out case with differing X or Y marginals is **detected** by `QC_0_0_2__BUILTIN_XYZ` | derived from the substrate lattice in `CROSS_TOOL_MAPPING.yaml` | any such case is not detected |
| P9 | `CL5` share stays **below 5%** | all 158 in-sample survivors sat at 0/12 and only one case was tolerance-bounded | share ≥ 5% |
| P10 | The count of held-out cases that are `QT_COUNT`-excluded but **not** `QT_STATE`-excluded is **non-zero** | this population is what makes the two profiles distinct rather than notational | the population is empty (the profile distinction would then be untested) |

Added at 5A.1:

| id | Prediction | Rationale | Falsified if |
|---|---|---|---|
| P11 | Both tools' frozen profiles express the shared claim classes `CL3`, `CL4`, `CL5`, `CL6`, and `CL1`/`CL2` remain QUTest-only | `CL1`/`CL2` need an exact endpoint-state or contract relation, which QuCheck's count-only substrate cannot decide | any shared class proves inexpressible, or a QUTest-only class turns out expressible |
| P12 | The two tools require the role filter for **different** reasons — QUTest on role grounds (it ships structural and nonfunctional assertions), QuCheck on reliability grounds (it ships none, but has support-shape and argmax families) | verified from source in `ASSERTION_INSTANCE_CLOSURE_AUDIT.md` | either tool's filter turns out to be driven by the other's reason |

## Prohibited outputs
- A certificate without a `profile_id`.
- An exclusion sentence that does not name its profile.
- Any `universe_scope: tool_wide` exclusion (prohibited outright at 5A.1, not merely conditioned).
- Any exclusion that is not role-filtered, substrate-bounded and reliability-qualified.
- Any exclusion quantified over an undifferentiated set of all a tool's built-ins.
- Any narrowing decision justified by the absence of a tool defect.
- Any combined "certifiability score" ordering U and M together.
- Reclassifying a held-out case by amending a rule instead of recording `CL6_ABSTAIN`.
