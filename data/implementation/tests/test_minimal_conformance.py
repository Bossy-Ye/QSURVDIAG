"""Unit-level conformance tests for QSurvDiag-confirmatory.

These use the minimal two-qubit examples of Section III / Fig. 1 only.  No study
mutant appears here, so the tests cannot be tuned to a study outcome.
"""
import sys
from qsurvdiag_confirmatory import Tri, T, F, U, certify, empirical, requirements

ALL_SAT = {f"OB{i:02d}": "satisfied" for i in range(1, 20)}
CASES, FAILURES = [], []


def check(name, got, want):
    ok = got == want
    CASES.append((name, "PASS" if ok else "FAIL", got, want))
    if not ok:
        FAILURES.append(name)


# ---- CL1: the pair is contract-equivalent -----------------------------------
r = certify({"R_C": T, "R_S": T, "R_O": T, "R_A": F, "R_T": F}, ALL_SAT)
check("CL1 route", r["report"], "CL1")
check("CL1 requires the contract relation be decided", "OB05" in r["required"], True)

# ---- CL2: inequivalent under C, equal endpoint state on the executed input ---
r = certify({"R_C": F, "R_S": T, "R_O": T, "R_A": F, "R_T": F}, ALL_SAT)
check("CL2 route", r["report"], "CL2")
check("CL2 requires the contract relation be decided (defect 1)",
      "OB05" in r["required"], True)

# ---- CL3: states differ, the interface observation does not ------------------
r = certify({"R_C": F, "R_S": F, "R_O": T, "R_A": F, "R_T": F}, ALL_SAT)
check("CL3 route", r["report"], "CL3")
check("CL3 requires profile closure and factorization",
      {"OB08", "OB09"} <= set(r["required"]), True)
check("CL3 is theta-free, so tolerance sensitivity does not gate it (defect 1)",
      "OB16" in r["required"], False)

# ---- CL4: Fig. 1 pair.  <Z0Z1> separates at 1.0 vs 0.0 (d_a = 1.0 > theta),
#           the executed suite holds single-qubit marginals only (0.5 vs 0.5).
r = certify({"R_C": F, "R_S": F, "R_O": F, "R_A": T, "R_T": F}, ALL_SAT,
            empirical_verdict=T)
check("CL4 route", r["report"], "CL4")
check("CL4 requires a witness above tolerance and its native confirmation",
      {"OB11", "OB13"} <= set(r["required"]), True)

# ---- CL5: no admissible assertion exceeds theta ------------------------------
r = certify({"R_C": F, "R_S": F, "R_O": F, "R_A": F, "R_T": F}, ALL_SAT)
check("CL5 route", r["report"], "CL5")
check("CL5 requires a closed and exhaustively enumerated universe (defect 1)",
      {"OB08", "OB10"} <= set(r["required"]), True)

# ---- Unresolved 1: an undecided relation ends the path (defect 2) -----------
r = certify({"R_C": U, "R_S": T, "R_O": T, "R_A": F, "R_T": F}, ALL_SAT)
check("Unresolved on undecided R_C", r["report"], "Unresolved")
check("Unresolved names the undecided relation", r["undecided_relation"], "R_C")
check("Unresolved carries no gating set of its own (defect 3)", r["required"], [])

r = certify({"R_C": F, "R_S": F, "R_O": U, "R_A": F, "R_T": F}, ALL_SAT)
check("Unresolved on undecided R_O", r["undecided_relation"], "R_O")

# ---- Unresolved 2: deliberately incomplete evidence names the missing items --
partial = dict(ALL_SAT)
del partial["OB10"]                      # enumeration completeness not recorded
r = certify({"R_C": F, "R_S": F, "R_O": F, "R_A": F, "R_T": F}, partial)
check("Unresolved on missing CL5 enumeration evidence", r["report"], "Unresolved")
check("Unresolved keeps the candidate it could not support", r["candidate"], "CL5")
check("Unresolved names OB10 as unknown", r["unknown"], ["OB10"])

partial = dict(ALL_SAT)
partial["OB08"] = "unknown"
partial["OB10"] = "unknown"
r = certify({"R_C": F, "R_S": F, "R_O": F, "R_A": F, "R_T": F}, partial)
check("Unresolved names both missing CL5 scope items", r["unknown"], ["OB08", "OB10"])

