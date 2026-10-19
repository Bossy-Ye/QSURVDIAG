"""FROZEN configuration for the SURVDIAG RQ3 confirmatory feasibility gate.

Preregistered. Everything scientifically material is frozen HERE before any execution.
Do NOT edit after the Stage-0 manifest is committed. All seeds/counts/budgets/thresholds
are outcome-blind (chosen with no reference to survival, equivalence, or pre-cert yield).

Author decisions applied:
  * Grover: DECOMPOSE the real Grover unitary into the fragment (mutations over the decomposed list).
  * Execution: CHECKPOINT AT QUALIFICATION (freeze Stage 0 + run Stage 1; do NOT run the 10,800 primary baseline yet).
"""
import math

FROZEN_TAG = "rq3-feasgate-v1"
PARENT_SPEC_COMMIT = "ebd32c8"           # frozen Method Spec v2 (main)
MASTER_SEED_HEX = "survdiag-rq3-feasibility-gate-v1-master-0000000000000000"

# ------------------------------------------------------------------ fragment
# fragment_v2 = original {h,x,y,z,s,sdg,t,rz,rx,ry,cx,cz,swap} + {p,cp,u,sx,rxx,rzz}.
# Grover is transpiled into GROVER_BASIS (a strict fragment_v2 subset) per the author decision.
FRAG_1Q_0 = {"h", "x", "y", "z", "s", "sdg", "t", "sx", "id"}   # no-angle 1-qubit
FRAG_1Q_1A = {"rz", "rx", "ry", "p"}                             # 1-angle 1-qubit
FRAG_1Q_3A = {"u"}                                               # 3-angle 1-qubit
FRAG_2Q_0 = {"cx", "cz", "swap"}                                 # no-angle 2-qubit
FRAG_2Q_1A = {"cp", "rxx", "rzz"}                                # 1-angle 2-qubit
GROVER_BASIS = ["h", "x", "sx", "rz", "cx"]                      # all in fragment_v2

# ------------------------------------------------------------------ corpus (11 instances)
# Shared QuCheck-QOPS core (9) + QOPS-only QAOA extension (2).
# id = "<family>_<n>"; "methods" = which methods evaluate this instance.
CORPUS = [
    # family,     n,  role,        methods
    ("dj",        3, "shared",   ("qucheck", "qops")),
    ("dj",        5, "shared",   ("qucheck", "qops")),
    ("grover",    3, "shared",   ("qucheck", "qops")),   # decomposed into GROVER_BASIS
    ("grover",    5, "shared",   ("qucheck", "qops")),
    ("qft",       3, "shared",   ("qucheck", "qops")),
    ("qft",       5, "shared",   ("qucheck", "qops")),
    ("qpe",       4, "shared",   ("qucheck", "qops")),
    ("qpe",       6, "shared",   ("qucheck", "qops")),
    ("teleport",  3, "shared",   ("qucheck", "qops")),
    ("qaoa",      4, "qops_only", ("qops",)),
    ("qaoa",      6, "qops_only", ("qops",)),
]
N_INSTANCES = 11
QUBIT_LIMIT = 14                       # cohort-specific (Pass 3B PD-1): historical cap 10 raised to the certified envelope 14

# GHZ / graph-state stay OUT of the primary corpus (prior runs showed low pre-cert eligibility
# for the examined entangler mutations); they remain available only as qualification controls.

# ------------------------------------------------------------------ mutant taxonomy (18 / circuit)
MUTATION_OPERATORS = ("gate_insertion", "gate_deletion", "gate_replacement")
GATE_SEMANTIC_CLASSES = {
    "local_basis_amplitude": ["x", "y", "h", "sx", "rx", "ry"],
    "phase_parameterized":   ["z", "s", "t", "p", "rz"],
    "entangling_controlled": ["cx", "cz", "cp", "rxx", "rzz"],
}
SAMPLES_PER_CELL = 2                    # 3 operators x 3 classes x 2 = 18 mutants / circuit
MUTANTS_PER_CIRCUIT = 18
POSITION_THIRDS = ("first", "middle", "last")   # ~6 mutants per third / circuit
PRIMARY_MUTANT_TOTAL = 198             # 11 x 18

# ------------------------------------------------------------------ frozen QuCheck baseline profile
QUCHECK = {
    "properties_per_program": 2,
    "inputs_per_property": 16,
    "shots_per_basis": 400,
    "measurement_bases": ("x", "y", "z"),      # single-qubit marginals only (contract-fixed)
    "alpha": 0.01,                             # QuCheck default; Holm-Bonferroni multiplicity
    "multiplicity": "holm_bonferroni",
    "statistic": "fisher_exact",
    "repetitions": 30,
    "op_minrep": 20,                           # frozen OP-MINREP (min valid runs)
    "seed_streams": ("input_generator", "property_selection", "simulator", "shot_sampling"),
    "simulator": "AerSimulator (exact/statevector-backed sampling, seeded)",
    "hardware": False,
}

# ------------------------------------------------------------------ frozen QOPS baseline profile
QOPS = {
    "test_cases_per_family": 1000,
    "oracle": "differential_expectation |<H>_orig - <H>_mut| > tol per commuting Pauli family",
    "tolerance": 0.01,
    "repetitions": 30,
    "exact_simulation": True,
    "commit": "psfam 0.0.16 + frozen protocol_freeze/scripts/qops_core.py",
    "hardware": False,
}

# ------------------------------------------------------------------ candidate search / certificate budgets
CANDIDATE = {
    "witness_input_language": "computational-basis inputs 0..2^n-1 (QuCheck) ; commuting Pauli families (QOPS)",
    "bounded_search_cap": 64,                  # max candidate instances enumerated / case
    "enumeration_timeout_s": 60,               # bounded search timeout (Study-B showed enum is the wall)
    "certificate_routes": ("analytic_up_to_global_phase", "sound_marginal_lower_bound", "qops_family_expectation"),
    "failed_search_is_not_certified_negative": True,
}

# ------------------------------------------------------------------ Gamma^pre obligations (frozen, from Method Spec v2)
GAMMA_PRE_OBLIGATIONS = (
    "pair_non_equivalence",
    "native_legality",
    "witness_distinguishability",
    "power_feasibility",
    "resource_feasibility",
    "decision_accessible_omission",
    "provenance_completeness",
)

# ------------------------------------------------------------------ execution size (bookkeeping)
SHARED_INSTANCES = 9
QOPS_ONLY_INSTANCES = 2
PRIMARY_PROFILES = SHARED_INSTANCES * MUTANTS_PER_CIRCUIT * 2 + QOPS_ONLY_INSTANCES * MUTANTS_PER_CIRCUIT   # 324 + 36 = 360
PRIMARY_BASELINE_RUNS = PRIMARY_PROFILES * QUCHECK["repetitions"]                                            # 10,800

# ------------------------------------------------------------------ QAOA freeze (generator determinism)
QAOA_SPEC = {
    "problem": "MaxCut",
    "graphs": {
        4: [(0, 1), (1, 2), (2, 3), (3, 0)],             # 4-cycle C4
        6: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (0, 3)],  # 6-cycle + one chord
    },
    "reps_p": 1,                                          # QAOA depth p=1
    "gamma": round(0.8, 12),                              # frozen cost angle
    "beta": round(0.5, 12),                               # frozen mixer angle
    "note": "graphs/depth/angles frozen before execution; deterministic (no RNG).",
}

PI = math.pi
