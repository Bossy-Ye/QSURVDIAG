# X4: operational settings recorded before any X4 execution

Recorded after the selection (`X4_SELECTION.csv`, sha256 00ae080d...) and before any native run of a selected
mutation.

Selection checks. The Qolumbina archive matches its frozen MD5 and all seven circuit hashes; every external original
reproduces its archived gate-list hash; the 13 archived pools are reproduced exactly; every first-rule mutation is in
its regenerated pool. The rule selects 253 insertions, 107 replacements and no deletion, because deletion sites are
few relative to insertion sites in the later thirds; this follows from the frozen rule and is reported.

Diagnosis implementation. The packaged v2 implementation (`frozen_deps`: `r2v_arms.diagnose`, `r2v_lib.native_check`,
`r2v_finalize.finalize_row`, `qsurvdiag_confirmatory.certify`) is run on a tree assembled from package files by hash
(as `scripts/reproduce_analytic.py` does), with the closed witness order v3 (`witness_order/AMENDMENT.md`) patched into
`ordered_universe` as in `witness_order/native.py`. QUTest 0.1.0, `environment/qiskit_settings.conf`.

Per population, as in its recorded protocol:

| | five other circuits | MQT Bench | Q# and QASMBench |
|---|---|---|---|
| executed input | all-zero | prep of SUBJECTS.json (multipliers) | prep from realized_inputs (v3), qft_n4/deutsch_n2 inside the circuit |
| contract | S1 contract_id | SUBJECTS.json contract | Qolumbina unitary, QASMBench fixed |
| baseline references | exact, rounded to 4 decimals | exact, rounded to 4 decimals | original's counts at reference seed 42 (2,000 shots) |
| original baseline guard | 12 runs, no failure | 12 runs, at most 1 failure | 12 runs, at most 1 failure, every run supported |

Common: S_MIN (one marginal per output-register qubit), tolerance 0.05, N = 2,000, 12 runs. A parse trial (the
mutant test without assertions) precedes execution; a rejected mutation is replaced by the next one in its cell
order. Seeds (X4_POSITION.md): mutant baseline runs 17042-17053, original guard runs 18042-18053; native confirmation
and negative control of a suite-omission candidate run the instance alone on the mutant at 17042-17053 with a guard
of three original runs at 18042-18044 (the v2 native check with these seeds).
