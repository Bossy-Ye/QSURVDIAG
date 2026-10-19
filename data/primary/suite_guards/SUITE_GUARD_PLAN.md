# B5 — revision batch A, pre-registered before execution

Frozen implementation, frozen populations, frozen
decision configuration except where an arm states otherwise. Nothing in b1..b4 is modified.

## A1 — the reference of Eq. (5), and the CL3 guard attrition

**Hypothesis, stated before measuring.** The systematic suites pin each assertion's reference to a
`_counts(original, INNER_SHOTS=2000, SEED)` estimate, and then test the program at 2000 shots. The
comparison is therefore a difference of two independent means and carries about sqrt(2) the
deviation of the one-sample Hoeffding rows printed in Eq. (5). If that is the mechanism, it
predicts three things:

1. the unmutated original fails its own guard at a rate the one-sample bound does not permit,
   concentrated where the suite is widest and the marginals sit near 0.5 (the QFT subjects);
2. replacing the sampled reference with the exact analytic value clears those guards without any
   other change;
3. after clearing, the 11 QFT CL3 cases become evaluable under S_FAMILY and S_BOTH, and the CL3
   suite result moves from 0 of 14 to 0 of 25.

**A1a, diagnostic, no execution.** For every (subject, suite) cell, compute the exact analytic
value of each assertion, the sampled reference the study used, and their difference. Report the
distribution against ATOL = 0.05, and the predicted one-sample versus two-sample failure
probability. This either supports the mechanism or refutes it.

**A1b, guard re-execution.** Re-run the original-program guard for all 20 subjects under all four
systematic suites with **exact analytic references**, N and R unchanged at 2000 and 12. Report
which cells clear.

**A1c, CL3 recovery.** For every baseline CL3 case that a cleared cell makes evaluable, re-run the
mutant under that suite at exact references, N = 2000, R = 12. Report kills.

**Registered prediction.** Property III.3 says no same-profile suite change can kill a CL3 case.
A1c should return 0 kills over however many cases become evaluable. A single kill refutes the
structural claim and must be reported as such.

## A2 — the single-witness repair under a second interface

The cost-ordered single assertion kills 26 of 26 CL4 cases under the QUTest profile. Fifty of the
63 baseline CL4 cases are observationally identical under QuCheck. This arm asks whether the repair
survives a profile change.

Re-run the b4 witness selection and execution for the 26 CL4 intervention cases under **QuCheck's
recovered observation**, holding the case set, the cost order, the guard convention and R fixed.
Report kills, and report how many cases have no above-threshold witness at all under that
observation.

**No prediction is registered as a success criterion.** A low rate is a finding about interface
dependence, not a failure of the method, and will be reported as such.

## A3 — transpiler-equivalence sweep

The 3.5 % recall reported against transpiler-based equivalence comes from one configuration. Sweep
optimization levels 0-3 across three basis sets and three seeds on the same 85 pairs the declared
contracts hold equivalent, and report the recall range.

## A4 — bias bound on the 53 unrecorded exclusions, analysis only

Characterise the 397 preserved construction cases against the 450 allocated, by subject and by
mutation operator, so the provenance hole carries a bounded statement instead of a disclosure.

## Not in scope

No new subjects, mutants, operators, tools or contracts. No human study. No additional real
defects. The report taxonomy is unchanged.
