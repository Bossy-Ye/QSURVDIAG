# All-pairs comparison: plan (committed before its native runs)

Runner: `allpairs_run.py` (with `qutest_capture.py`). Analysis: `allpairs_analyze.py`. Bound: `allpairs_bound.py`
(`allpairs_bound.out`). Outputs: `ALLPAIRS_SEMANTIC.json`, `ALLPAIRS_NATIVE_RUNS.csv`, `ALLPAIRS_HISTOGRAMS.jsonl.gz`,
`ALLPAIRS_SUMMARY.json`, `ALLPAIRS_RESULTS.json`, `ALLPAIRS_CASES.csv`.

## 0. Selection history

This comparison is not blind. The cohort and its outcomes under the matched repair comparison (`data/combined_suite/`,
N = 2,000) are known. The all-pairs comparator was chosen after examining the archived witness composition of that
comparison: of the 37 witnesses outside the adjacent-pair suite S, 24 are non-adjacent two-qubit Z products, which a
suite of every pairwise Z correlation would contain. The comparator, the budget and the analysis below are fixed
before any execution of either policy at this budget. Before this commit, only ideal-state computations were run on
the cohort (`--semantic-only`: the archived witnesses recompute unchanged for all 210 cases; containment and suite
sizes below). The capture mechanism was tested on a three-qubit circuit outside the cohort.

## 1. Question and population

On the existing suite-omission candidates, what does a diagnosis-selected assertion add over a generic suite
containing every pairwise Z correlation, at the same measurement budget?

The cohort is the complete cohort of the matched repair comparison: 210 candidates (187 corpus, 23 MQT Bench),
including the 46 that QSurvDiag withheld. The issued-versus-withheld distinction (164 / 46) is kept; a withheld
candidate that meets the support rule here stays a withheld candidate. Units: pairs, distinct originals (63) and
distinct D suite designs (117) are reported separately; pairs are not independent programs.

## 2. Policies

| Policy | Assertions | Information used to select assertions |
|---|---|---|
| D: diagnostic candidate suite | the baseline marginals (one per qubit) plus the archived candidate witness of the matched comparison | original and mutant, through the existing diagnostic procedure |
| A: all-pairs suite | the baseline marginals plus Z_i Z_j for every unordered pair i < j | program width; references computed from the original |

- Both: the same executed input (all-zero) and output register (every qubit), the computational-basis observation
  profile, original-centred analytic references rounded to 4 decimals (the `pragma` serialization of `cmp_run.py`,
  reused unchanged), two-sided `~=` at theta = 0.05, the validated execution adapter (`qutest_execution_adapter`,
  `serialization_adapter`) and QUTest 0.1.0.
- D's witness is the archived one; the runner recomputes it and stops if it differs. No witness is reselected.
- A is built uniformly from the width: n + n(n-1)/2 assertions, at most 91 (n = 13). No assertion is removed.
- Containment (ideal states, before any run): A contains D's witness in 197 cases (173 adjacent and 24 non-adjacent
  pairs). It does not in 13 (5 entropies, 2 Hellinger distances, 3 weight-3, 1 weight-4 and 2 weight-9 Z products).
  In those 13 no pairwise Z product separates the ideal distributions by more than theta. D has n + 1 assertions,
  and its two Hellinger witnesses add a reference line.

## 3. Budget: N = 8,000 for both policies

One budget, fixed before any run; no grid and no later increase. The reason is A's original validity. Every marginal
and Z-product assertion of QUTest 0.1.0 is an empirical mean over the shots. `evaluate_marginal` counts the target bit
and `evaluate_observable` averages (-1)^parity over the counts, and each passes when |estimate - reference| <= atol
(checked in the pinned source). The ideal backend samples the final measurement of every shot independently. With
references rounded to 4 decimals, a failure of the correct original needs a deviation of at least 0.05 - 0.00005.
Hoeffding's inequality with range 2 for every assertion and a union bound over A's m assertions give

  P(A rejects its correct original in one run) <= 2 m exp(-N (0.05 - 0.00005)^2 / 2),

