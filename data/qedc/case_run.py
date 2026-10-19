"""QED-C TFIM workflow case: semantic diagnosis, native action comparison, validation and cost.
Design: data/qedc/PLAN.md (frozen before this script's native runs).

Usage (analytic-tier environment):
  python -I case_run.py <package root> <run tree> <precalculated_data.json> <out dir> [workers]
<run tree>: as for data/output_condition/oc_rerun.py (QUTest 0.1.0 reachable through the frozen adapter).
<precalculated_data.json>: QED-C v2.0.8 `qedcbench/hamiltonian_simulation/_common/precalculated_data.json`,
sha256 88480e85ca8f90813cc5a799c075b96666502391d41b1b3b885eb7fcc45bcaec (checked).
"""
import ast, csv, hashlib, json, os, sys, time, platform
from concurrent.futures import ProcessPoolExecutor
from math import pi
from pathlib import Path
import numpy as np

PKG, TREE, REFP, OUT = (Path(a).resolve() for a in sys.argv[1:5])
WORKERS = int(sys.argv[5]) if len(sys.argv) > 5 else 4
FROZEN = PKG / "data/prospective/mqt_bench/frozen_deps"
sys.path[:0] = [str(TREE / "study/cross_tool_stage/qutest"), str(FROZEN)]
import qutest_adapter as QA                                                  # noqa: E402
from qsurvdiag_confirmatory import compare_threshold, candidate, certify, empirical, T, F, U  # noqa: E402
from scipy.sparse.linalg import expm_multiply                                # noqa: E402
from qiskit import QuantumCircuit                                            # noqa: E402
from qiskit.quantum_info import Statevector, SparsePauliOp                   # noqa: E402

REF_SHA = "88480e85ca8f90813cc5a799c075b96666502391d41b1b3b885eb7fcc45bcaec"
assert hashlib.sha256(REFP.read_bytes()).hexdigest() == REF_SHA
REF = json.load(open(REFP))
K, TT, H_FIELD, J_SPEC = REF["k"], REF["t"], 1.0, 1.0
TAU = TT / K
THETA, LO, HI = 0.05, 1e-10, 1e-8
WIDTHS = list(range(2, 9))                     # the benchmark's default widths (get_circuits min 2, max 8)
J_COMPANION = 0                                # terminal Z on qubit 0
N, R, GUARD = 2000, 12, 3                      # study certification settings
CERT_SEEDS = [42 + r for r in range(R)]; GUARD_SEEDS = CERT_SEEDS[:GUARD]
VAL_MUT = [7042 + r for r in range(R)]; VAL_ORIG = [8042 + r for r in range(R)]   # independent validation streams
QEDC_SHOTS = 100                               # the benchmark's default num_shots

# study difference functions, extracted verbatim from scripts/analytic/r2v_lib.py
_ns = {"np": np}
for node in ast.parse(open(PKG / "scripts/analytic/r2v_lib.py").read()).body:
    if isinstance(node, ast.FunctionDef) and node.name in ("marg", "zexp", "shannon_bits", "tvd", "hellinger", "kl", "ordered_universe"):
        exec(compile(ast.Module([node], []), "r2v_lib", "exec"), _ns)
ordered_universe, hellinger, zexp_p, marg = _ns["ordered_universe"], _ns["hellinger"], _ns["zexp"], _ns["marg"]

# ------------------------------------------------------------------ programs (study gate format)
def tfim_gates(n, zz_angle, terminal_z=None, xbasis=False):
    g = [{"gate": "h", "q": [0]}] + [{"gate": "cx", "q": [k - 1, k]} for k in range(1, n)]
    for _ in range(K):
        g += [{"gate": "rx", "q": [i], "angles": [2 * TAU * H_FIELD]} for i in range(n)]
        for j in range(2):
            for i in range(j % 2, n - 1, 2):
                g += [{"gate": "cx", "q": [i, i + 1]}, {"gate": "rz", "q": [i + 1], "angles": [zz_angle]}, {"gate": "cx", "q": [i, i + 1]}]
    if terminal_z is not None: g.append({"gate": "z", "q": [terminal_z]})
    if xbasis: g += [{"gate": "h", "q": [i]} for i in range(n)]
    return g
