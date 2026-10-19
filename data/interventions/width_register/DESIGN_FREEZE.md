# E13 — certificates at widths 8 to 10, across the instrument and contract axes

**Revised and re-frozen 2026-08-16, before any evidence was generated.** The first version
of this freeze fixed one observation profile and one contract type. That design answers the
distribution half of RQ3 and is blind to RQ1 and to the movement half of RQ3, which is the
half that carries the argument. It is replaced.

## Role in the design

The article establishes at widths 3 to 7 that the licensed report moves when the instrument
moves and the program does not, and that the boundary between contract equivalence and
realized-input equality moves when the declared contract changes. This arm asks whether
both hold at widths 8 to 10, holding families and rules fixed so that any difference is
attributable to width.

## Subjects

Fifteen, five families at three widths, located by content hash and specification-verified
before use. Origins and specs recorded in `E13_SUBJECTS.json`.

## Register structure, determined empirically and fixed here

Per-qubit marginals of each origin decide the output register. Nothing is assigned by hand.

| family | output register | workspace | evidence |
|---|---|---|---|
| `ghz` | all $n$ | none | every qubit at $P(1)=0.5$ |
| `qft` | all $n$ | none | every qubit at $P(1)=0.5$ |
| `dj` | $q_0 \dots q_{n-2}$ | $q_{n-1}$ ancilla | output qubits deterministic at 1, ancilla at 0.5 |
| `qpeexact` | $q_0 \dots q_{n-2}$ counting | $q_{n-1}$ eigenstate | eigenstate qubit fixed at 1 |
| `qpeinexact` | $q_0 \dots q_{n-2}$ counting | $q_{n-1}$ eigenstate | eigenstate qubit fixed at 1 |

**Consequence, stated in advance:** `ghz` and `qft` have output register equal to all
qubits, so ALL and SUBSET coverage coincide for them and those six subjects do **not**
exercise the coverage axis. The nine `dj` and `qpe` subjects do. This is reported rather
than hidden, and no coverage claim is drawn from `ghz` or `qft`.

## Axis 1 — observation profile (RQ3, movement)

Each case is certified under all four profiles the article varies:

| profile | basis | coverage |
|---|---|---|
| `Z_ALL` | $Z$ | all qubits |
| `Z_SUBSET` | $Z$ | the declared output register |
| `XYZ_ALL` | $X, Y, Z$ | all qubits |
| `XYZ_SUBSET` | $X, Y, Z$ | the declared output register |

## Axis 2 — declared contract (RQ1)

`qft` is a reusable unitary block and admits an arbitrary-input reading, so the three `qft`
subjects are certified under **both** `C_FIXED_INPUT_STATE`, evaluated as
$|\langle\psi_b(0)|\psi_m(0)\rangle|$, and `C_ARBITRARY_INPUT_UNITARY`, evaluated as
$|\mathrm{Tr}(U_b^\dagger U_m)|/2^n$. `ghz`, `dj` and `qpe` prepare a state from
$|0\rangle^{\otimes n}$ and take the fixed-input contract only; assigning them an
arbitrary-input contract would misdescribe what they compute.

CL1 and CL2 separate only when contract equivalence is strictly stronger than
realized-input state equality, which happens under the arbitrary-input contract. The `qft`
arm therefore carries RQ1 and the rest do not.

## Unchanged from the article

The realized suite, one $Z$-marginal assertion per declared output qubit with the reference
taken from the original, reused verbatim from `s3_engine.py`. The licensing verdict from the
frozen `claim_decision.py` through `candidates_from_substrate` and `decide`. Tolerance and
repetitions from the adapter's `ATOL` and $R = 12$.

## Registered predictions

Each is falsifiable and tied to a question.

- **P1 (RQ3, movement).** CL3 collapses to **zero** under `XYZ_ALL` at widths 8 to 10, as it
  does at 3 to 7, because widening the basis to all three Paulis over all qubits makes the
  observation non-restricting. A nonzero CL3 there refutes the injectivity proposition at
  width.
- **P2 (RQ3, movement).** CL3 is strictly larger under `Z_SUBSET` than under `Z_ALL` for the
  nine subjects that exercise the coverage axis, because narrowing coverage restricts the
  observation further.
- **P3 (RQ1).** CL1 and CL2 both occur under `C_ARBITRARY_INPUT_UNITARY` for `qft`, and CL2
  is empty under `C_FIXED_INPUT_STATE`, where the two conditions coincide.
- **P4 (RQ4).** The reachable set at widths 8 to 10 equals the reachable set at 3 to 7. A
  class reachable at one range and not the other is a finding about width.
- **P5 (methodology).** Complete enumeration succeeds for every case at the cardinality the
  profile's law gives, $2^{n+1}+n+1$: 521 at $n=8$, 1,035 at $n=9$, 2,059 at $n=10$. A
  departure means the universe is not what the profile records.

## Falsification

A case the frozen decision function cannot classify; an enumeration whose cardinality
departs from the law; a nonzero CL3 under `XYZ_ALL`.

## Scope

Fifteen subjects, five families, three widths, four profiles, two contracts on one family.
It describes how the report behaves with width inside these families and is not a sample of
quantum programs generally.

---

# E13c — recorded amendment: GHZ output register

**Amended 2026-08-16, after the E13 run, before re-running.**

## What changes

`ghz_8/9/10` had `output_register_qubits` = all n, derived from the rule "every qubit whose
marginal is non-deterministic". That rule is replaced **for GHZ only** by the convention the
article's own construction cohort uses: **a one-qubit output register**.

`E2_CASE_SUBSTRATE` records `ghz_4` at 1/4, `ghz_5` at 1/5, `ghz_7` at 1/7. `qft` remains at
all n, matching the same source (`qft_4` 4/4, `qft_5` 5/5, `qft_6` 6/6). `qpe` stays at n-1.

## Why, and why it is not tuning

GHZ prepares $(|0\dots0\rangle + |1\dots1\rangle)/\sqrt{2}$. Every qubit's marginal carries
the identical statement, so one marginal is a complete assertion about the declared output
and the remaining n-1 are redundant. Asserting all n overstates what the program declares.

This is stated plainly: the amendment **will** increase CL4. In the construction cohort,
GHZ's three subjects supply **38 of the 42** CL4 cases precisely because their suites assert
one marginal while the profile observes all n. CL4 lives in the gap between a wide profile
and a narrow suite, and the original E13 rule closed that gap for GHZ.

The justification is the redundancy argument and the precedent, not the effect on the
counts. A reader who rejects the argument should read the pre-amendment numbers, which
remain valid under their own rule and are retained.

## What is retained

`E13_CERTIFICATES.json` from the pre-amendment run is preserved as
`E13_CERTIFICATES_PREAMENDMENT.json`. Its 32 certificates (18 CL1, 14 CL3) stand under the
all-n rule. The two runs are reported side by side, never pooled.

## Prediction registered before the re-run

- CL4 becomes non-empty for `ghz_8/9/10`, since the profile observes n qubits while the
  suite asserts one.
- CL3 for `ghz` may fall, as differences previously invisible to a wide suite become
  witnessed by an assertion the suite omits.
- `qft`, `qpeexact`, `qpeinexact` are unchanged; any movement there indicates the amendment
  leaked beyond GHZ.
