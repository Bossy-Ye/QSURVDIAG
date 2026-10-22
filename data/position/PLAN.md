# X4. Later mutation positions: plan (fixed before its native runs)

## 0. Selection history

Not blind. The selection rule of the five other circuits, the Q# and QASMBench programs and MQT Bench takes the first
mutations of each stratum in text order, so most selected mutations change the first gate (140 of 149, 244 of 270,
68 of 120). The outcomes of those populations are known. A feasibility run before this plan regenerated the pools
and, for qft_n4 only, executed a position-balanced set of 30 mutations natively (7 killed, 23 surviving, matching the
prediction); qft_n4 is therefore reported with and without its later-position sample.

## 1. Question and population

Do the outcomes of these populations change when mutations at later positions are included?

Programs: the five other circuits (simon_4, wstate_4, swaptest_5, cuccaro_adder_5, toffoli_barenco_5), the nine Q#
and QASMBench programs (ParityPhase, Is2PowerPhase, AdderHamiltonianMixture, DraperAdder, IsingEvolution,
LessThanPhase, DiagonalZHamiltonian, deutsch_n2, qft_n4) and the four MQT Bench programs (qwalk_4, qwalk_5,
rg_mult_8, rg_mult_12).

## 2. Selection rule (deterministic, no RNG)

- Pools: the archived deduplicated pools (`data/external/cohort/EXTERNAL_OPPORTUNITY_POOL.csv`,
  `data/prospective/mqt_bench/population/MUTATION_POOL.csv`) and, for the five other circuits, the pool regenerated
  by the packaged enumerator; mutations already selected are removed.
- Each mutation carries its stratum (operator x gate class, 9 strata) and its position third (first, middle, last,
  by anchor index).
- Per program: 10 mutations from the middle third and 10 from the last third. Within a third, the 10 are apportioned
  over the 9 strata in proportion to availability by largest remainder (ties by stratum order), with shortfalls
  redistributed by the same rule.
- Within a cell, mutations are sorted by (anchor index, location, mutated hash) and the j-th of k is taken at index
  floor((j + 0.5) * size / k).
- A mutation that the execution adapter or the QUTest parser rejects is replaced by the next one in the same order;
  replacements are listed.
- Selections and their hashes are written to `X4_SELECTION.csv` before any run.

## 3. Execution and diagnosis

- Each program keeps its contract, executed input, output register and baseline suite, and the population's protocol:
  N = 2,000, 12 runs, three guard runs of the original, the current evidence rules and the closed witness order (v3).
- Seeds: mutant runs 17042-17053, original runs 18042-18053 (not used before).
- Suite omissions are natively confirmed and their negative controls run as in the original populations.

## 4. Analysis

- Outcomes per population by position (first-rule sample, middle, last), with distinct sites and distinct repair
  suites.
- Observation limitations and suite omissions at non-first positions; whether the five other circuits contain an
  observation limitation once later positions are sampled.
- The archived outcomes of the first-rule samples are not changed.
- If the source archive of the six Qolumbina programs is not available, the analysis covers the other 12 programs and
  states the restriction.

## 5. Outputs

`X4_SELECTION.csv`, `X4_NATIVE_RUNS.csv`, `X4_FINAL.csv`, `X4_SUMMARY.json`, the selector, runner and analysis script.
