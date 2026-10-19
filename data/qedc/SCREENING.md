# Screening protocol: one externally justified workflow boundary

Status: fixed before any candidate is screened and before any new mutant outcome exists.
Version control records when this file was first committed; that commit is the only evidence of its timing.
It is not a public preregistration.

## Purpose

Find one external testing or validation workflow in which the declared fixed-program count profile is an
independently justified boundary. A qualifying case connects a sourced requirement, a pre-existing observation
boundary, a contract-relevant surviving mutation and a testing action with a consequence. The search targets one
convincing case. It is not a prevalence study, and an empty result is a reportable result.

## Candidate order

Sources already cited by the article or integrated into the study come first. Candidate 8 is an extension that is
screened only for the record and selected only if candidates 1 to 7 all fail.

| Order | Candidate | Why it is on the list |
|---|---|---|
| 1 | Long and Zhao, black-box testing framework for oracle quantum programs (pinned source `MgcosA/Code_of_Testing_Oracle_Quantum_Program_Article` at `2bf129cd…`) | integrated: seven external programs come from it |
| 2 | Muskit 0.0.3 execution workflow with the two oracles of Ali et al. (ICST 2021) | audited tool; documented oracles read the computational-basis distribution only |
| 3 | QUTest 0.1.0 shipped case studies and examples (`case-studies/`, `examples/`) | audited tool; the study's native runner |
| 4 | Qiskit 2.4.1 transpiler defect (issue 16164) and the Qiskit workflow that detects and repairs it | analyzed separately in the article (Section 5.6) |
| 5 | Bugs4Q benchmark test workflow | integrated: 42 defects |
| 6 | QASMBench and MQT Bench published validation conventions | integrated program sources |
| 7 | Baseline workflows described by Oldfield et al. (TOSEM 2025) and QDoctor (ASE 2026) | cited as related test-design work |
| 8 | QED-C application-oriented benchmarks (counts-based fidelity scoring) | extension: an independently adopted validation policy, if no earlier candidate supplies one |

## Eligibility criteria

A candidate qualifies only if every criterion holds, each supported by a primary source (project documentation,
implementation, published workflow description or existing validation policy) or by an executable check.

- EL1. An externally developed program with an independently stated functional requirement.
- EL2. An existing test or validation task, with its intended tester and workflow stage.
- EL3. The observations and transformations available in that task.
- EL4. A pre-existing reason that richer observations are unavailable in the task or require a separate workflow
  step: an interface restriction, an access restriction, an independently adopted workflow policy, or a resource
  condition whose permitted actions and costs exclude the richer measurement. None of the following suffices
  alone: hardware measures in the computational basis; an API returns counts; current tests use Z measurements;
  shots or money are finite; the authors run the program unchanged; the method benefits from a finite universe.
  The complete ordinary caller path is checked, including resubmission of another measurement job and any
  state-dependent verdict channel such as an entanglement witness.
- EL5. The sourced requirement is violated by a difference that the task's observation can hide. A requirement
  that promises only the terminal Z-output distribution makes such a difference contract-equivalent; the
  requirement is not strengthened to manufacture a hidden fault, and a difference confined to an intentionally
  ignored subsystem does not count.
- EL6. The information diagnosis needs (circuit definition, executed input, references, simulator) is available to
  a named analyst under a stated access arrangement.
- EL7. The workflow can be reproduced in this environment (Python, Qiskit, QUTest 0.1.0) within the limit below,
  with any compatibility adapter verified before use.

## Search and integration limit

- Screen the eight candidates above at the level of their primary sources. No other candidate is added unless all
  eight fail EL4, and then at most two further candidates of the missing boundary kind, each named and justified
  here by an amendment committed before it is screened.
- Per candidate: primary documents and source code, plus at most one executable probe of the observation path.
- Screening reads no mutant outcome.

## Selection rule

Select the first candidate in the order above that meets EL1 to EL7. Record every candidate with the criteria it
meets and fails and the source of each judgement. The selected context is not replaced because its diagnosis or
action turns out unfavorable.

## Fixed after selection, before any validating run

