# QED-C TFIM case: demonstration design (frozen before its diagnostic and native runs)

Context and selection history: `SCREENING.md`. Three stages are kept
apart: (1) the candidate-screening rule, committed before screening (`SCREENING.md`);
(2) the exploratory selection of the TFIM program inside QED-C, made after specification, implementation and
reference probes whose fidelity, score and X-basis differences are exploratory outcome evidence
(`convention_scan*.out`, `tfim_pair*.out`); (3) this design, committed before the runs it governs. This is not an
outcome-blind selection and not a preregistration.

Runner: `case_run.py`. Outputs: `CASE_RESULTS.json`, `NATIVE_RUNS.csv`.

## 1. Programs and pairs

Settings from the stored benchmark data (`precalculated_data.json`, sha256 `88480e85…caec`): K = 5 Trotter steps,
t = 0.2, h = 1; the specified J = 1. The driver always passes these stored values to the kernel
(`hamiltonian_simulation_benchmark.py`, `get_circuits`: `K=k, t=t_val` from the data file, whatever `K` and `t`
the caller supplies). Widths: the benchmark's default range, n = 2 to 8 (`get_circuits(min_qubits=2,
max_qubits=8)`), all of them; no width is selected by its result.

| Object | Definition | Role |
|---|---|---|
| E | exact `exp(-iHt)` applied to GHZ+, H = J sum Z_i Z_{i+1} + h sum X_i, J = h = 1 | specification; not a program |
| P | the kernel's TFIM circuit with the ZZ rotation angle `2*tau*J` (J = 1): same GHZ preparation, step count, gate order and measurement as the shipped kernel | specification-consistent Trotter implementation, **researcher-corrected**; the original of both pairs |
| M | the shipped kernel's TFIM circuit, ZZ angle `pi*tau` (J = pi/2) | counterpart of the natural pair |
| C | P followed by a terminal Z on qubit 0, before measurement | counterpart of the constructed pair; **a deliberately constructed fault**, not an upstream defect |

Pairs: natural (P, M) and constructed (P, C). The shipped M is never treated as a contract-valid original.
Circuits are built from the study's transcription, whose final states equal the upstream kernel's at n = 2, 4, 6
to 1e-12 (`kernel_equivalence_check.out`); the upstream circuit, decomposed into `r` and `u` gates, is not passed
to QUTest. This is a driver adaptation: the kernel is not run through the QED-C driver or analyzer.

## 2. Diagnostic context

- Contract: fixed-input state contract, final state equal (up to global phase) to P's from GHZ+. Source: the
  README's state-level requirement with the stored J = h = 1, K = 5, t = 0.2; P is its Trotter implementation
  within the shipped scheme. R_C coincides with R_S.
- Executed input: GHZ+ = (|0...0> + |1...1>)/sqrt 2, prepared by the kernel's own `h; cx` chain.
- Register and transformations (Pi0, the method-2 scoring procedure): every qubit measured in Z; the program as
  given; no transformation.
- Assertion universe: the study's original-centred universe U(P) on the joint Z distribution of all qubits
  (marginals, Z products, basis-state probabilities, entropy, total variation, Hellinger, KL), 2^(n+1)+n+3
  instances, references P's ideal values, two-sided comparison at theta = 0.05, distances measured from P's
  distribution. This universe is study-defined; QED-C has no assertion language.
- Executed suite T (study-defined adapter of the method-2 score): one QUTest assertion, Hellinger distance to the
  upstream stored exact distribution at most theta. QED-C's Hellinger fidelity is (1 - H^2)^2, so the rule equals
  fidelity >= 0.9950. QED-C itself reports the score without an acceptance rule; this threshold is ours. T's
  reference is the upstream exact distribution, not P's distribution; both are recorded.
- Tolerance theta = 0.05; equality margins: equal below 1e-10, different above 1e-8, undecided between.
- Diagnostic inputs: the public kernel source, the stored data file, and a statevector simulator. Their
  acquisition (simulation) is timed.
- Required evidence: the evidence requirements of the article (Table 1), with the existing `certify()` of `qsurvdiag_confirmatory.py`; OB13 and OB15 by
  native runs of the witness and control alone (12 mutant runs, seeds 42-53; 3 original guard runs, seeds 42-44),
  OB03 from 12 mutant runs of T; OB02 from 12 original runs of T (and, for a suite-omission candidate, the
  witness and control guards).

## 3. Action comparison on each pair

| Condition | Procedure | What changes in the observation |
|---|---|---|
| A, existing scoring procedure | T | nothing |
| B, stronger assertions on the same counts | T plus the combined suite (marginals on every qubit, adjacent two-qubit Z products, original-centred); and, where QSurvDiag names a witness, T plus the witness (procedure D) | nothing: the same Z counts, more statistics |
| C, fixed supplementary measurement | a Hadamard on every qubit after the program, then Z measurement, and one assertion | the measurement basis (X on every qubit); computation, input, contract and counterpart unchanged |

Statistic for C, fixed now:
- constructed pair: the X parity of all qubits, `observable "Z0 ... Z(n-1)" ~= ref` after the Hadamards, with
  P's ideal value as reference. Semantic basis, to be verified by the runner: H commutes with the X parity
  X^(n); GHZ+ has parity +1; every Trotter factor (RX rotations, ZZ rotations) commutes with X^(n); a terminal
  Z_j anticommutes with it and leaves every Z probability unchanged. So P has parity +1 and C has parity -1,
  while their Z distributions are equal. The witness is researcher-designed, not derived by QSurvDiag.
- natural pair: the first instance in the study's witness order, computed on the X-basis distributions of P and
  M, whose difference exceeds theta (original-centred reference). This rule was chosen with the exploratory
  X-basis evidence in view. The X parity is not used for the natural pair: P and M both preserve it.
- if no X-basis instance exceeds theta at a width, C is recorded as unavailable at that width.

## 4. Native settings, validation and cost

- QUTest 0.1.0, ideal backend, N = 2,000 shots (the study's certification setting), gate lists in `x`, `h`,
  `cx`, `rx`, `rz`, `z`.
- Certification streams: mutant seeds 42-53, original guard seeds 42-44 (OB02, OB13, OB15, and the C statistic).
- Validation streams, independent of certification: every complete procedure (A; B; D where a witness
  exists; C where a statistic exists) runs 12 times on the counterpart at seeds 7042-7053 and 12 times on the
  original at seeds 8042-8053. A procedure is supported when it kills the counterpart in 12 of 12 runs and fails
  the original in at most 1 of 12 (the MQT Bench validation rule). Other outcomes are reported as observed.
- The QED-C score itself is reported, not thresholded: polarization fidelity from noiseless Aer counts at the
  benchmark default of 100 shots and at 2,000 shots, over the 12 validation seeds, for both programs of each pair,
  through a reimplementation of `qedclib/metrics.py` lines 698-816.
- Cost: semantic analysis time (state simulation, universe enumeration), native executions, shots and run
  time per condition, workers and machine. Shared counts are not re-acquired for extra statistics; the extra cost
  of B and D is zero shots per run, and the extra cost of C is a separate execution per run.
- No retry. A tool error is recorded as unsupported and is neither a kill nor a survival.

## 5. Readings fixed now

- The natural pair receives the outcome `certify()` returns; if it is Unresolved or no outcome, the discrepancy
  and the score are reported without a class. A high QED-C score is not called a survival.
- The constructed pair's observation limitation rests on the semantic argument; native repetitions only check
  implementation behavior.
- The case supports at most: a validated detection improvement (C supported, A and B not); a supported decision
  to stop strengthening within the profile (constructed pair, CL3); an escalation to another observation
  procedure; or only a partial practical case. The study conclusion stays B unless the evidence warrants more.

## 6. Clarifications appended after the freeze (wording only; no change to what the runner executes)

- Program boundary and input. Every executed circuit is the complete circuit: input |0...0>, the kernel's GHZ
  preparation (`h(0)` and a `cx` chain) exactly once, then the TFIM evolution, then (for C only) the terminal Z,
  then (for condition C only) the Hadamards, then measurement. "Executed input GHZ+" in section 2 refers to the
  evolution subcircuit; no state is initialized separately and the preparation is never applied twice
  (`adapter_check_all_widths.out`: preparation once at every width).
- External requirement versus diagnostic relation. Three things are kept apart: (1) the external task, evolution of
  GHZ+ under the documented Hamiltonian with J = h = 1 for t = 0.2 (README); (2) the approximation the benchmark
  selects, K = 5 first-order Trotter steps in the kernel's gate order; (3) the diagnostic relation QSurvDiag uses,
  equality of final states with the researcher-corrected reference implementation P. The README asks for an
  approximate simulation and does not itself require exact equality with P; relation (3) is the study's choice of
  contract for the diagnosis. No upstream approximation threshold is introduced. For the natural pair the
  discrepancy is explained by the coefficient (pi/2 against 1) and by comparing E, P and M. For the constructed
  pair the link to the external task is direct: E and P both have global-X parity +1, C has parity -1, so C is
  orthogonal to E as well as to P (`parity_check.out`: |<E|C>|^2 below 1e-30 at every width).
- Adapter verification for all evaluated widths: `adapter_check_all_widths.out` (n = 2..8): transcribed M equals
  the pinned upstream TFIM method-2 circuit as an operator; the gate order agrees on every qubit wire (Qiskit's
  decomposition interleaves gates on disjoint qubits differently at n >= 6); every qubit i is measured into bit i;
  P differs from M only in the ZZ rotation angles; C equals P plus `z` on qubit 0; effective K = 5, t = 0.2, h = 1.
- Execution provenance. The case is an adapted execution with a reproduced upstream metric: the study's
  transcription runs through QUTest, and the QED-C score is computed by a reimplementation of the pinned metric
  functions; it is not an unmodified end-to-end QED-C run.

## 7. Correction and reanalysis, recorded before it runs

- Reference consistency. The executed method-2 rule T tests Hellinger distance <= 0.05 against the stored
  exact-evolution distribution E (`method2_suite`, `distribution hellinger <= 0.05`; QUTest compares the distance
  directly, so the equivalent fidelity cutoff is (1 - 0.05^2)^2 = 0.99500625, displayed earlier as 0.9950). The
  declared universe U(P) is original-centred: its Hellinger instance is referenced to P's ideal distribution. T is
  therefore not an instance of U(P), and the runner's R_T, computed on T, does not follow the method. T is kept as
  its own analysis (the external metric). The QSurvDiag analysis is reconciled with the admitted baseline T', the
  Hellinger instance of U(P) (reference P's ideal distribution, same comparator and threshold).
- Reanalysis without new samples. `reanalysis.py` evaluates T and T' through QUTest at the
  recorded seeds of the A streams; it requires every re-run T verdict to equal the archived one, which shows that
  the same histograms are being evaluated, and stops otherwise.
- Validity gate in code. `report.py` admits a diagnosis only when the original passes T' (false failures at
  most 1 of 12, the OB02 rule), keeps the runner's raw certify() output, and marks other cells as not evaluable
  while keeping their semantic evidence and the separately evaluated X-basis intervention. The rule is checked on a
  saved invalid cell (constructed pair, n = 6) and a saved valid cell (constructed pair, n = 3).
- Shared path. In the study's shared reporting path (`r2v_arms.diagnose`, `certify`), OB02 is required only for
  suite omissions; for other outcomes the baseline guard is enforced upstream (suite validity before mutant
  outcomes are read). No archived reported outcome in `R2V_FINAL_*.csv` or the MQT Bench `C3_REPORTS.csv` has a
  failed baseline guard (the only failed `final_OB02` values belong to 19 cases already Unresolved), so the gap is
  confined to the case wrapper.
