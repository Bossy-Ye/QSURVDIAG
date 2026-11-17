# Output-condition suites: correction plan (frozen before the confirming run)

This file, `oc_rerun.py` and `AFFECTED_PAIRS.csv` are committed
before any native run of a corrected suite. Before the commit the following had been seen: the ideal (statevector)
predictions of `data/checks/output_condition_suites.py` (65 of the 69 suite omissions would be killed), an
original-only sampling calibration (`calibrate_original_only.out`, below) and an adapter probe that ran each
corrected suite once on each original at 100 and 8,000 shots and seed 999, outside every scheduled seed. No
mutant was run under a corrected suite.

## 1. Scope

The output-condition suite (`S_SPEC`) of the suite experiment covers 239 pairs of eight subjects. The GHZ suites
(total variation to the specified distribution) already express their condition and keep their records (90
pairs, `data/primary/records/T1_4_SSPEC_599.csv`). The QFT, Simon and W-state suites change: 149 executable
pairs (qft_4, qft_5, qft_6: 30 each; simon_4: 30; wstate_4: 29, after the excluded `wstate_4#h29`), listed in
`AFFECTED_PAIRS.csv` from the archived manifests (`R2V_FINAL_PRIMARY.csv`, `T1_4_SSPEC_599.csv`). No baseline
contract, suite, profile or assertion policy changes, so the baseline diagnosis totals do not change.

## 2. Conditions and suites

Every subject keeps its executed input |0...0>, its declared output register and the declared QUTest profile.
References come from the specification, not from the original (the output-condition suite's own reference
policy). Tolerance theta = 0.05 on every assertion.

| Subject | Specified output condition and source | Recorded suite | Corrected suite | Why the corrected suite expresses the condition at the ideal level |
|---|---|---|---|---|
| simon_4 | the output register (q0, q1) is distributed uniformly over {y : y.s = 0 mod 2}, s = 11, i.e. {00: 1/2, 11: 1/2} (`SSPEC_PROVENANCE.json`, from the frozen subject manifest; Simon 1997) | marginals p1(q0) = p1(q1) = 0.5 | the two marginals and `observable "Z0 Z1" ~= 1.0` | a two-bit distribution has three free parameters, p1(q0), p1(q1) and <Z0 Z1>; the three equalities hold exactly for {00: 1/2, 11: 1/2} and for no other distribution. The marginals alone also accept the uniform distribution on all four strings |
| qft_n, n = 4, 5, 6 | the transform of |0...0> is the equal superposition, so the measured distribution of all n qubits is uniform (`SSPEC_PROVENANCE.json`; Nielsen and Chuang) | marginals p1(q) = 0.5 for every q | the n marginals and `distribution total_variation_distance <= 0.05` against the uniform distribution | TV = 0 exactly for the uniform distribution. The marginals alone are a consequence of uniformity, not equivalent to it (GHZ has every marginal 1/2) |
| wstate_4 | the W state gives the uniform distribution on the four weight-one strings (`SSPEC_PROVENANCE.json` records only its consequence "every qubit has Z marginal 1/n"; Dür, Vidal and Cirac 2000) | marginals p1(q) = 0.25 | the four marginals and `distribution total_variation_distance <= 0.05` against {0001, 0010, 0100, 1000: 1/4} | TV = 0 exactly for the W distribution; marginals of 1/4 also allow weight-zero and weight-two strings |

The recorded marginals are kept: each is implied by the corrected condition, so at the ideal level they change no
acceptance decision of the corrected suite for QFT and W (|marginal difference| <= TV), and for Simon they are
two of the three defining equalities. The corrected suites were derived from the conditions; they were not chosen
by which known mutants they kill.

## 3. Acceptance regions under the nonzero tolerance

- Simon: accept when |p1(q0) - 1/2| <= 0.05, |p1(q1) - 1/2| <= 0.05 and <Z0 Z1> >= 0.95, i.e.
  P(00) + P(11) >= 0.975 on the output register. The ancilla register (q2, q3) is not constrained, as the
  condition does not constrain it.
- QFT: accept when TV(p, uniform) <= 0.05 (marginal constraints then hold automatically).
- W: accept when TV(p, W) <= 0.05.
- The sampled TV is biased upward. Original-only calibration at N = 8,000 (Monte Carlo, 20,000 draws): mean
  sampled TV of a uniform distribution 0.017 (n = 4), 0.025 (n = 5), 0.035 (n = 6); 0.008 for the W distribution;
  per-run false-failure probability below 1e-4 in every case. A mutant can therefore be killed natively with an
  ideal TV below 0.05, most at n = 6; the analysis reports native kills against the ideal prediction pair by pair
  and does not reinterpret either.

## 4. Execution settings and original-validity rule

As the archived suite experiment (A1g): QUTest 0.1.0, ideal backend, N = 8,000, R = 12 repetitions, mutant seeds
from `e1_seed_schedule.seed_for` (development pairs 6000 + r, additional pairs 42 + r), original guard runs at
seeds 42 to 53. Gate lists are lowered with the validated execution adapter (`qutest_execution_adapter.adapt`,
`serialization_adapter.emit_name`), which rewrites the `rxx`/`rzz` forms QUTest 0.1.0 cannot parse.

Original-validity rule: a subject's corrected suite is valid only if its original passes all 12 guard runs. If an
original fails any guard run, its pairs are reported as not evaluable under the corrected suite, the failure is
investigated and reported, and neither the reference nor the suite is changed after the fact.

Verdict per pair: killed (12 of 12), survived (0 of 12), split (1 to 11), or unsupported (any tool error).

## 5. Analysis, fixed now

- Matched comparison with the recorded suites on the same pairs: new kills, lost baseline kills (pairs the
  recorded suite killed that the corrected suite does not), splits and unsupported runs, original failures.
- Two reporting units, kept apart: Figure 4(b)'s 96 cases on the eight subjects (69 suite omissions and 27
  observation limitations) and the matched-changes table's 239 matched pairs (all pairs of the eight subjects, killed and
  surviving under the baseline).
- The matched-changes row recomputed with the existing statistics code path (exact McNemar, circuit bootstrap with
  B = 10,000, leave-one-circuit-out), GHZ cells reused unchanged.
- Native counts are reported as such; the ideal prediction (65 of 69) stays a prediction.

## 6. Validation and cost

The rerun is itself the confirming run of a fixed suite; no witness is selected from it. Recorded per run: seed,
verdict, wall time. Summary: executions, shots, total wall and CPU time, workers, machine. The original guard runs
are shared by all pairs of a subject and are counted once per subject.