PROG = {"P": lambda n, xb=False: tfim_gates(n, 2 * TAU * J_SPEC, xbasis=xb),       # specification-consistent Trotter (researcher-corrected)
        "M": lambda n, xb=False: tfim_gates(n, pi * TAU, xbasis=xb),               # shipped kernel coupling
        "C": lambda n, xb=False: tfim_gates(n, 2 * TAU * J_SPEC, J_COMPANION, xb)} # constructed companion
PAIRS = [("natural", "P", "M"), ("constructed", "P", "C")]

def state(gates, n):
    qc = QuantumCircuit(n)
    for x in gates: getattr(qc, x["gate"])(*x.get("angles", []), *x["q"])
    return Statevector(qc).data
def exact(n):
    terms = [("ZZ", [i, i + 1], J_SPEC) for i in range(n - 1)] + [("X", [i], H_FIELD) for i in range(n)]
    Hm = SparsePauliOp.from_sparse_list(terms, num_qubits=n).to_matrix(sparse=True)
    psi0 = np.zeros(2 ** n, complex); psi0[0] = psi0[-1] = 2 ** -0.5
    return expm_multiply(-1j * TT * Hm, psi0)
def refdist(n):
    return {k: float(v) for k, v in REF[f"Exact TFIM - Qubits{n}"].items() if v > 1e-15}
def refvec(n):
    v = np.zeros(2 ** n)
    for k, x in refdist(n).items(): v[int(k, 2)] = x
    return v / v.sum()
def eq(m): return T if m < LO else (F if m > HI else U)

# ------------------------------------------------------------------ QED-C score (exact reimplementation)
def qedc_hf(p, q):          # qedclib/metrics.py hellinger_fidelity_with_expected, lines 710-750
    ps, qs = sum(p.values()), sum(q.values()); pn = {k: v / ps for k, v in p.items()}; qn = {k: v / qs for k, v in q.items()}
    tot = 0.0
    for k, v in pn.items():
        if k in qn: tot += (np.sqrt(v) - np.sqrt(qn.pop(k))) ** 2
        else: tot += v
    tot += sum(qn.values()); d = np.sqrt(abs(tot)) / np.sqrt(2); return (1 - d ** 2) ** 2
def qedc_polarization(counts, ref, n):   # metrics.py polarization_fidelity, lines 775-816 (n <= 16)
    hf = qedc_hf(counts, ref); u = {format(i, f"0{n}b"): 1 / 2 ** n for i in range(2 ** n)}; f0 = qedc_hf(u, ref)
    return min(1.0, max(0.0, (hf - 1) / (1 - f0) + 1)), hf

# ------------------------------------------------------------------ assertion text
def inst_pragma(inst, n, ref_vals):
    k, key = inst["kind"], inst["key"]
    if k == "marginal": return [f"//% expect marginal m[{key}] p1 ~= {round(inst['ref'], 4)} atol={THETA}"]
    if k == "zmask":
        zs = " ".join(f"Z{i}" for i in range(n) if (key >> i) & 1)
        return [f'//% expect observable "{zs}" ~= {round(inst["ref"], 4)} atol={THETA}']
    if k == "prob": return [f'//% expect probability "{format(key, f"0{n}b")}" ~= {round(inst["ref"], 4)} atol={THETA}']
    if k == "entropy": return [f"//% expect entropy ~= {round(inst['ref'], 4)} atol={THETA}"]
    ref = {format(x, f"0{n}b"): float(ref_vals[x]) for x in range(2 ** n) if ref_vals[x] > 1e-15}
    metric = {"tvd": "total_variation_distance", "hellinger": "hellinger", "kl": "kl"}[k]
    return ["//% expect distribution ref " + json.dumps(ref, separators=(",", ":")), f"//% expect distribution {metric} <= {THETA}"]
def method2_suite(n):       # study-defined acceptance rule for the method-2 score: Hellinger distance <= theta to the upstream reference
    return ["//% expect distribution ref " + json.dumps(refdist(n), separators=(",", ":")), f"//% expect distribution hellinger <= {THETA}"]
