# X2: records made after the plan was timestamped

Each section is one record, in the order recorded; the time is that of its last change (UTC). The plan is `PLAN.md`.

## X2_CLARIFICATIONS: clarifications recorded before any X2 execution

Recorded 2026-10-20 12:08:19 UTC.

Inspection of the source at commit `74c27570` after the plan was timestamped shows three statements of the plan that do
not match the source. They are resolved below by following the source; no X2 test has been executed.

1. Suite A covers four programs, not five. The MITRE files adapted to the case-study programs are
   `deutsch_jozsa.py`, `grover_tests.py`, `qft_tests.py` and `teleportation.py`, the four the source's README lists for
   its comparison. `superdense_coding.py` is the unadapted MITRE original: it tests its own implementation and calls
   `qiskit.execute`, which the required qiskit version no longer provides. Superdense coding and phase estimation are
   therefore tested by suite B only.
2. Suite A measurement budgets are those of the tests themselves. The source's runner passes a nominal value
   (`shots_list`: 7,500 or 12,600 for Deutsch-Jozsa, 7,500 for Grover and QFT) that the Deutsch-Jozsa, Grover and QFT
   tests do not consume: they run their circuits with the shot counts written in the tests. Teleportation uses the
   runner's value, 100 measurements per test. The plan's "7,500 measurements" is replaced by "as in the source".
3. Seeding. Besides QuCheck's `random_seed` and the simulator seed, Python's `random` and NumPy's global generator are
   seeded with the run seed, because the Grover test draws its pad from NumPy.

Suite B uses every property that QuCheck's Coordinator discovers in the program's folder (`number_of_properties=-1`)
and `run_optimization=True`, as in the source's runner. All other parts of the plan are unchanged.

## X2_OPERATIONAL: operational definitions recorded before any mutant execution

Recorded 2026-10-20 12:12:52 UTC.

These fix how section 4 of the plan is computed for programs that take arguments and suites that run many circuits.
No mutant has been executed when this file is recorded; originals ran only in a harness smoke test at seed 1.

1. Program inputs. Every call of the program function during a suite run is recorded with its arguments. X_S is the
   set of argument tuples recorded in the 12 runs of suite S on the original; F is the union over both suites.
2. Program equality on an argument tuple a: the circuits P(a) and M(a) returned by the original and the mutant have
   equal unitaries up to global phase (Operator.equiv) or, when a circuit contains a non-unitary instruction
   (initialize), equal final states from the all-zero state up to global phase.
   - Contract equivalence: equality on every a in F.
   - Executed-input equality under S: equality on every a in X_S, not on every a in F.
3. Contexts and observations. Every circuit that suite S submits to the simulator in a run is a context: the test's
   own preparation, the program, any test-side gates (un-computation, basis changes added by QuCheck) and the
   measurements. Its observation is the exact distribution of the measured bits, computed from the circuit without
   its final measurements. Original and mutant runs at the same seed generate the same inputs; their contexts are
   paired in submission order. If the two runs submit different numbers of contexts, or paired contexts differ in
   width or measured bits, the case is unresolved (alignment) and reported.
   - Observation limitation under S: every paired observation is equal (margin 1e-9) while program equality fails
     on some a in X_S.
4. Admissible instances and witness.
   - Suite A: the declared QUTest types (marginals, Z products, basis-state probabilities, entropy, three distances)
     on each context's distribution, in the closed witness order; contexts in submission order.
   - Suite B: the single-qubit marginal of each measured bit of each context (QuCheck's assertions in the case
     studies compare single-qubit outcome distributions in the bases they measure), contexts in submission order,
     bits ascending.
   - The witness is the first instance whose difference exceeds theta = 0.05; if a paired observation differs but no
     instance exceeds theta, the outcome is a below-tolerance difference.