The mutation design of the case (mechanism-directed demonstration or systematic sample, with its sampling rule),
the contract, executed input, baseline suite and output register, the existing profile Pi0, the diagnostic access
arrangement, the menu of richer observations with its deterministic selection rule, the intervention protocol,
the validation plan and the cost instrumentation are recorded in `PLAN.md` and committed before
the runs they govern.

## Conclusions the investigation can reach

A. External relevance and action consequence established for this workflow. B. External restriction established;
practical consequence partial, with the missing element named. C. No qualifying external case established. These
are study conclusions, not diagnostic outcomes.

## Outcome

M met, N not met, P partly, U unverified. Sources are pinned; line numbers refer to the pinned revision.

| # | Candidate (pinned source) | EL1 | EL2 | EL3 | EL4 | EL5 | EL6 | EL7 | Decisive reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Long and Zhao black-box oracle testing framework (`MgcosA/Code_of_Testing_Oracle_Quantum_Program_Article` `2bf129cd`) | M | M | M | **N** | M | M | P | "Black-box" hides only the program's internals. The tester prepares two-value superpositions and applies the adjoint of the expected output state, relative phase included, before a Z check (`internal.qs` 56-79, 218-220): the upstream test is already basis-changed and phase-sensitive |
| 2 | Muskit 0.0.3 executor with the Ali et al. oracles (PyPI sdist, hash as in `data/profiles/MUSKIT_DOWNLOAD.json`; oracles in `Simula-COMPLEX/quito` `05ab7bfd`) | M | P | M | P | **N** | M | M | Executor appends Z measurement of every qubit with no hook (`functionalities.py` 127-145), but the specification is a distribution per basis input, so a phase-only change is contract-equivalent |
| 3 | QUTest 0.1.0 case studies and examples (`c56e5a83`) | M | M | M | **N** | **N** | M | M | the test author writes the circuit and may place gates; entanglement witness reads the state vector; every stated requirement is Z-level |
| 4 | Qiskit 2.4.1 commutation-checker defect, fixed in 2.4.2 (fix `1da93bbd`) | M | M | M | **N** | M | M | M | Qiskit's own regression tests compare `Operator` objects (`test_commutation_checker.py` 665-711); no documented Qiskit workflow restricts validation of transpiled circuits to counts |
| 5 | Bugs4Q (`Z-928/Bugs4Q` `7a719839`, `Bugs4Q-Framework` `e596a251`) | P | M | M | **N** | N/U | M | P | `unittest` tests read state vectors, unitaries and counts; no policy restricts them |
| 6 | QASMBench (`357b9423`), MQT Bench (`v2.3.0`) | P | P | M | **N** | N | M | M | QASMBench's published evaluation uses state tomography; MQT Bench has no output-validation policy; no per-circuit requirement |
| 7 | Baselines of Oldfield et al. (TOSEM 2025) and QDoctor (ASE 2026) | U | P | P | **N** | U | U | U | from abstracts only: both present computational-basis-only testing as a limitation their technique removes, not as an external constraint |
| 8 | QED-C application-oriented benchmarks (`SRI-International/QC-App-Oriented-Benchmarks` `v2.0.8` = `efad5275`), Hamiltonian Simulation, method 2 | M | M | M | **M** | M (see 2.3) | M | P | independently adopted counts-only fidelity policy with a documented rationale; requirement stated at state level |

Candidates 1 and 3 to 7 fail EL4; candidate 2 meets EL4 only in part and fails EL5. Candidate 8 met EL1 to EL6 and
EL7 in part; EL7 was closed by `kernel_equivalence_check.out` (the transcription equals the upstream kernel's final
states to 1e-12) and by the native runs of `case_run.py`, which execute that transcription through QUTest 0.1.0
(a driver adaptation: neither the QED-C driver nor its analyzer runs).

Program inside candidate 8, chosen after exploratory probes and before any mutant run: of the Hamiltonian
Simulation programs, the Heisenberg kernel does not pass its own method-2 validation on an ideal simulator
(Hellinger fidelity 0.03 to 0.94, `convention_scan.out`), whereas the TFIM references equal exact evolution of the
stated Hamiltonian (fidelity 1.000000 at n = 2..8, `convention_scan_tfim.out`). The case uses TFIM.
