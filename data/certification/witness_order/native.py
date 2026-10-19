"""Native evidence of the v3 amendment (AMENDMENT.md): the controls that the closed witness order forms where the v2 order formed
none, and the QED-C X-basis statistic it selects where the v2 order selected none.

Usage (analytic-tier environment; run tree as assembled by scripts/reproduce_analytic.py):
  R2V_PA=<tree>/artifact/ QSD_ROOT=<tree>/study \
  python -I native.py <package root> <run tree> <precalculated_data.json> <out dir>
Control jobs use r2v_lib.native_check (V2_SPECIFICATION.md section 9: the assertion alone, guard on the original at
seeds 42-44, mutant at 42-53, N = 2000); the recorded witness check (OB13) is repeated first as a check of the
environment. QED-C runs use the programs and seed streams of data/qedc/case_run.py. Writes CHANGES.csv,
NATIVE_RUNS.csv and QEDC_X_RUNS.csv to <out dir>.
"""
import csv, json, sys, time
from pathlib import Path
import numpy as np
PKG, TREE, REFP, OUT = (Path(a).resolve() for a in sys.argv[1:5])
OUT.mkdir(parents=True, exist_ok=True)
R2 = PKG / "data/certification/outcomes"
sys.path[:0] = [str(PKG / "scripts/analytic")]
import r2v_lib as V                                                          # noqa: E402
from qiskit import QuantumCircuit                                            # noqa: E402
from qiskit.quantum_info import Statevector                                  # noqa: E402

def closed_order(pp, pm, n):
    """AMENDMENT.md: the v2 witness order followed by the single-qubit Z products, by qubit index."""
    ordered, alld = V.ordered_universe(pp, pm, n)
    for q in range(n):
        m = 1 << q; a = V.zexp(pp, n, m)
        ordered.append({"kind": "zmask", "key": m, "d": abs(a - V.zexp(pm, n, m)), "ref": a})
    assert len(ordered) == len(alld) == 2 ** (n + 1) + n + 3
    return ordered

def sv(gates, n):                                                            # as frozen_deps/r2v_arms.py
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", [])
        (getattr(qc, g["gate"])(*a, *[int(i) for i in g["q"]]) if a else getattr(qc, g["gate"])(*[int(i) for i in g["q"]]))
    return np.asarray(Statevector.from_int(0, dims=(2,) * n).evolve(qc).data)

# Bugs4Q-Framework qiskit/26, fixed_26.py (original) and buggy_26.py (mutant); sha256 in
# data/external/defects/E5_DEFECT_MANIFEST.csv. Both circuits act on two qubits from |00>.
DEFECT_26 = {"orig": [{"gate": "h", "q": [0]}, {"gate": "x", "q": [1]}, {"gate": "cx", "q": [0, 1]}],
             "mut": [{"gate": "h", "q": [0]}, {"gate": "h", "q": [1]}, {"gate": "cx", "q": [0, 1]}]}
JOBS = {json.loads(l)["job_id"]: json.loads(l) for l in open(R2 / "R2V_NATIVE_JOBS_ARMS.jsonl")}

def candidates_without_control():
    for f, arm, key in (("R2V_FINAL_PRIMARY.csv", "primary", "case_key"), ("R2V_FINAL_WIDTH.csv", "width", "case_key"),
                        ("R2V_FINAL_CORPUS.csv", "corpus", "case_key"), ("R2V_FINAL_EXTERNAL.csv", "external", "case_key"),
                        ("R2V_FINAL_DEFECT.csv", "defect", "defect_id")):
        for r in csv.DictReader(open(R2 / f)):
            if r.get("v2_candidate") == "CL4" and not r["c_kind"]:
                if arm == "defect":
                    yield arm, r[key], int(r["n"]), DEFECT_26["orig"], DEFECT_26["mut"], r
                else:
                    j = JOBS[f"{arm}|{r[key]}|OB13"]; yield arm, r[key], int(r["n"]), j["orig_gates"], j["mut_gates"], r

