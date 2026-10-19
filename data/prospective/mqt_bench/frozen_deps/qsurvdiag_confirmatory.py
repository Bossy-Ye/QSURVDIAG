"""QSurvDiag-confirmatory: the decision procedure that conforms to the normative
method of Section III of the manuscript.

This module is NOT a repair made after seeing outcomes.  Every rule below is
derived from a statement already published in Section III; the frozen Phase-5
implementation implements a proper subset of it, and the five deviations are
recorded in CONFORMANCE_TABLE.md.

Normative sources (manuscript Section III):
  S3.C  "Each comparison returns true, false or undecided, and a comparison that
         returns undecided ends the path with no candidate."          -> Tri
  S3.C  Eq. (3) eq:substrate, the exact partition of complete paths.   -> candidate()
  S3.D  "For a candidate report q, a prospectively fixed set Req(q) specifies
         what that report needs ... Relation evidence establishes the values of
         R_C, R_S, R_O, R_A^t and R_T^t that the selected path reads."-> requirements()
  S3.D  "CL3 requires a complete profile and factorization through alpha.
         CL5 requires complete coverage of a closed U(P)."             -> SCOPE
  S3.D  Eq. (4) eq:conc, the finite-shot decision bound.               -> empirical()
"""

from enum import Enum


class Tri(Enum):
    """Three-valued relation outcome.  DEFECT 2: the frozen layer was boolean."""
    TRUE = "true"
    FALSE = "false"
    UNDECIDED = "undecided"

    def __bool__(self):                      # refuse silent collapse to bool
        raise TypeError("Tri is three-valued; compare explicitly")


T, F, U = Tri.TRUE, Tri.FALSE, Tri.UNDECIDED

RELATIONS = ("R_C", "R_S", "R_O", "R_A", "R_T")

# ------------------------------------------------- Stage 2 threshold comparison
# CORRECTION 9 (conformance category 9).  Section III: every comparison returns
# "true, false or undecided, and an undecided comparison ends the path with no
# candidate".  A theta comparison whose margin lies at or below the resolution at
# which the difference is recorded is decided by the simulator, not by the
# mathematics, so it returns UNDECIDED rather than a boolean.
#
# THRESHOLD_RESOLUTION is the recorded resolution of the analytic margins, not a
# tuned tolerance: it is the resolution at which d_a is committed to the record.
THRESHOLD_RESOLUTION = 5e-9


def compare_threshold(d_a, theta, resolution=THRESHOLD_RESOLUTION):
    """Three-valued `d_a > theta`.

    TRUE  when d_a exceeds theta by more than the recording resolution;
    FALSE when it falls short by more than that;
    UNDECIDED when |d_a - theta| <= resolution -- resolution-limited.

    d_a must be the unrounded stored value.  Passing a display-rounded margin
    defeats the comparison, which is the defect this replaces.
    """
    if abs(d_a - theta) <= resolution:
        return U
    return T if d_a > theta else F


def exists_above(diffs, theta, resolution=THRESHOLD_RESOLUTION):
    """Kleene existential over an assertion universe: does any member separate?

    `diffs` is every admissible instance's difference functional value.  The
    quantification is over the universe entire; CORRECTION 8 forbids filtering it
    by whether a family carries a finite-shot row, because that is Stage-3
    information and Section III states the bound "does not define R_A or R_T".

    TRUE  if some member is decisively above theta;
    FALSE if every member is decisively below;
    UNDECIDED otherwise -- no member decides it and at least one is
    resolution-limited.
    """
    verdicts = [compare_threshold(d, theta, resolution) for d in diffs]
    if any(v is T for v in verdicts):
        return T
    if any(v is U for v in verdicts):
        return U
    return F

# ---------------------------------------------------------------- Stage 2 ----
# Eq. (3): CL1 <=> R_C
#          CL2 <=> ~R_C & R_S
#          CL3 <=> ~R_C & ~R_S & R_O
#          CL4 <=> ~R_C & ~R_S & ~R_O & R_A & ~R_T
#          CL5 <=> ~R_C & ~R_S & ~R_O & ~R_A
# The path is read in order; the first UNDECIDED ends it with no candidate.
PATH = (
    ("R_C", T, "CL1"),
    ("R_S", T, "CL2"),
    ("R_O", T, "CL3"),
    ("R_A", F, "CL5"),
    ("R_T", F, "CL4"),
)


def candidate(rel):
    """Return (report, path, undecided_relation).

    report is one of CL1..CL5, or None when the path ends with no candidate.
    DEFECT 2 fix: an UNDECIDED relation ends the path instead of collapsing to
    false.  DEFECT 5 fix: the empirical layer feeds R_A/R_T as Tri, so a split
    native verdict reaches this function as UNDECIDED rather than as an
    imperative the scan cannot execute.
    """
    path = []
    for name, hit, report in PATH:
        v = rel[name]
        if v is U:
            return None, path, name
        path.append((name, v.value))
        if v is hit:
            return report, path, None
    # every relation decided and R_T is TRUE: an executed assertion separates
    # the pair, so it is not a survivor.  Section III makes this path empty.
    return None, path, "R_T_inconsistent"


# ---------------------------------------------------------------- Stage 3 ----
# Requirement evidence, grouped exactly as Section III-D groups it.
#
# 1) RELATION evidence, per relation AND per polarity.  DEFECT 1 fix: the frozen
#    registry attached evidence only to the relations a report asserts
#    positively, so a report resting on ~R_A carried no obligation to have
#    searched a closed, exhaustively enumerated universe.
REL_EVIDENCE = {
    ("R_C", T): ("OB04", "OB05"),
    ("R_C", F): ("OB04", "OB05"),
    ("R_S", T): ("OB06", "OB07"),
    ("R_S", F): ("OB06", "OB07"),
    ("R_O", T): ("OB06", "OB07"),
    ("R_O", F): ("OB06", "OB07"),
    ("R_A", T): ("OB11", "OB12", "OB13"),
    ("R_A", F): ("OB08", "OB10"),          # exhaustion over a CLOSED universe
    ("R_T", T): ("OB14",),
    ("R_T", F): ("OB14",),
}

