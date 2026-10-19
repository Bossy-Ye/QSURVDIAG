# E1 repository discovery log

All searching done 2026-09-22, after `protocol.md` was frozen and committed (`7dcbd61`).

## Where I searched

**GitHub, via the authenticated `gh` CLI**, in two modes.

*Code search* (`gh search code`), for the priority-1 and priority-2 frameworks of the protocol:

| query | distinct repositories returned |
|---|---|
| `qucheck quantum property` | 0 |
| `from qucheck` | 1 — `GabrielPontolillo/qucheck` |
| `import qucheck` | 1 — `qafny/quantumTesting` |
| `qutest quantum pragma` | 0 |
| `assertEqual statevector qiskit` | 0 |
| `muskit mutation quantum` | 0 |

GitHub's code-search API is heavily restricted for unindexed terms, and returned almost nothing.
**No repository outside the tool's own was found using QUTEST**, and only one third-party repository
was found using QuCheck. This is a finding about availability, not about the frameworks.

*Topic search* (`gh search repos --topic`), sorted by stars, filtered to >= 40 stars and pushed since
2025-01:

`qiskit`, `cirq`, `pennylane`, `quantum-algorithms`, `quantum-computing`, `quantum-programming` —
72 result rows, 46 distinct repositories after de-duplication.

## Filtering

1. **Listing-level screen** (title, description, topic): dropped awesome-lists, resource
   collections, course material and tutorial repositories on X2/X5, and single-author toy
   repositories named "qiskit-test" and similar. 46 → 25 carried forward.
2. **API verification** of all 25: commit SHA on the default branch, SPDX license, archived flag,
   last push, full recursive tree, test-file inventory. Recorded in `repository_candidates.csv`.
   Nothing in that file is asserted without an API response behind it.
3. **Source-level screen** of 8 shortlisted repositories: developer test files fetched and read to
   check E4 (does a test assert on quantum behavior), and candidate unit sources fetched and read to
   check E9 (does the unit construct gates in-repository).

## Two measurement defects found and corrected during discovery

- The first test-file detector required a `tests/` path component, so repositories using the
  `*_test.py`-beside-source convention reported **0 test files**. Cirq showed 0, then 492 once
  corrected; Qualtran 0 → 326; ReCirq 0 → 101; TensorFlow Quantum 0 → 48. Every count in the census
  comes from the corrected detector.
- The behavioural-test classifier in `select_units.py` used a narrower signal list than the one I had
  verified by reading files, and silently skipped any file the API failed to return. Both were fixed:
  unreadable files are now reported, and the signal list matches what reading confirmed. The unit
  selection changed under the fix, which is why the selection in
  `PILOT_CANDIDATE_REPORT.md` is marked provisional.

## Counts

| | |
|---|---|
| result rows seen across all searches | 72 + 2 |
| distinct repositories after de-duplication | 46 |
| screened out at listing level (X2/X5, toy repositories) | 21 |
| **inspected against the API** (commit, license, tree, tests) | **25** |
| of those, read at source level (tests and unit sources) | 8 |
| pilot candidates (E1–E4, E6, E8, E9 verified; E5/E7 pending execution) | 3 |
| eligible with a flagged concern | 3 |
| excluded with a recorded reason | 2 |
| reserve, metadata verified, E4/E9 not yet read | 17 |

No repository was inspected, kept or dropped on the basis of any QSurvDiag outcome. No mutant exists
and no diagnosis has been computed.

## Tooling corrections, 2026-09-22

**Contamination detector.** The first detector matched the substring `mutation`, which also matches
**`permutation`**. It reported 5 mutation-testing artifacts in `quantumlib/Qualtran`; all five were
`permutation.py`, `permutation.ipynb` and `permutation_test.py`, mathematical permutation files.
Replaced with a token-aware rule in `detect_mutation_artifacts.py`, which requires that
`mutant`/`mutation` not be preceded by a letter, and also matches `mutmut`, `mutpy`, `qmutpy`,
`muskit`. Self-tested on 9 constructed cases, 9/9, including `permutation.py`, `commutation.py` and
`transmutation.py` as negatives. Re-run across all candidates:

| repository | token-aware | old substring |
|---|---|---|
| `quantumlib/Qualtran` | **0** | 5 (all `permutation`) |
| `qiboteam/qibo` | 0 | 0 |
| `unitaryfoundation/mitiq` | 0 | 0 |
| `GabrielPontolillo/qucheck` | **255** | 255 |

This is a tooling correction. It changes no protocol outcome and no recorded decision: qucheck's
exclusion stands on its 255 genuine artifacts and its test-file provenance, and Qualtran was never
excluded on the false signal.

**Output-path collision.** `work/select_replacements.py`, cloned from `select_units_v11.py` to
screen reserve repositories, inherited its hard-coded output path and **overwrote the committed
`selected_units_v11.json`** holding the qucheck/qibo/mitiq selection. Detected while building the
Qualtran packet. The original was recovered from commit `7f1c510` and verified to match the
published selection exactly; the screener now writes `selected_units_replacements.json`. No
downstream artifact was built from the clobbered file: `pilot_manifest_v1.1.csv` and the 24-unit
packet both predate it, and the packet hash is unchanged.
