# X1 extension: the separating setting of the QED-C constructed pair (recorded before its native runs)

Not blind: the QED-C study (RQ5) is complete, and its X-parity measurement, designed by the researchers, detected the
constructed fault P_Z at widths 2-8. The X1 rule (X1_OBSERVATION_CHANGE.md, section 2), applied to the pair (P, P_Z)
from ideal states, names at every width n = 2..8 the setting with the X basis on qubit 0 and the Z basis elsewhere;
its witness is the marginal of qubit 0 (difference 0.177 at n = 2, 0.090 at n = 3, 0.089 for n >= 4).

Native execution follows X1 section 3 unchanged: QUTest 0.1.0 through the pinned CLI, the setting's gate, every
qubit measured, the witness with the original's ideal reference rounded to 4 decimals and tolerance 0.05, N = 8,000;
12 runs on P_Z and 12 on P; control: the same witness without the setting's gate, 12 runs on P_Z. Seeds: P_Z
19042-19053, P 20042-20053 (not used before). Supported: P_Z killed in 12 of 12 runs and P failing in at most 1 of 12.
Reported as exploratory.