# 2) SCOPE evidence, stated verbatim in Section III-D for CL3 and CL5.
SCOPE_EVIDENCE = {
    "CL3": ("OB08", "OB09"),
    "CL5": ("OB08", "OB10"),
}

# 3) DECISION evidence: it "relates the ideal assertion difference to the
#    shot-based verdict".  It therefore attaches to reports whose condition
#    reads a theta-comparison, and to the native verdict every survivor rests on.
DECISION_EVIDENCE = {
    "CL1": ("OB03",),
    "CL2": ("OB03",),
    "CL3": ("OB03",),                      # theta-free condition: no OB16
    "CL4": ("OB02", "OB03", "OB15", "OB16", "OB17"),
    "CL5": ("OB03", "OB16"),
}

GLOBAL_EVIDENCE = ("OB01", "OB18", "OB19")


def requirements(report, rel):
    """Req(q), derived from the report's own condition in Eq. (3)."""
    req = set(GLOBAL_EVIDENCE)
    req |= set(DECISION_EVIDENCE[report])
    req |= set(SCOPE_EVIDENCE.get(report, ()))
    for name, value in condition_of(report):
        req |= set(REL_EVIDENCE[(name, value)])
    return req


def condition_of(report):
    """The conjuncts of Eq. (3) for one report, as (relation, polarity)."""
    conds = {
        "CL1": [("R_C", T)],
        "CL2": [("R_C", F), ("R_S", T)],
        "CL3": [("R_C", F), ("R_S", F), ("R_O", T)],
        "CL4": [("R_C", F), ("R_S", F), ("R_O", F), ("R_A", T), ("R_T", F)],
        "CL5": [("R_C", F), ("R_S", F), ("R_O", F), ("R_A", F)],
    }
    return conds[report]


# ------------------------------------------------------- empirical layer -----
def empirical(kills, reps):
    """The finite-shot verdict, evaluated in STAGE 3 only.

    DEFECT 5 fix, corrected at Round 0.5.  Section III defines R_A^theta and
    R_T^theta from the analytic assertion differences d_a; the finite-shot
    verdict is decision evidence, which Section III-D places in Stage 3.  This
    function therefore reports the STABILITY of the sampled decision and never
    edits a Stage-2 relation.  A unanimous verdict over R repetitions is
    reliable at margin delta with probability at least 1 - R*B(N,delta)
    (Eq. 4); a split verdict is reachable only when the analytic margin lies
    inside the concentration band, so it is recorded as UNDECIDED support and
    routes the candidate to Unresolved through OB03.
    """
    if reps is None or kills is None:
        return U
    if kills == 0:
        return F
    if kills == reps:
        return T
    return U                                # 0 < kills < R: inside the band


# ------------------------------------------------------------- procedure -----
def certify(rel, evidence, empirical_verdict=None):
    """Run the full corrected procedure over one recorded evidence record.

    rel               : dict of the five relations as Tri
    evidence          : dict OBxx -> "satisfied" | "failed" | "unknown"
                        (an obligation absent from the dict is UNKNOWN)
    empirical_verdict : Tri from empirical(), or None when not applicable

    Returns a dict with the candidate, the supported report, the requirement
    partition and, for Unresolved, the named missing items.
    """
    rel = dict(rel)

    # STAGE 2 reads the analytic relations exactly as computed from d_a.  The
    # sampled verdict does NOT enter here: Section III-C defines R_A^theta and
    # R_T^theta analytically, and Section III-D evaluates finite-shot support
    # in Stage 3.  A split or unstable sampled decision therefore cannot
    # redefine assertion existence; it can only withdraw support for the
    # candidate, which it does below through OB03.
    report, path, undecided = candidate(rel)

    if report is None:
        # DEFECT 3 fix: Unresolved is not gated by an obligation set of its own.
        # Its record names the relation that ended the path; the partition rule
        # is satisfied because Req(Unresolved) is empty by construction and the
        # unmet items are reported against the path, not against a gating set.
        return {
            "candidate": None,
            "report": "Unresolved",
            "path": path,
            "undecided_relation": undecided,
            "required": [],
            "satisfied": [],
            "failed": [],
            "unknown": [],
            "unresolved_reason": f"relation {undecided} is undecided",
        }

    req = sorted(requirements(report, rel))

    # STAGE 3.  Finite-shot stability is decision evidence carried by OB03, which
    # gates every report.  An UNDECIDED sampled verdict fails it.
    evidence = dict(evidence)
    if empirical_verdict is U:
        evidence["OB03"] = "failed"
    elif empirical_verdict is not None and "OB03" not in evidence:
        evidence["OB03"] = "satisfied"

    sat = [o for o in req if evidence.get(o) == "satisfied"]
    fail = [o for o in req if evidence.get(o) == "failed"]
    unk = [o for o in req if evidence.get(o) not in ("satisfied", "failed")]

    if fail or unk:
        return {
            "candidate": report,
            "report": "Unresolved",
            "path": path,
            "undecided_relation": None,
            "required": req,
            "satisfied": sat,
            "failed": fail,
            "unknown": unk,
            "unresolved_reason": "requirement evidence incomplete: "
                                 + ",".join(fail + unk),
        }

    return {
        "candidate": report,
        "report": report,
        "path": path,
        "undecided_relation": None,
        "required": req,
        "satisfied": sat,
        "failed": [],
        "unknown": [],
        "unresolved_reason": None,
    }
