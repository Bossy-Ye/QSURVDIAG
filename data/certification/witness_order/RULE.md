# QSurvDiag v3: closed witness order

v3 amends one clause of `V2_SPECIFICATION.md`, the witness order of section 5. Every other clause, setting and
record of v2 is unchanged, and the v2 files are kept as archived.

## Rule

The order of section 5 gains a last item:

9. single-qubit Z products, by qubit index.

The order then lists all 2^(n+1) + n + 3 instances of U(P). A single-qubit Z product restates the marginal of its
qubit on twice its range, <Z_q> = 1 - 2 p_q, so it comes after every other instance. The named witness w* and the
matched-cost control c* are selected from this order as in v2.

## Effect

A v2 selection is the first qualifying instance of the v2 order, and the instances v3 appends follow all of it, so
every v2 selection stays in place. A selection changes only where v2 found none:

| Selection | Where v2 found none | v3 selection |
|---|---|---|
| witness w* | none: every suite-omission candidate has a v2 witness | unchanged |
| control c* | corpus pair `qra_cases_v1_1/QRA_360` and released defect 26, two-qubit pairs with no v2 instance below theta outside the suite | <Z_0>, difference 0 |
| X-basis statistic of the QED-C shipped-coupling pair | n = 2, where the largest difference in the v2 order is 0.047 | <Z_0> on the X-basis counts, the X expectation of qubit 0, difference 0.0945 |

`native.py` ran the new selections natively with the v2 procedures (`CHANGES.csv`, `NATIVE_RUNS.csv`,
`QEDC_X_RUNS.csv`):
- both controls kill their mutants in fewer than 12 of 12 runs with a clean guard (OB15 satisfied), and the
  repeated witness checks reproduce the recorded 12 of 12 kills; both candidates become natively confirmed suite
  omissions (CL4);
- the QED-C statistic kills the counterpart in 12 of 12 certification and 12 of 12 validation runs, and the
  original passes its 3 guard and 12 validation runs.

`audit.py` counts the effect per population (`IMPACT.csv`). The corpus reports 143 suite omissions, and 98
of its 562 survivors stay unresolved; in the repair comparison, `qra_cases_v1_1/QRA_360` moves from the withheld to
the issued candidates. No other outcome of any population changes.