changes, native = [], []
for arm, case, n, og, mg, r in candidates_without_control():
    assert arm == "defect" and case == "26" or (arm, case) == ("corpus", "qra_cases_v1_1/QRA_360"), (arm, case)
    pp, pm = np.abs(sv(og, n)) ** 2, np.abs(sv(mg, n)) ** 2
    order = closed_order(pp, pm, n); k2 = len(order) - n
    w = next(x for x in order if (x["kind"], str(x["key"])) == (r["w_kind"], r["w_key"]))
    assert order.index(w) < k2 and V.compare_threshold(w["d"], V.THETA) is V.T
    # the record shows no v2 instance outside the suite below theta, so the control is the first appended instance below it
    c = next(x for x in order[k2:] if V.compare_threshold(x["d"], V.THETA) is V.F)
    changes.append({"population": arm, "case": case, "selection": "control", "v2": "none",
                    "v3": f"{c['kind']} {c['key']}", "v3_d": c["d"]})
    for purpose, inst in (("OB13", w), ("OB15", c)):
        lines = V.pragmas(inst, n, pp); t0 = time.time(); res = V.native_check(mg, og, n, lines)
        st = V.ob13_status(res) if purpose == "OB13" else V.ob15_status(res)
        native.append({"job_id": f"{arm}|{case}|{purpose}", "arm": arm, "case": case, "purpose": purpose, "n": n,
                       "inst_kind": inst["kind"], "inst_key": inst["key"], "inst_d": inst["d"], "lines": " | ".join(lines),
                       **res, "status": st, "seconds": round(time.time() - t0, 1)})
        print(native[-1]["job_id"], lines, "guard fails", res["guard_fails"], "kills", res["kills"], "->", st, flush=True)

# QED-C shipped-coupling pair (P, M): X-basis statistic under both orders, every default width
src = open(PKG / "data/qedc/case_run.py").read().split("# ------------------------------------------------------------------ native runner")[0]
sys.argv = ["case_run", str(PKG), str(TREE), str(REFP), str(OUT)]
g = {"__name__": "native"}; exec(src, g)
qruns = []
for n in g["WIDTHS"]:
    ga, gb = g["PROG"]["P"](n, True), g["PROG"]["M"](n, True)
    pa, pb = np.abs(g["state"](ga, n)) ** 2, np.abs(g["state"](gb, n)) ** 2
    order = closed_order(pa, pb, n); k2 = len(order) - n
    first = lambda xs: next((x for x in xs if V.compare_threshold(x["d"], V.THETA) is V.T), None)
    x2, x3 = first(order[:k2]), first(order)
    if x2 is not None:
        assert x3 is x2; continue
    changes.append({"population": "qedc", "case": f"natural n={n}", "selection": "X-basis statistic", "v2": "none",
                    "v3": f"{x3['kind']} {x3['key']}", "v3_d": x3["d"]})
    A = g["inst_pragma"](x3, n, pa)
    for tag, gates, seeds in (("X_mut_cert", gb, g["CERT_SEEDS"]), ("X_orig_guard", ga, g["GUARD_SEEDS"]),
                              ("X_orig_val", ga, g["VAL_ORIG"]), ("X_mut_val", gb, g["VAL_MUT"])):
        for s in seeds:
            t0 = time.perf_counter(); v, _ = g["QA"].run_qutest(g["QA"].make_test(gates, n, A, g["N"], s))
            qruns.append({"pair": "natural", "n": n, "run": tag, "n_assertions": len(A), "seed": s, "verdict": v,
                          "seconds": round(time.perf_counter() - t0, 3)})
        print("qedc n =", n, A, tag, "KILLED", sum(x["verdict"] == "KILLED" for x in qruns if x["run"] == tag and x["n"] == n),
              "of", len(seeds), flush=True)

for name, rows in (("CHANGES.csv", changes), ("NATIVE_RUNS.csv", native), ("QEDC_X_RUNS.csv", qruns)):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
