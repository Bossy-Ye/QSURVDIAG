# History

When each rule was fixed, what changed after earlier outcomes were known, and the records that date each step.
Section 7.1 of the article summarizes this record.

## 1. Rules changed after the initial analysis

| Change | Reason | Effect on outcomes |
|---|---|---|
| Distribution distances at Hellinger and Kullback-Leibler as well as total variation | QUTest 0.1.0 implements all three | three below-tolerance outcomes, of two distinct corpus pairs (one also in the width set), become candidates for a suite omission |
| Equality margins between 1e-10 and 1e-8 left undecided | such margins are not decidable in double precision | four outcomes, of three distinct pairs, become Unresolved |
| Assertion types the declared profile leaves out, recorded apart from inadmissible types | separates the evaluated scope from types that cannot support a behavioral claim | none |
| One fixed order for every distinguishing assertion, with a negative control from the same order | the initial rule had no fixed tie-break | none |
| Every requirement evaluated on the case's own record, with native confirmation | the initial evidence model assumed confirmation where an experiment did not run it | 48 candidates for a suite omission withdrawn: 45 corpus, 2 width-set, 1 defect |
| Single-qubit Z products placed last in the witness order, which then lists the whole universe (v3, `data/certification/witness_order/`) | the order left them out, so a candidate whose only instances below theta were single-qubit Z products had no negative control | two of the withdrawn candidates, corpus `qra_cases_v1_1/QRA_360` and defect 26, natively confirmed again; the QED-C X-basis statistic is selected at n = 2 |

The rows overlap and do not add. Two of the three new candidates of the first row are withdrawn by the fifth row, and
the third is natively confirmed; the sixth row restores two candidates that the fifth withdrew. Changes are counted
per experiment, because some pairs occur in both the corpus and the width set. These changes alter 51 outcomes
across the experiments, which involve 48 distinct pairs:
- 50 become Unresolved and one becomes a natively confirmed suite omission;
- no outcome of the 20 circuits or of the Q# and QASMBench programs changes, and no observation limitation changes.

The outcomes changed by the first five rows are listed in `data/certification/outcomes/R2V_RULE_CHANGES.csv`, and
the two that the sixth row returns to their initial outcome in `data/certification/witness_order/IMPACT.csv`.

## 2. When each rule was fixed

Fixing a rule means recording it in a file.

Fixed before the outcomes they concern (initial analysis):
- the profiles, evidence requirements and reporting rules, before any outcome of the five circuits of other
  algorithm families, the width set or the Q# and QASMBench programs;
- the mutant selections for the five circuits of other algorithm families and the Q# and QASMBench programs;
- the generic and output-condition suites, before any outcome;
- the defect eligibility conditions, before any defect ran.

Set or changed after earlier outcomes were known:
- the QuCheck observation on every qubit, declared after the output-register evaluation of transfer was known;
- the ideal references and N = 8,000 of the suite experiment. These followed guard runs in which originals failed
  suites with correlators at sampled references and N = 2,000. A recorded plan switched to ideal references, and
  after further guard runs to N = 8,000, before any mutant ran at that budget;
- the current evidence requirements (section 1);
- the width-set GHZ register, reduced to q0 after a first run at eight to ten qubits (amendment E13c of
  16 August 2026, `data/interventions/width_register/DESIGN_FREEZE.md`);
- the execution adapter of the Q# and QASMBench programs, introduced after the aggregate counts of a voided first
  execution but before any comparison or outcome;
- the corpus eligibility conditions and stratification variable, fixed after semantic comparisons but before the native
  corpus tests;
- the output-condition suites, corrected to express their conditions completely after the first outcomes. The
  correction and its plan were committed before the corrected suites ran (`data/output_condition/`);
- the all-pairs comparator of the repair comparison, chosen after the outcomes of the earlier comparison with the
  combined suite were known, from the composition of its witnesses. Its plan was committed before its runs
  (`data/all_pairs/PLAN.md`);
- the closed witness order (v3), after the v2 outcomes and the QED-C runs were known
  (`data/certification/witness_order/AMENDMENT.md`);
