"""S3: native execution, frozen profile application, certificate generation.
Imports the FROZEN decision function and validator; never reimplements them.
RUN: .venv-qutest-audit/bin/python research_repair/phase5_validation/s3_certification/s3_engine.py
"""
import csv, hashlib, importlib.util, io, json, os, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "cross_tool_stage", "qutest"))
import qutest_adapter as QA
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Operator

PRE = os.path.join(ROOT, "research_repair", "phase5a_prefreeze")
S1D = os.path.join(ROOT, "research_repair", "phase5_validation", "s1_materialization")
S2D = os.path.join(ROOT, "research_repair", "phase5_validation", "s2_cohort")

def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s)
    b = io.StringIO(); o = sys.stdout; sys.stdout = b
    try: s.loader.exec_module(m)
    finally: sys.stdout = o
    return m
CD = _load("cd", os.path.join(PRE, "scripts", "claim_decision.py"))      # FROZEN decision function
VC = _load("vc", os.path.join(PRE, "scripts", "validate_certificates.py"))  # FROZEN validator

SUBJ = {s["subject"]: s for s in json.load(open(os.path.join(S1D, "S1_SUBJECTS.json")))}
MUT = list(csv.DictReader(open(os.path.join(S2D, "S2_SAMPLED_MUTANTS.csv"))))
PRF = {r["mutant_id"]: r for r in csv.DictReader(open(os.path.join(S2D, "S2_NATIVE_PREFLIGHT.csv")))}
R, ATOL, TOL = 12, QA.ATOL, 1e-9
TOL_GRID = [0.01, 0.02, 0.05, 0.10]

# ---------------------------------------------------------------- exact semantics
def sv(gates, n, bits=0):
    qc = QuantumCircuit(n)
    for i in range(n):
        if (bits >> i) & 1: qc.x(i)
    for g in gates: getattr(qc, g["gate"])(*g.get("angles", []), *g["q"])
    return Statevector.from_instruction(qc).data

def uni(gates, n):
    qc = QuantumCircuit(n)
    for g in gates: getattr(qc, g["gate"])(*g.get("angles", []), *g["q"])
    return Operator(qc).data

def zdist(state):           # exact joint Z distribution, index = little-endian bitstring
    return np.abs(state) ** 2

def marg(p, n, q):          # exact p1 of qubit q
    return float(sum(p[i] for i in range(len(p)) if (i >> q) & 1))

def obs_z(p, n, mask):      # exact <Z_S>
    return float(sum(p[i] * (-1) ** bin(i & mask).count("1") for i in range(len(p))))

def shannon(p):
    q = p[p > 1e-15]; return float(-np.sum(q * np.log2(q)))

def rot_marg(state, n, q, basis):
    """exact single-qubit marginal p1 of qubit q measured in basis x/y/z (QuCheck's substrate)."""
    qc = QuantumCircuit(n)
    if basis == "x": qc.h(q)
    elif basis == "y": qc.sdg(q); qc.h(q)
    st = Statevector(state).evolve(qc).data
    return marg(np.abs(st) ** 2, n, q)

def uniform_joint(state, n, qubits, basis):
    """exact joint distribution over `qubits` with ALL of them measured in the same basis (QuCheck substrate)."""
    qc = QuantumCircuit(n)
    for q in qubits:
        if basis == "x": qc.h(q)
        elif basis == "y": qc.sdg(q); qc.h(q)
    p = np.abs(Statevector(state).evolve(qc).data) ** 2
    out = defaultdict(float)
    for i, a in enumerate(p):
        if a > 1e-15:
            out["".join(str((i >> q) & 1) for q in qubits)] += float(a)
    return dict(out)

# ---------------------------------------------------------------- native execution
def suite(sid):
    s = SUBJ[sid]; gates, n, outq = s["base_gates"], s["n"], s["output_register_qubits"]
    refs = {q: QA.reference_marginal(gates, n, q) for q in outq}
    return [QA.marginal_assertion(q, refs[q]) for q in outq], refs

def native(gates, n, asserts, reps=R):
    v = []
    for rep in range(reps):
        vd, summ = QA.run_qutest(QA.make_test(gates, n, asserts, seed=QA.SEED + rep))
        v.append((rep, vd, summ))
    return v