which is 0.0084 at m = 91 and N = 8,000, and is vacuous at N = 2,000 (15.0; `allpairs_bound.out`). The bound needs no
independence between assertions read from one histogram. Limits:
- it concerns a correct original in a single run;
- it does not guarantee mutant detection, least of all near the threshold;
- it does not cover D's entropy or Hellinger witnesses;
- it does not replace the native original guards, which decide validity below.

The 2,000-shot matched comparison stays evidence about its own setting. Its D results are not compared with A at
8,000 shots.

## 4. Native execution, observations and validation

- Fresh streams, not used by any earlier run: mutant seeds 11042-11053 and original seeds 12042-12053, paired across
  policies (run r of D and run r of A use the same seed).
- Each policy's suite runs 12 times on each mutant. Original validity runs once per distinct (original, policy suite)
  at the original seeds and is linked to every case that uses it.
- Every execution runs through the pinned qutest CLI with `-v` (the verdict of record, as in every earlier experiment)
  and through QUTest's own `discover_tests`/`run_test` in the runner process. That second run wraps the ideal backend's
  `run()` only to keep the counts QUTest evaluates. Per execution the runner records:
  - the CLI verdict and per-assertion results with values;
  - the in-process verdict and per-assertion results;
  - the per-assertion results re-evaluated on the kept counts with QUTest's own `evaluate_*` functions;
  - the histogram.
  All of these must agree.
- Sampling arrangement: QUTest 0.1.0 evaluates one suite per execution, so D and A are separate native executions. They
  use the same circuit text and seed, and each sees the same histogram, which the runner checks. Histograms are
  archived once per (program, seed) in `ALLPAIRS_HISTOGRAMS.jsonl.gz`. Per-run containment is asserted only where the
  two histograms are identical.
- Support rule (unchanged): the mutant is killed in 12 of 12 runs, the linked original fails in at most 1 of 12, and no
  tool error occurs. The original-validity gate is applied in the analysis code. Invalid and unsupported cases stay in
  the cohort with their reason.

## 5. Measures

1. Paired supported actions: both, D only, A only, neither.
2. Mutant kills of 12, per policy.
3. Original failures of 12, per linked suite.
4. Tool errors or unsupported executions.
5. Results where A contains D's witness and where it does not.
6. Issued (164) and withheld (46) candidates.
7. Corpus and MQT Bench, beside the pooled counts.
8. The near-threshold group (witness difference below theta + 0.01).

Structural check: where A contains D's witness and both read the same histogram, every D kill must be an A kill and
the shared assertions must have the same status in every run. A violation is investigated as a defect.

Subordinate, derived analysis: the adjacent-pair suite S is a subset of A. Its verdicts at N = 8,000 are derived from
the per-assertion results of the native A executions, and are labelled as derived, not as native S runs.

## 6. Cost, under one reuse policy

Recorded:
- diagnosis and reference-generation time;
- assertion-evaluation time (QUTest's evaluate functions on the counts);
- native executions and shots;
- distinct logical suites;
- native original-validation executions and distinct original histograms.

Every assertion of a run reads that run's histogram, so a larger suite needs no more shots. The several D suites of
one original read the same histograms at the original seeds, so the acquisitions they need are those of A. Actual
implementation cost (one native execution per suite and seed) is reported apart from what is unavoidable in
principle. No shot saving is claimed for the smaller suite.

## 7. Interpretation fixed in advance

| Outcome | Interpretation |
|---|---|
| A supports most of the same actions as D | generic pairwise strengthening handles much of this cohort |
| D supports meaningful actions A does not, with comparable original validity | stronger evidence for diagnostic selection than the adjacent-pair comparison |
| D's advantage comes mainly from original validity | stated as that mechanism, not as distinguishing power |
| A supports more actions | ordinary all-pairs strengthening performs better here; the comparative repair claim is narrowed |
| both fail near the threshold | kept as a limitation |

Every scheduled case is analysed and unfavorable results are kept. No comparator is added and no threshold, witness or
budget is changed in response to the result. A correctness defect would be corrected and recorded.