- the development circuits, chosen after a pilot had tested 33 of their 450 mutants; the pilot's runs are not among
  the released records;
- the one-qubit GHZ output register of the 20 circuits, kept after an earlier analysis had shown that the GHZ
  circuits supply most suite omissions (`data/interventions/width_register/DESIGN_FREEZE.md`, E13c, 16 August 2026);
- the designs of the separating-setting, later-position and developer-suite experiments, after all earlier outcomes
  and after pilots on some of their pairs (section 0 of each `PLAN.md`), but before any of their runs;
- in the developer-suite experiment, the comparison of final states on the executed contexts, placed ahead of the
  comparison of observations before any of its outcomes was reported (`data/developer_suites/OPERATIONAL.md`,
  X2_STATE_RELATION);
- the separating setting of the QED-C constructed pair, after the QED-C study was complete
  (`data/observation_change/QEDC_EXTENSION.md`);
- in the developer-suite experiment, the negative control of its one suite omission, run after its outcomes were
  known (`data/developer_suites/OPERATIONAL.md`, X2_NEGATIVE_CONTROL).

Strength of the timing records:
- The rules and predictions of the evaluation on the five circuits of other algorithm families were committed to
  version control.
- The allocation of the Q# programs was recorded with checksums, which fix its content; its date rests on recorded file
  times.
- For the MQT Bench programs, the protocol and the mutant population were committed in two stages before any mutant ran.
  The checksum manifest of each stage was timestamped by an RFC 3161 authority.
- The current rules were recorded with a checksum. Their file modification times precede the outcomes they changed,
  but no commit or independent timestamp made before those outcomes verifies when they were fixed. An identical copy was
  committed and timestamped later, with the MQT Bench protocol.
- The screening protocol of the QED-C case, its design, the output-condition correction and both repair comparisons
  were each committed to version control before the first of their run records (`PLAN.md` and `SCREENING.md` in
  `data/output_condition/`, `data/combined_suite/`, `data/all_pairs/` and `data/qedc/`). The released files differ
  from the committed ones only in file paths and cross-references.
- The designs of the separating-setting, developer-suite and later-position experiments were timestamped together
  by an RFC 3161 authority before any of their runs (Freeze C), and the extension of separating settings to the later
  positions before its settings were computed (Freeze D). Records made after that carry their recorded times
  only.
- No rule was deposited in a public registry.

| Step | Record | Check |
|---|---|---|
| Predictions on the five other circuits committed before their mutants were sampled | commits `e11027e`, `35f0d5c` of `CLAIM_DECISION_BASELINE.md` precede the cohort freeze `a3d926a`, 30 July 2026 | V11 |
| Suite experiment: ideal references, then N = 8,000 after guard-only runs | `PLAN_B5.sha256`; file times `a1b.log` 19:13, `a1b_ext.log` 19:19, `b5_a1c_cl3.py` 19:19, `a1c.log` 19:43, 2 September 2026 | V17 |
| Current rules (v2) fixed before the v2 outcomes | `V2_SPECIFICATION.sha256`; file times: specification 15:12, first `R2V_*` output 15:23, 28 September 2026 | |
| Protocol of the Q# and QASMBench programs, v1 to v4 | each JSON with its `.sha256`; file times 16:08, 16:21, 16:50, 18:04, 6 September 2026 | V18 |
| MQT Bench protocol and mutants fixed before any mutant ran | RFC 3161 receipts of Freeze A (05:33:09 UTC) and Freeze B (05:35:54 UTC), 9 October 2026, before Stage C | `verify_integrity.py --tsr` |
| Designs of the separating-setting, developer-suite and later-position experiments | RFC 3161 receipt of Freeze C, 08:31:41 UTC, 20 October 2026, over `X1_OBSERVATION_CHANGE.md`, `X2_DEVELOPER_SUITES.md` and `X4_POSITION.md`, released as the `PLAN.md` of `data/observation_change/`, `data/developer_suites/` and `data/position/`; first runs after it by the study's file times | `verify_integrity.py --tsr` |
| Separating settings at the later positions | RFC 3161 receipt of Freeze D, 18:42:20 UTC, 22 October 2026, over `X1_POSITION_EXTENSION.md`, released as `data/observation_change/POSITION_EXTENSION.md`; settings computed and runs made after it | `verify_integrity.py --tsr` |
| Later operational records | `data/position/OPERATIONAL.md` 12:37 UTC, 20 October; `data/observation_change/QEDC_EXTENSION.md` 07:25 UTC, 21 October; `data/developer_suites/OPERATIONAL.md`, time per section | |