5. Native confirmation of a suite omission: the witness context is executed alone at 2,000 shots with the witness as
   an assertion (original's ideal value rounded to 4 decimals as reference, tolerance 0.05), 12 runs on the mutant
   (seeds 15042-15053) and 12 on the original (seeds 16042-16053); supported when the mutant is killed in 12 of 12
   and the original fails in at most 1 of 12. Several suite-A tests run one shot per context, which cannot carry a
   tolerance assertion; 2,000 shots is the study's baseline budget. The study's negative control is not applied in
   X2; this is reported.
6. Contexts are executed through the case-study code with Aer; the exact distributions are computed with
   qiskit.quantum_info in the same environment.

## X2_RUNTIME_DECISION: runtime check result and the suite-B input count (recorded before any mutant execution)

Recorded 2026-10-20 13:30:36 UTC.

The planned runtime check (12 runs per original, four processes) was stopped by the memory limit: suite B on QFT with
100 inputs needs 5.7 GB per process. It was therefore measured with one run per original at seed 16042, serially:

| suite B, 100 inputs | seconds per run | peak memory |
|---|---|---|
| Deutsch-Jozsa | 10.9 | 0.19 GB |
| Grover | 397.6 | 3.6 GB |
| QFT | 185.1 | 5.7 GB |
| phase estimation | 504.3 | 0.57 GB |
| teleportation | 20.5 | 0.21 GB |
| superdense coding | 2.5 | 0.16 GB |

Projected serial time of suite B on all mutants (30 per program, 12 runs): about 112 hours, above the 48-hour
threshold of the plan. Suite B therefore uses 20 inputs. Suite A per run: Grover 49.1 s, QFT 81.0 s, Deutsch-Jozsa
0.25 s, teleportation 0.31 s. The teleportation original failed suite B in this single run; its failure rate is
measured by the 12 guard runs.

Execution detail with unchanged semantics: the capture of the original at a given seed is identical for every mutant
of that program (same generated inputs), so it is computed once per (suite, program, seed) and paired with each
mutant run at that seed.

## X2_OPERATIONAL_ADDENDUM: addendum to the operational definitions (recorded before any mutant execution)

Recorded 2026-10-20 14:02:16 UTC.

A harness check on originals only (original against itself, seed 1) found two defects; both are corrected before
any mutant runs.

1. Suite A uses Aer's `qasm_simulator` backend, a different class from `AerSimulator`. Seeding and capture now act on
   their common base class `AerBackend`, so every suite-A simulation is seeded and captured. Each simulation call in a
   run receives its own seed, run seed x 1,000,003 + call index: a single seed for every call would make the retries
   of a test (the Grover test makes up to ten attempts) identical copies. (The runtime-check timings of suite A were
   taken without seeding; timing is unaffected.)
2. With `run_optimization=True`, QuCheck merges measurement circuits through a hash-ordered set of base circuits, so
   the submission order of the same original at the same seed differs between executions and cannot pair contexts.
   (QuCheck's unoptimized mode cannot be used instead: it raises a KeyError in the source when one base circuit has
   several measurements.) The harness therefore iterates the base circuits in their insertion order, which follows
   QuCheck's sorted property order and its seeded input order, and submits the merged circuits in the order they are
   built. Merging, the circuits and their measurements are unchanged; only the submission order is fixed, so the
   native verdict keeps the published configuration (`run_optimization=True`, 2,500 measurements, 20 inputs) and the
   same run provides the contexts.

## X2_EXACT_METHOD: computation of exact distributions (recorded before any mutant execution)

Recorded 2026-10-20 16:34:37 UTC.

Item 6 of X2_OPERATIONAL computes each context's exact distribution with qiskit.quantum_info. On suite B of the
QFT this takes about 15 minutes per run: the contexts begin with `initialize`, which quantum_info evaluates by
synthesising a state-preparation circuit. The exact distributions are therefore computed with Aer's statevector
method (`save_probabilities` on the measured qubits, double precision, `initialize` executed natively), called
outside the seeded and captured simulator path, so the native runs are unchanged.

Check on recorded original captures before the change (suite B QFT seed 15045, suite B Deutsch-Jozsa seed 15042,
suite A Grover seed 15042; 467 contexts): largest absolute difference between the two methods 3.2e-14, below the
equality margin 1e-9. Original captures already computed are kept.

## X2_STATE_RELATION: state equality on the executed contexts (amendment recorded before any X2 outcome is reported)

Recorded 2026-10-21 07:37:15 UTC.

X2_OPERATIONAL decides program equality on an argument tuple by the unitaries of the returned circuits and then
compares observations. It omits the state relation of the article's comparison order (state equality before
observation equality): a returned circuit is executed only from the states that the test prepares, so two circuits
with different unitaries can reach the same final state in every executed context.