def combined_suite(pp, n):  # Policy S: marginals on every qubit and adjacent two-qubit Z products, original-centred
    A = [f"//% expect marginal m[{q}] p1 ~= {round(marg(pp, n, q), 4)} atol={THETA}" for q in range(n)]
    A += [f'//% expect observable "Z{i} Z{i+1}" ~= {round(zexp_p(pp, n, (1 << i) | (1 << (i + 1))), 4)} atol={THETA}' for i in range(n - 1)]
    return A

# ------------------------------------------------------------------ native runner
def run_job(job):
    gates, n, A, seeds = job
    out = []
    for s in seeds:
        t0 = time.perf_counter(); v, msg = QA.run_qutest(QA.make_test(gates, n, A, N, s)); out.append((s, v, round(time.perf_counter() - t0, 3)))
    return out
def kills(out): return sum(v == "KILLED" for _, v, _ in out)
def unsup(out): return sum(v == "UNSUPPORTED" for _, v, _ in out)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cost = {"semantic_seconds": 0.0, "native": {}}
    sem, jobs, keys = {}, [], []
    t_sem = time.perf_counter()
    for n in WIDTHS:
        e = exact(n); r2 = refvec(n)
        st = {k: state(PROG[k](n), n) for k in "PMC"}
        stx = {k: state(PROG[k](n, True), n) for k in "PMC"}
        for label, a, b in PAIRS:
            sa, sb = st[a], st[b]; pa, pb = np.abs(sa) ** 2, np.abs(sb) ** 2
            ordered, alld = ordered_universe(pa, pb, n)
            m_state = abs(abs(np.vdot(sa, sb)) - 1); m_obs = float(np.max(np.abs(pa - pb)))
            suite_keys = set()                                         # the executed method-2 suite holds no original-centred instance
            w = next((x for x in ordered if (x["kind"], x["key"]) not in suite_keys and compare_threshold(x["d"], THETA) is T), None)
            c = next((x for x in ordered if (x["kind"], x["key"]) not in suite_keys and compare_threshold(x["d"], THETA) is F), None)
            top = max(alld)
            t_rej = lambda p: hellinger(p, r2) > THETA                 # the executed suite's ideal decision
            rel = {"R_C": eq(m_state), "R_S": eq(m_state), "R_O": eq(m_obs),
                   "R_A": compare_threshold(top, THETA) if eq(m_obs) is F else F,
                   "R_T": (T if (t_rej(pb) and not t_rej(pa)) else F) if eq(m_obs) is F else F}
            cand, path, und = candidate(rel)
            # supplementary X-basis statistic (frozen rule): constructed pair -> X-parity of every qubit;
            # natural pair -> first instance in witness order on the X-basis distributions whose difference exceeds theta
            pxa, pxb = np.abs(stx[a]) ** 2, np.abs(stx[b]) ** 2
            ox, _ = ordered_universe(pxa, pxb, n)
            if label == "constructed":
                xs = next(x for x in ox if x["kind"] == "zmask" and x["key"] == 2 ** n - 1)
            else:
                xs = next((x for x in ox if compare_threshold(x["d"], THETA) is T), None)
            sem[(label, n)] = {"pair": label, "n": n, "original": a, "counterpart": b,
                "overlap": abs(np.vdot(sa, sb)) ** 2, "state_margin": m_state, "obs_margin": m_obs,
                "fid_exact_original": abs(np.vdot(e, sa)) ** 2, "fid_exact_counterpart": abs(np.vdot(e, sb)) ** 2,
                "hellinger_to_upstream_ref_original": hellinger(pa, r2), "hellinger_to_upstream_ref_counterpart": hellinger(pb, r2),
                "qedc_ideal_hf_original": qedc_hf({format(i, f"0{n}b"): pa[i] for i in range(2 ** n)}, refdist(n)),
                "qedc_ideal_hf_counterpart": qedc_hf({format(i, f"0{n}b"): pb[i] for i in range(2 ** n)}, refdist(n)),
                "max_admitted_d": top, "universe_size": len(alld),
                "relations": {k: v.value for k, v in rel.items()}, "candidate": cand, "path_end": und,
                "witness": None if w is None else {k: w[k] for k in ("kind", "key", "d")},
                "control": None if c is None else {k: c[k] for k in ("kind", "key", "d")},
                "xstat": None if xs is None else {k: xs[k] for k in ("kind", "key", "d")},
                "x_parity_original": float(zexp_p(pxa, n, 2 ** n - 1)), "x_parity_counterpart": float(zexp_p(pxb, n, 2 ** n - 1))}
            ga, gb, gxa, gxb = PROG[a](n), PROG[b](n), PROG[a](n, True), PROG[b](n, True)
            T2 = method2_suite(n); S = combined_suite(pa, n)
            def add(tag, gates, A, seeds):
                jobs.append((gates, n, A, seeds)); keys.append((label, n, tag, len(A)))
            # A: the existing scoring procedure (study-defined acceptance), certification streams
            add("A_orig_cert", ga, T2, CERT_SEEDS); add("A_mut_cert", gb, T2, CERT_SEEDS)
            # validation streams for every complete procedure
            add("A_orig_val", ga, T2, VAL_ORIG); add("A_mut_val", gb, T2, VAL_MUT)
            add("B_orig_val", ga, T2 + S, VAL_ORIG); add("B_mut_val", gb, T2 + S, VAL_MUT)
            if w is not None:      # QSurvDiag evidence for a suite-omission candidate
                Aw = inst_pragma(w, n, pa); Ac = inst_pragma(c, n, pa) if c is not None else None
                add("W_mut_cert", gb, Aw, CERT_SEEDS); add("W_orig_guard", ga, Aw, GUARD_SEEDS)
                if Ac: add("Ctl_mut_cert", gb, Ac, CERT_SEEDS); add("Ctl_orig_guard", ga, Ac, GUARD_SEEDS)
                add("D_orig_val", ga, T2 + Aw, VAL_ORIG); add("D_mut_val", gb, T2 + Aw, VAL_MUT)
            if xs is not None:     # C: the fixed supplementary measurement (gates after the program, then measure)
                Ax = inst_pragma(xs, n, pxa)
                add("X_mut_cert", gxb, Ax, CERT_SEEDS); add("X_orig_guard", gxa, Ax, GUARD_SEEDS)
                add("X_orig_val", gxa, Ax, VAL_ORIG); add("X_mut_val", gxb, Ax, VAL_MUT)
    cost["semantic_seconds"] = round(time.perf_counter() - t_sem, 3)
    t0 = time.time()
    with ProcessPoolExecutor(WORKERS) as ex:
        res = list(ex.map(run_job, jobs))
    cost["native_wall_seconds"] = round(time.time() - t0, 1)
    nat = {}
    with open(OUT / "NATIVE_RUNS.csv", "w", newline="") as f:
        wr = csv.writer(f, lineterminator="\n"); wr.writerow(["pair", "n", "run", "n_assertions", "seed", "verdict", "seconds"])
        for (label, n, tag, na), out in zip(keys, res):
            nat[(label, n, tag)] = out
            for s, v, sec in out: wr.writerow([label, n, tag, na, s, v, sec])
            c = cost["native"].setdefault(tag.split("_")[0], {"executions": 0, "shots": 0, "seconds": 0.0})
            c["executions"] += len(out); c["shots"] += N * len(out); c["seconds"] = round(c["seconds"] + sum(x[2] for x in out), 3)
    # QED-C score itself from Aer counts at the benchmark default (100 shots) and at N, seeds of the A streams
    rows = []
    for (label, n), s in sem.items():
        x = {k: (v if not isinstance(v, (np.floating,)) else float(v)) for k, v in s.items()}
        for who, g in (("original", PROG[s["original"]](n)), ("counterpart", PROG[s["counterpart"]](n))):
            for shots in (QEDC_SHOTS, N):
                sc = [qedc_polarization(QA._counts(g, n, shots, sd), refdist(n), n)[0] for sd in VAL_ORIG[:R]]
                x[f"qedc_score_{who}_{shots}shots_mean"] = float(np.mean(sc)); x[f"qedc_score_{who}_{shots}shots_min"] = float(np.min(sc))
        ev = {}
        cand = s["candidate"]
        get = lambda tag: nat.get((label, n, tag))
        a_m = get("A_mut_cert"); a_o = get("A_orig_cert")
        x["A_cert_mutant_kills"] = kills(a_m); x["A_cert_original_fails"] = kills(a_o)
        for tag in ("A_orig_val", "A_mut_val", "B_orig_val", "B_mut_val", "D_orig_val", "D_mut_val", "X_orig_val", "X_mut_val",
                    "W_mut_cert", "W_orig_guard", "Ctl_mut_cert", "Ctl_orig_guard", "X_mut_cert", "X_orig_guard"):
            o = get(tag); x[tag] = None if o is None else f"{kills(o)}/{len(o)}" + (f" ({unsup(o)} unsupported)" if o and unsup(o) else "")
        # evidence record for certify(): items that this case's record can establish
        allun = any(unsup(get(t) or []) for t in ("A_mut_cert", "A_orig_cert"))
        ev.update({"OB01": "failed" if allun else "satisfied", "OB04": "satisfied", "OB05": "satisfied",
                   "OB06": "satisfied", "OB07": "satisfied" if s["relations"]["R_O"] != "undecided" else "unknown",
                   "OB08": "satisfied", "OB09": "satisfied", "OB10": "satisfied" if s["universe_size"] == 2 ** (n + 1) + n + 3 else "failed",
                   "OB14": "satisfied", "OB17": "satisfied", "OB18": "satisfied", "OB19": "satisfied",
                   "OB02": "satisfied" if kills(a_o) / R <= 0.10 else "failed"})
        if cand == "CL5": ev["OB16"] = "satisfied" if compare_threshold(s["max_admitted_d"], THETA) is F else "failed"
        if cand == "CL4":
            w = s["witness"]; ev["OB11"] = "satisfied"; ev["OB12"] = "satisfied" if w["kind"] in ("marginal", "zmask", "prob", "entropy", "tvd", "hellinger", "kl") else "failed"
            ev["OB16"] = "satisfied" if compare_threshold(w["d"], THETA) is T else "failed"
            wg, wm, cg, cm = get("W_orig_guard"), get("W_mut_cert"), get("Ctl_orig_guard"), get("Ctl_mut_cert")
            guard_bad = (kills(wg) if wg else 0) + (kills(cg) if cg else 0)
            if guard_bad: ev["OB02"] = "failed"
            ev["OB13"] = "unknown" if (unsup(wm) or (wg and kills(wg))) else ("satisfied" if kills(wm) == R else "failed")
            ev["OB15"] = ("unknown" if cm is None else ("unknown" if (unsup(cm) or (cg and kills(cg))) else ("failed" if kills(cm) == R else "satisfied")))
        rel = {k: {"true": T, "false": F, "undecided": U}[v] for k, v in s["relations"].items()}
        rep = certify(rel, ev, empirical_verdict=empirical(kills(a_m), R))
        x["report"] = rep["report"]; x["unmet"] = ";".join(rep.get("failed", []) + rep.get("unknown", []))
        rows.append(x)
    json.dump({"settings": {"widths": WIDTHS, "N": N, "R": R, "guard": GUARD, "theta": THETA, "cert_seeds": CERT_SEEDS,
                            "val_mutant_seeds": VAL_MUT, "val_original_seeds": VAL_ORIG, "qedc_shots": QEDC_SHOTS,
                            "K": K, "t": TT, "J_spec": J_SPEC, "h": H_FIELD, "companion_qubit": J_COMPANION},
               "cases": rows, "cost": cost, "machine": platform.platform(), "workers": WORKERS},
              open(OUT / "CASE_RESULTS.json", "w"), indent=1, default=lambda o: o if not isinstance(o, np.generic) else o.item())
    print(json.dumps(cost))

if __name__ == "__main__":
    main()