failed = dict(ALL_SAT)
failed["OB19"] = "failed"                # a frozen rule was amended
r = certify({"R_C": T, "R_S": T, "R_O": T, "R_A": F, "R_T": F}, failed)
check("A failed requirement also yields Unresolved", r["report"], "Unresolved")
check("Unresolved names the failed item", r["failed"], ["OB19"])

# ---- empirical layer: the split verdict is undecided, not false (defect 5) ---
check("unanimous survive is FALSE", empirical(0, 12), F)
check("unanimous kill is TRUE", empirical(12, 12), T)
check("split verdict is UNDECIDED", empirical(8, 12), U)

# ---- A. the Stage-2 / Stage-3 boundary --------------------------------------
# A1. the analytic relations are fixed by d_a and do not move with the sampled
#     verdict.  Same Stage-2 input, three different sampled verdicts.
ANALYTIC = {"R_C": F, "R_S": F, "R_O": F, "R_A": T, "R_T": F}
seen = []
for kills in (0, 8, 12):
    res = certify(ANALYTIC, ALL_SAT, empirical_verdict=empirical(kills, 12))
    seen.append(tuple(res["path"]))
check("A1 analytic Stage-2 path is invariant under the sampled verdict",
      len(set(seen)), 1)
check("A1 analytic R_A stays TRUE under a split verdict",
      dict(certify(ANALYTIC, ALL_SAT, empirical_verdict=empirical(8, 12))["path"])["R_A"],
      "true")
check("A1 the caller's relation dict is not mutated", ANALYTIC["R_A"], T)

# A2. an unstable sampled decision withdraws support without changing Stage 2.
stable = certify(ANALYTIC, ALL_SAT, empirical_verdict=empirical(0, 12))
unstable = certify(ANALYTIC, ALL_SAT, empirical_verdict=empirical(8, 12))
check("A2 stable verdict supports CL4", stable["report"], "CL4")
check("A2 unstable verdict yields Unresolved", unstable["report"], "Unresolved")
check("A2 unstable verdict keeps CL4 as the candidate", unstable["candidate"], "CL4")
check("A2 unstable verdict fails OB03 and nothing else", unstable["failed"], ["OB03"])
check("A2 no Stage-2 relation is undecided", unstable["undecided_relation"], None)
check("A2 Stage-2 path is identical either way", stable["path"], unstable["path"])

# A3. historical missing relation evidence stays missing.  grover_5#e06 never had
#     R_O, R_A or R_T computed, so the path must end at the first of them.
HIST = {"R_C": F, "R_S": F, "R_O": U, "R_A": U, "R_T": U}
r = certify(HIST, ALL_SAT, empirical_verdict=empirical(8, 12))
check("A3 historical gap ends the path at the first missing relation",
      r["undecided_relation"], "R_O")
check("A3 historical gap is not reconstructed into a candidate", r["candidate"], None)
check("A3 historical gap reports no requirement set", r["required"], [])

# ---- the partition rule holds on every supported report ---------------------
for rep, rel in [("CL1", {"R_C": T, "R_S": T, "R_O": T, "R_A": F, "R_T": F}),
                 ("CL2", {"R_C": F, "R_S": T, "R_O": T, "R_A": F, "R_T": F}),
                 ("CL3", {"R_C": F, "R_S": F, "R_O": T, "R_A": F, "R_T": F}),
                 ("CL4", {"R_C": F, "R_S": F, "R_O": F, "R_A": T, "R_T": F}),
                 ("CL5", {"R_C": F, "R_S": F, "R_O": F, "R_A": F, "R_T": F})]:
    res = certify(rel, ALL_SAT)
    part = sorted(res["satisfied"] + res["failed"] + res["unknown"])
    check(f"{rep} partition equals its gating set", part, sorted(res["required"]))

w = max(len(c[0]) for c in CASES)
for name, verdict, got, want in CASES:
    print(f"{verdict}  {name.ljust(w)}   got={got!r}")
print(f"\n{len(CASES) - len(FAILURES)}/{len(CASES)} conformance checks passed")
sys.exit(1 if FAILURES else 0)