Check on the first candidates (Deutsch-Jozsa m2, m12 and m16, which survive both suites with equal observations and
unequal unitaries), seed 15042: in all 13 suite-A and 109 suite-B contexts the final states of mutant and original
agree up to global phase (m2 and m16 add a diagonal gate after the final Hadamard gates, where each data qubit is in a
basis state; m12 prepares the ancilla with Y instead of X).

Amended rule: a survivor whose observations agree in every paired context and whose returned circuits differ on
some executed argument is compared on the final states of every executed context (each context without its final
measurements, Aer statevector, equality up to global phase at 1e-9), at all 12 seeds. If every context state agrees,
the outcome is executed-input equality; otherwise it is observation limitation. No other rule changes.

## X2_EQUALITY_METHOD: computation of program equality (execution detail; definitions unchanged)

Recorded 2026-10-21 09:42:46 UTC.

Program equality (X2_OPERATIONAL, item 2) compares the two programs' circuits for each recorded call with
Operator.equiv (global phase, atol 1e-9). Building each operator gate by gate took about 45 s per suite-A pair. From
17:05 UTC, the operators of circuits with at most 12 qubits and without initialize, state preparation, reset or
measurement are computed with Aer's unitary method (double precision, outside the seeded path) and compared with the
same Operator.equiv; other circuits keep the previous computation. From 17:10 UTC, each equality is computed once per program, mutant
and call signature, and reused at every seed, since it does not depend on the seed.

Check against the previous computation (all recorded calls of the original capture at seed 15042): suite A
Deutsch-Jozsa m3, m7, m12, em0 (13 calls each) and suite B QFT m3, em0 (100 calls each): identical results.
The first 23 suite-A Deutsch-Jozsa pair runs, before 17:05, used the previous computation; all
later runs use this one. Rows are not individually time-stamped; the 23 are the pair rows with more than 30 s.

From 17:27 UTC, calls wider than 14 qubits (suite A Grover: 19 and 23 qubits), whose operators do not fit in memory
and which the previous computation therefore compared as final states from |0...0> with Statevector.equiv, take
those final states from Aer's statevector method and compare them with the same Statevector.equiv. Check on the
19-qubit call of the original: largest absolute amplitude difference 1.6e-13 (1.8 s against 641 s). No suite-A
Grover pair had run before this change.

From 19:41 UTC, for circuits wider than 14 qubits, each exact distribution and the original's final state are stored
under a key of the circuit's full content (gates, full-precision parameters, qubits, clbits) and reused for an
identical circuit, since they do not depend on the seed. Check on the four contexts of the suite-A Grover original
capture at seed 15042: stored and recomputed distributions identical to the recorded ones. 20 suite-A Grover pair
runs had completed before this change.

From 07:33 UTC on 21 October, a suite-A run stops at its first failing test: the suite has then failed, so its verdict
is decided, and the remaining tests of a killed run are not executed. Passing runs execute every test as before. The
MITRE Grover test retries a failing search up to ten times, so a killed run otherwise executed its 19- and 23-qubit
circuits up to thirty times (about 1,500 s per run). 132 suite-A Grover pair runs and all suite-A Deutsch-Jozsa runs
had completed before this change; their per-test records list every test.

Native QuCheck on the 20 circuits (PLAN.md, section 5): the first execution, finished at 09:41 UTC on
21 October, named every generated property file prop_pair.py. QuCheck imports property files by module name, so
within a worker process later runs reused an earlier run's property, and every control was reported as detected
(816 of 816). The runs are invalid and are not used. From 09:42 UTC each run writes its property under its own module
name and records its own p-values; the runs were repeated at the same seeds.