Times are local (UTC+3) unless marked UTC. The `provenance` column of `provenance/source_manifest.csv` gives, per file:
`git-committed` (the commit that holds this content; every commit of the file in `git_commit_records.csv`),
`timestamp-certified` (listed in an RFC 3161 manifest), `hash-recorded` (hash in the named checksum file, or in a study
checksum file that is not released; no external time) or `file only` (modification time in `original_mtime_utc`).

## 3. Earlier transfer exercise with QuCheck-style tests

An experiment with 2,000 shots on the output register, made before the every-qubit QuCheck profile was declared,
detected 5 of the 21 transfer cases. It used separately constructed contingency tables and Fisher tests in QuCheck's
pinned environment and did not call QuCheck's analysis routine, so these detections are not native QuCheck verdicts.
The article's transfer result is computed from simulated final states under the declared profile. Records:
`data/prospective/cross_tool/s3/S3_QUCHECK_RESULTS.csv`.

## 4. Predictions about the five other circuits

Committed before their mutants were sampled, each with the result that would falsify it. Shares are of the 102
survivors; rates of the 33 contract-equivalent mutants.

| Prediction | Observed | Status |
|---|---|---|
| P1. No unresolved outcome | 0 | confirmed |
| P2. No rule fixed in advance is changed during this evaluation | 0 | confirmed |
| P3. Contract equivalences are 10-30 % | 33 (32.4 %) | contradicted |
| P4. Suite omissions exceed 26.6 % | 21 (20.6 %) | contradicted |
| P5. The gate-set assertion separates more than 80 % | 0 | contradicted |
| P6. Depth separates some, fewer than the gate set | 11 | contradicted |
| P7. The method applies to the QuCheck profile with no shared rule changed | applied | confirmed |
| P8. QuCheck detects every observation limitation with an X or Y difference | no case | not evaluable |
| P9. Below-tolerance differences are under 5 % | 0 | confirmed |
| P10. At least one observation limitation | 0 | contradicted |
| P11. Both profiles express the shared outcomes; only QUTest's, the two equalities | 3 of 6 outcomes occurred | partly exercised |
| P12. The two tools need the admissibility filter for different reasons | as predicted | confirmed |

P5 and P6 were derived from untranspiled gate lists; the audit transpiles both programs to one basis-gate set.
P7 concerns the output-register QuCheck profile, before the every-qubit profile was declared.

## 5. Reference correction in the QED-C case

The QED-C case first ran with the stored-reference acceptance rule as its executed baseline. After those runs, the rule
was found not to be an instance of the original-centered universe, whose Hellinger instance is referenced to P. The
correction and its procedure were recorded before they were evaluated. The diagnostic baseline referenced to P was
evaluated on the histograms of the recorded runs, regenerated by rerunning QUTest at their recorded seeds; the
reproduced verdicts of the stored-reference rule matched all 672 recorded ones. The original-validity rule was then
applied in the reporting code. The raw outputs of the first analysis are kept (`data/qedc/PLAN.md` section 7).

## 6. Earlier repair comparison at N = 2,000

Before the all-pairs comparison, the same 210 candidates were compared with the combined suite (a marginal on every
qubit and the Z products of all neighboring qubits). The repairs reliably killed 174 candidates and the combined suite
133. Among the 173 candidates whose witness the combined suite contained, the 27 that only the repair reliably killed
all failed for the combined suite on the original's guard runs, not on detection; 24 of the 37 witnesses outside the
combined suite were non-adjacent two-qubit Z products. At that budget a union bound over a suite of this size is
vacuous. The all-pairs suite and the 8,000-shot budget were chosen after this comparison and planned before their runs
(`data/combined_suite/`, `data/all_pairs/PLAN.md`).