# ---------------------------------------------------------------- main
def main():
    runs, verds, contract_ev, state_rel, obs_rel, rau, wits, cfg = [], [], [], [], [], [], [], []
    certs, cert_idx, absten, vovp, xt, ent, effcls = [], [], [], [], [], [], []
    qt_adm, qc_adm = [], []
    SUITE = {sid: suite(sid) for sid in SUBJ}

    # original-program native baseline per subject (OB02)
    orig_ff = {}
    for sid, s in SUBJ.items():
        a, refs = SUITE[sid]
        vv = native(s["base_gates"], s["n"], a)
        ff = sum(1 for _, vd, _ in vv if vd != "SURVIVED") / R
        orig_ff[sid] = ff
        for rep, vd, summ in vv:
            runs.append({"case": f"ORIGINAL::{sid}", "subject": sid, "role": "original", "repetition": rep,
                         "seed": QA.SEED + rep, "shots": QA.INNER_SHOTS, "atol": ATOL, "backend": "ideal",
                         "verdict": vd, "summary": summ})
        print(f"original {sid:20s} false_fail={ff:.4f}")

    elig = [m for m in MUT if PRF[m["mutant_id"]]["eligibility"] == "ELIGIBLE_NATIVE"]
    print(f"eligible cases: {len(elig)}")

    for ci, m in enumerate(elig):
        mid, sid, n = m["mutant_id"], m["subject"], int(m["n"])
        if ci % 10 == 0:
            print(f"  [{ci}/{len(elig)}] {mid}", flush=True)
        s = SUBJ[sid]; base, mg = s["base_gates"], json.loads(m["mutated_gates"])
        outq = s["output_register_qubits"]; asserts, refs = SUITE[sid]
        arb = m["contract_id"] == "C_ARBITRARY_INPUT_UNITARY"

        # ---- A. native verdict
        vv = native(mg, n, asserts)
        kills = sum(1 for _, vd, _ in vv if vd == "KILLED")
        inval = sum(1 for _, vd, _ in vv if vd == "UNSUPPORTED")
        for rep, vd, summ in vv:
            runs.append({"case": mid, "subject": sid, "role": "mutant", "repetition": rep,
                         "seed": QA.SEED + rep, "shots": QA.INNER_SHOTS, "atol": ATOL, "backend": "ideal",
                         "verdict": vd, "summary": summ})
        verdict = "KILLED" if kills == R else ("SURVIVED" if kills == 0 else "UNSTABLE")
        verds.append({"mutant_id": mid, "subject": sid, "kills": kills, "repetitions": R,
                      "p_kill": round(kills / R, 4), "invalid_runs": inval, "verdict": verdict,
                      "stable": kills in (0, R), "original_false_fail": round(orig_ff[sid], 4),
                      "aggregation_rule": "0/12 survivor, 12/12 killed, otherwise UNSTABLE",
                      "significance": 0.05, "multiplicity": "n/a (QUTest applies none)"})

        # ---- B. exact contract + state + observation
        sb, sm = sv(base, n, 0), sv(mg, n, 0)
        st_eq = abs(abs(np.vdot(sb, sm)) - 1.0) < TOL
        fu = None
        if 2 ** n <= 4096:
            ub, um = uni(base, n), uni(mg, n)
            fu = abs(abs(np.trace(ub.conj().T @ um)) / (2 ** n) - 1.0) < TOL
        ce = fu if arb else st_eq
        pb, pm = zdist(sb), zdist(sm)
        tvd = float(0.5 * np.sum(np.abs(pb - pm)))
        zd_eq = tvd <= TOL
        contract_ev.append({"mutant_id": mid, "subject": sid, "contract_id": m["contract_id"],
            "relation_evaluated": "|Tr(Ub^H Um)|/2^n" if arb else "|<psi_b(0)|psi_m(0)>|",
            "contract_equivalent": ce, "full_unitary_equivalent": fu,
            "declared_input_state_equivalent": st_eq, "grounding": "EXTERNAL",
            "alt_scope_sensitivity": ("also declared-input-state equivalent" if arb and st_eq else
                                       ("also full-unitary equivalent" if (not arb) and fu else ""))})
        state_rel.append({"mutant_id": mid, "subject": sid, "endpoint_state_equal_up_to_phase": st_eq,
            "state_overlap": round(float(abs(np.vdot(sb, sm))), 12), "precision": "1e-9",
            "licenses_trajectory_claim": False})
        xy = max(abs(rot_marg(sb, n, q, b) - rot_marg(sm, n, q, b)) for q in range(n) for b in ("x", "y"))
        obs_rel.append({"mutant_id": mid, "subject": sid, "joint_Z_tvd": round(tvd, 12),
            "z_distribution_identical": zd_eq, "max_xy_marginal_diff": round(float(xy), 12),
            "witness_class": ("STATE_IDENTICAL_ON_CONTRACT_INPUT" if st_eq else
                              ("XY_MARGINAL_VISIBLE_ONLY" if zd_eq and xy > ATOL else
                               ("JOINT_ONLY_INVISIBLE_TO_UNIFORM_MARGINALS" if zd_eq else "Z_VISIBLE")))})

        # ---- count-substrate exhaustive enumeration (QT_0_1_0__COUNT_SUBSTRATE)
        cands, cnt = [], 0
        for q in range(n):
            cnt += 1; cands.append(("marginal", f"m[{q}]", abs(marg(pm, n, q) - marg(pb, n, q)), marg(pb, n, q), "RELIABLE"))
        for mask in range(1, 2 ** n):
            cnt += 1; cands.append(("observable_Z", f'"{mask}"', abs(obs_z(pm, n, mask) - obs_z(pb, n, mask)), obs_z(pb, n, mask), "RELIABLE"))
        for x in range(2 ** n):
            cnt += 1; cands.append(("probability", f'"{format(x, "0%db" % n)}"', abs(pm[x] - pb[x]), float(pb[x]), "RELIABLE"))
        cnt += 1; cands.append(("entropy", "entropy", abs(shannon(pm) - shannon(pb)), shannon(pb), "RELIABLE"))
        cnt += 1; cands.append(("distribution", "total_variation_distance", tvd, 0.0, "RELIABLE"))
        expect_card = n + (2 ** n - 1) + 2 ** n + 1 + 1
        best = max(cands, key=lambda c: c[2])
        above = [c for c in cands if c[2] > ATOL]
        # suite inclusion: the realized suite asserts marginals on outq only
        in_suite = bool(above) and best[0] == "marginal" and int(best[1][2:-1]) in outq
        # pick a witness NOT already in the realized suite where one exists
        omitted = [c for c in above if not (c[0] == "marginal" and int(c[1][2:-1]) in outq)]
        wpick = max(omitted, key=lambda c: c[2]) if omitted else (best if above else None)
        wits.append({"mutant_id": mid, "subject": sid, "profile_id": "QT_0_1_0__COUNT_SUBSTRATE",
            "instances_enumerated": cnt, "cardinality_expected": expect_card,
            "enumeration_complete": cnt == expect_card,
            "n_instances_above_tolerance": len(above), "best_family": best[0], "best_param": best[1],
            "best_exact_diff": round(best[2], 12), "picked_family": wpick[0] if wpick else "",
            "picked_param": wpick[1] if wpick else "", "picked_exact_diff": round(wpick[2], 12) if wpick else 0.0,
            "picked_reference_from_original": round(wpick[3], 12) if wpick else 0.0,
            "picked_reliability": wpick[4] if wpick else "", "witness_in_realized_suite": in_suite,
            "tolerance": ATOL})

        # ---- structural role audit (negative-control measurement, NOT a certificate)
        def transp(g):
            qc = QuantumCircuit(n)
            for x in g: getattr(qc, x["gate"])(*x.get("angles", []), *x["q"])
            from qiskit import transpile
            return transpile(qc, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1, seed_transpiler=20260730)
        tb, tm = transp(base), transp(mg)
        gs_sep = {i.operation.name for i in tb.data} != {i.operation.name for i in tm.data}
        dp_sep = tb.depth() != tm.depth()
        qt_adm.append({"mutant_id": mid, "subject": sid, "contract_equivalent": ce,
            "gateset_separates": gs_sep, "depth_separates": dp_sep,
            "count_substrate_separates": bool(above), "entangled_separates": None,
            "profile_id": "QT_0_1_0__STRUCTURAL_ROLE_AUDIT", "note": "negative-control measurement; no claim class exists for structural evidence"})

        # ---- configuration evidence
        subtol = (not zd_eq) and (not above)
        grid = {str(t): bool([c for c in cands if c[2] > t]) for t in TOL_GRID}
        cfg.append({"mutant_id": mid, "subject": sid, "z_distribution_identical": zd_eq,
            "tolerance_grid_any_witness": json.dumps(grid),
            "tolerance_grid_stable": len(set(grid.values())) == 1,
            "grid_method": "EXACT evaluation of the enumerated instance space at each atol (not resampled); stronger than a sampled grid",
            "any_instance_above_tolerance": bool(above), "max_exact_diff": round(best[2], 12),
            "tolerance": ATOL, "configuration_limited": subtol,
            "limiting_parameter": "tolerance" if subtol else "",
            "would_flip_at": (round(best[2], 12) if subtol else "")})

    # persist the per-case tables now; certificates are built in s3_certify.py from these
    def wcsv(fn, rows, empty=None):
        rows = rows or [empty]
        with open(os.path.join(HERE, fn), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    wcsv("S3_NATIVE_RUNS.csv", runs)
    wcsv("S3_NATIVE_VERDICTS.csv", verds)
    wcsv("S3_CONTRACT_EVIDENCE.csv", contract_ev)
    wcsv("S3_ENDPOINT_STATE_RELATIONS.csv", state_rel)
    wcsv("S3_OBSERVATION_RELATIONS.csv", obs_rel)
    wcsv("S3_ASSERTION_WITNESSES.csv", wits)
    wcsv("S3_CONFIGURATION_EVIDENCE.csv", cfg)
    wcsv("S3_QUTEST_ADMISSIBILITY.csv", qt_adm)
    print("\nS3 part A/B complete:", len(verds), "cases;", Counter(v["verdict"] for v in verds))

if __name__ == "__main__":
    main()
