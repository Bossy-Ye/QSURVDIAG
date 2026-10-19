"""Frozen dependency manifest for the prospective MQT Bench cohort (Pass 3B).

Every module the experiment reuses from the study is listed with its live path. Freeze A
copies each byte-for-byte into frozen_deps/ and records its SHA-256 in frozen_deps/DEPS.sha256.
Every runner calls verify() first and refuses to run if any live file differs from its frozen copy.
"""
import hashlib, os, json, sys

PILOT = "/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot"
PA = "/Users/mac/Desktop/ZX-STUDY/paper-artifact"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DEPS = {
    # revised analysis (v2): specification and implementation, reused unchanged
    "V2_SPECIFICATION.md": f"{PA}/revision2/V2_SPECIFICATION.md",
    "r2v_lib.py": f"{PA}/revision2/r2v_lib.py",
    "r2v_arms.py": f"{PA}/revision2/r2v_arms.py",
    "r2v_finalize.py": f"{PA}/revision2/r2v_finalize.py",
    "r2_external.py": f"{PA}/revision2/r2_external.py",
    "r2_primary.py": f"{PA}/revision2/r2_primary.py",
    "qsurvdiag_confirmatory.py": f"{PA}/github/code/qsurvdiag/qsurvdiag_confirmatory.py",
    "serialization_adapter.py": f"{PA}/github/code/qsurvdiag/serialization_adapter.py",
    "e1_lib.py": f"{PA}/github/code/qsurvdiag/e1_lib.py",
    "e1_relations.py": f"{PA}/github/code/qsurvdiag/e1_relations.py",
    # data read by e1_lib at import time (not used by this cohort; frozen so imports are reproducible)
    "SSPEC_PROVENANCE.json": f"{PA}/revision2/SSPEC_PROVENANCE.json",
    "PROGRAM_MANIFEST.csv": f"{PILOT}/final_empirical_study/PROGRAM_MANIFEST.csv",
    "S1_SUBJECTS.json": f"{PILOT}/research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json",
    "MUTANT_POPULATION.csv": f"{PILOT}/final_empirical_study/MUTANT_POPULATION.csv",
    "S2_GENERATED_MUTANTS.csv": f"{PILOT}/research_repair/phase5_validation/s2_cohort/S2_GENERATED_MUTANTS.csv",
    # execution adapters
    "qutest_execution_adapter.py": f"{PA}/manuscript/tse/protocol/impl/qutest_execution_adapter.py",
    "qutest_adapter.py": f"{PILOT}/cross_tool_stage/qutest/qutest_adapter.py",
    # mutation enumerator and allocator
    "mutants.py": f"{PILOT}/rq3_feasibility_gate/core/mutants.py",
    "gate_config.py": f"{PILOT}/rq3_feasibility_gate/core/gate_config.py",
    "fragment.py": f"{PILOT}/rq3_feasibility_gate/core/fragment.py",
    "representation.py": f"{PILOT}/rq3_feasibility_gate/core/representation.py",
    "s2_cohort.py": f"{PILOT}/research_repair/phase5_validation/s2_cohort/s2_cohort.py",
    # frozen finite-shot bound (B')
    "decision_bound.py": f"{PILOT}/confirmatory/decision_bound.py",
    # bounded ladder for the observation-limitation validation (E15b rule, as executed in B3)
    "b3_actionability_exec.py": f"{PILOT}/confirmatory/definitive_rerun_b3/b3_actionability_exec.py",
}

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def frozen_table():
    p = os.path.join(ROOT, "frozen_deps", "DEPS.sha256")
    out = {}
    for line in open(p):
        h, name = line.split()
        out[name] = h
    return out

def verify():
    """Abort unless every live dependency equals its frozen copy (Freeze A)."""
    ft = frozen_table(); bad = []
    for name, live in DEPS.items():
        if sha(live) != ft[name] or sha(os.path.join(ROOT, "frozen_deps", name)) != ft[name]:
            bad.append(name)
    if bad:
        raise SystemExit(f"DEPENDENCY DRIFT, refusing to run: {bad}")
    return True

def freeze():
    import shutil
    os.makedirs(os.path.join(ROOT, "frozen_deps"), exist_ok=True)
    with open(os.path.join(ROOT, "frozen_deps", "DEPS.sha256"), "w") as f:
        for name, live in DEPS.items():
            dst = os.path.join(ROOT, "frozen_deps", name)
            if os.path.exists(dst):
                os.chmod(dst, 0o644); os.remove(dst)
            shutil.copy2(live, dst)
            f.write(f"{sha(live)}  {name}\n")
    return verify()

if __name__ == "__main__":
    if sys.argv[1:] == ["freeze"]:
        print("frozen:", freeze())
    else:
        print("verified:", verify())
