# X1 extension: separating settings of the later-position observation limitations (fixed before their native runs)

Not blind: the X1 result on the 35 observation limitations of the 20 circuits and the 65 later-position observation
limitations (`data/position/X4_FINAL.csv`, report CL3) are known. No separating setting of the 65 has been computed,
and none has run natively.

Population: the 65 pairs with report CL3 in `X4_FINAL.csv`. Final states come from the executed input of each pair as
in the X4 diagnosis (preparation and gate lists written by `x4_select.py`); every qubit is measured.

Setting: the X1 rule (X1_OBSERVATION_CHANGE.md, section 2), unchanged.

Native execution: X1 section 3, unchanged: QUTest 0.1.0 through the pinned CLI, the setting's gates, the witness with
the original's ideal value rounded to 4 decimals as reference and tolerance 0.05, N = 8,000; 12 runs on the mutant at
seeds 21042-21053 and 12 on the original at 22042-22053 (not used before); control: the same witness without the
setting's gates, 12 runs on the mutant at 21042-21053.

Decision: supported when the mutant is killed in 12 of 12 runs and the original fails in at most 1 of 12. A pair for
which no setting has a witness is reported as such.

Reported: pairs supported of 65, by population; settings by number of rotated qubits; settings evaluated by the search
and its time; control kills; original failures. No rerun, reselection of settings or change of budget after the first
run; an execution that fails before any test body runs is rerun once at the same seed and reported.

Prediction: 65 of 65 supported, with no control kill.
