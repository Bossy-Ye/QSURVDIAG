# Protocol deviations

| ID | Declared | Stage | Change | Reason | Expected effect |
|---|---|---|---|---|---|
| PD-1 | 2026-10-09, before Freeze A | population tooling | cohort-only enumerator copy with `QUBIT_LIMIT` 10 -> 14 (`cohort_enumerator/PD1_QUBIT_LIMIT.diff`); historical enumerator unchanged | the historical eligibility cap leaves `rg_mult_12` (n = 12) without eligible mutants; the cap is an eligibility parameter, not an algorithmic assumption (PROTOCOL.md 5.3) | none on `qwalk_4`, `qwalk_5`, `rg_mult_8` (identical ordered pools, verified); enables `rg_mult_12` (7,872 distinct candidates) |

No deviation after Freeze A as of its commit.
