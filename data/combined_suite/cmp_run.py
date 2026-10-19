"""Matched repair comparison: Policy D (QSurvDiag's baseline-plus-witness suite) against Policy S (the combined
suite) on the pre-confirmation suite-omission candidates of the corpus and MQT Bench.
Design: data/combined_suite/PLAN.md (frozen before the native runs).

Usage (analytic-tier environment):
  python -I cmp_run.py <package root> <run tree> <out dir> [workers] [--semantic-only]
"""
import ast, csv, hashlib, json, os, sys, time, platform
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

PKG, TREE, OUT = (Path(a).resolve() for a in sys.argv[1:4])
WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 4
SEMANTIC_ONLY = "--semantic-only" in sys.argv
FROZEN = PKG / "data/prospective/mqt_bench/frozen_deps"
sys.path[:0] = [str(TREE / "study/cross_tool_stage/qutest"), str(FROZEN)]
import qutest_adapter as QA                                   # noqa: E402
from qsurvdiag_confirmatory import compare_threshold, T       # noqa: E402
from qutest_execution_adapter import adapt                    # noqa: E402
from serialization_adapter import emit_name                   # noqa: E402
from qiskit import QuantumCircuit                             # noqa: E402
from qiskit.quantum_info import Statevector                   # noqa: E402

THETA, N, R = 0.05, 2000, 12
VAL_MUT = [9042 + r for r in range(R)]; VAL_ORIG = [10042 + r for r in range(R)]
_ns = {"np": np}
for node in ast.parse(open(PKG / "scripts/analytic/r2v_lib.py").read()).body:
    if isinstance(node, ast.FunctionDef) and node.name in ("marg", "zexp", "shannon_bits", "tvd", "hellinger", "kl", "ordered_universe"):
        exec(compile(ast.Module([node], []), "r2v_lib", "exec"), _ns)
marg, zexp, shannon, ordered_universe = _ns["marg"], _ns["zexp"], _ns["shannon_bits"], _ns["ordered_universe"]

def sv(gates, n):              # the study's simulator convention (e1_relations._sv)
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", []); getattr(qc, g["gate"])(*a, *[int(x) for x in g["q"]])
    return Statevector.from_int(0, dims=(2,) * n).evolve(qc).data
def lowered(gates): return [{**x, "gate": emit_name(x["gate"])} for x in adapt(gates)]

def cases():
    out = []
    for j in (json.loads(l) for l in open(PKG / "data/certification/outcomes/R2V_NATIVE_JOBS_ARMS.jsonl")):
        if j["arm"] == "corpus" and j["purpose"] == "OB13":
            out.append({"arm": "corpus", "case": j["case"], "n": j["n"], "orig": j["orig_gates"], "mut": j["mut_gates"],
                        "orig_key": hashlib.sha256(json.dumps(j["orig_gates"], sort_keys=True).encode()).hexdigest()[:16], "w_kind": j["inst"]["kind"], "w_key": j["inst"]["key"]})
    fin = {r["case_key"]: r for r in csv.DictReader(open(PKG / "data/certification/outcomes/R2V_FINAL_CORPUS.csv"))}
    for c in out:
        r = fin[c["case"]]; c["certified"] = r["v2_report"] == "CL4"; c["unmet"] = r["unmet"]; c["subject"] = r.get("subject", "")
    mq = PKG / "data/prospective/mqt_bench"
    S = {s["subject"]: s for s in json.load(open(mq / "subjects/SUBJECTS.json"))}
    man = {r["mutant_id"]: r for r in csv.DictReader(open(mq / "population/MUTANT_MANIFEST.csv"))}
    for r in csv.DictReader(open(mq / "records/stage_c/C3_REPORTS.csv")):
        if r["v2_candidate"] != "CL4" or r["native_verdict"] != "SURVIVED": continue
        s = S[r["subject"]]; mg = json.load(open(mq / "population" / man[r["case"]]["gates_path"]))
        out.append({"arm": "mqt", "case": r["case"], "n": s["n"], "orig": s["prep"] + s["body"], "mut": s["prep"] + mg,
                    "orig_key": r["subject"], "w_kind": r["w_kind"], "w_key": int(r["w_key"]) if r["w_key"] else None,
                    "certified": r["v2_report"] == "CL4", "unmet": r["unmet"], "subject": r["subject"]})
    return out

def pragma(kind, key, n, pp):
    if kind == "marginal": return [f"//% expect marginal m[{key}] p1 ~= {round(marg(pp, n, key), 4)} atol={THETA}"]
    if kind == "zmask":
        zs = " ".join(f"Z{i}" for i in range(n) if (key >> i) & 1)
        return [f'//% expect observable "{zs}" ~= {round(zexp(pp, n, key), 4)} atol={THETA}']
    if kind == "prob": return [f'//% expect probability "{format(key, f"0{n}b")}" ~= {round(float(pp[key]), 4)} atol={THETA}']
    if kind == "entropy": return [f"//% expect entropy ~= {round(shannon(pp), 4)} atol={THETA}"]
    ref = {format(x, f"0{n}b"): float(pp[x]) for x in range(2 ** n) if pp[x] > 1e-15}
    metric = {"tvd": "total_variation_distance", "hellinger": "hellinger", "kl": "kl"}[kind]
    return ["//% expect distribution ref " + json.dumps(ref, separators=(",", ":")), f"//% expect distribution {metric} <= {THETA}"]
def baseline(n, pp): return [l for q in range(n) for l in pragma("marginal", q, n, pp)]        # S_MIN: every qubit is the output register
def adjacent(n, pp): return [l for i in range(n - 1) for l in pragma("zmask", (1 << i) | (1 << (i + 1)), n, pp)]

def run_job(job):
    gates, n, A, seeds = job; res = []
    for s in seeds:
        t0 = time.perf_counter(); v, _ = QA.run_qutest(QA.make_test(lowered(gates), n, A, N, s)); res.append((s, v, round(time.perf_counter() - t0, 3)))
    return res

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    C = cases(); rows, jobs, keys, ostate = [], [], [], {}
    t_ref = 0.0
    for c in C:
        n = c["n"]
        t0 = time.perf_counter()
        if c["orig_key"] not in ostate: ostate[c["orig_key"]] = np.abs(sv(c["orig"], n)) ** 2
        t_ref += time.perf_counter() - t0
        pp = ostate[c["orig_key"]]
        t1 = time.perf_counter()                                       # Policy D's diagnostic analysis for this case
        pm = np.abs(sv(c["mut"], n)) ** 2
        ordered, alld = ordered_universe(pp, pm, n)
        sk = {("marginal", q) for q in range(n)}
        w = next((x for x in ordered if (x["kind"], x["key"]) not in sk and compare_threshold(x["d"], THETA) is T), None)
        t_diag = time.perf_counter() - t1
        assert w is not None and w["kind"] == c["w_kind"] and (w["key"] == c["w_key"] or w["kind"] in ("entropy", "tvd", "hellinger", "kl")), (c["case"], w, c["w_kind"], c["w_key"])
        D = baseline(n, pp) + pragma(w["kind"], w["key"], n, pp)
        S = baseline(n, pp) + adjacent(n, pp)
        adj = w["kind"] == "zmask" and bin(w["key"]).count("1") == 2 and (w["key"] >> (w["key"].bit_length() - 2)) == 3
        s_ideal = [x for x in ordered if (x["kind"] == "zmask" and bin(x["key"]).count("1") == 2 and (x["key"] >> (x["key"].bit_length() - 2)) == 3)]
        s_kill_ideal = any(compare_threshold(x["d"], THETA) is T for x in s_ideal)
        row = {"arm": c["arm"], "case": c["case"], "program": c["orig_key"],
               "n": n, "certified_by_D": c["certified"], "unmet": c["unmet"], "w_kind": w["kind"], "w_key": w["key"], "w_d": w["d"],
               "witness_in_S": adj, "S_ideal_kills": s_kill_ideal, "D_assertions": len(D), "S_assertions": len(S),
               "diag_seconds": round(t_diag, 4), "D_suite_id": json.dumps([c["orig_key"], w["kind"], w["key"]]), "S_suite_id": c["orig_key"]}
        rows.append(row)
        if not SEMANTIC_ONLY:
            jobs.append((c["mut"], n, D, VAL_MUT)); keys.append((c["case"], "D_mut"))
            jobs.append((c["mut"], n, S, VAL_MUT)); keys.append((c["case"], "S_mut"))
        c["_D"], c["_S"] = D, S
    # original validity: one run per unique (original, suite)
    seen = {}
    if not SEMANTIC_ONLY:
        for c, row in zip(C, rows):
            for pol, sid in (("D", row["D_suite_id"]), ("S", row["S_suite_id"])):
                k = (c["orig_key"], pol, sid)
                if k in seen: continue
                seen[k] = len(jobs); jobs.append((c["orig"], c["n"], c["_" + pol], VAL_ORIG)); keys.append((k, f"{pol}_orig"))
    t0 = time.time(); res = []
    if jobs:
        with ProcessPoolExecutor(WORKERS) as ex: res = list(ex.map(run_job, jobs))
    wall = time.time() - t0
    nat = dict(zip(keys, res))
    with open(OUT / "CMP_NATIVE_RUNS.csv", "w", newline="") as f:
        wr = csv.writer(f, lineterminator="\n"); wr.writerow(["key", "role", "seed", "verdict", "seconds"])
        for (k, role), out in nat.items():
            for s, v, sec in out: wr.writerow([json.dumps(k) if isinstance(k, tuple) else k, role, s, v, sec])
    K = lambda o: sum(v == "KILLED" for _, v, _ in o); Uu = lambda o: sum(v == "UNSUPPORTED" for _, v, _ in o)
    for c, row in zip(C, rows):
        if SEMANTIC_ONLY: continue
        for pol, sid in (("D", row["D_suite_id"]), ("S", row["S_suite_id"])):
            mo = nat[(c["case"], f"{pol}_mut")]; oo = nat[((c["orig_key"], pol, sid), f"{pol}_orig")]
            row[f"{pol}_mut_kills"] = K(mo); row[f"{pol}_mut_unsupported"] = Uu(mo)
            row[f"{pol}_orig_fails"] = K(oo); row[f"{pol}_orig_unsupported"] = Uu(oo)
            row[f"{pol}_supported"] = K(mo) == R and K(oo) <= 1 and not Uu(mo) and not Uu(oo)
            row[f"{pol}_mut_seconds"] = round(sum(x[2] for x in mo), 2)
    with open(OUT / "CMP_CASES.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]) + [k for k in (rows[-1] if not SEMANTIC_ONLY else {}) if k not in rows[0]], lineterminator="\n")
        wr.writeheader(); wr.writerows(rows)
    origrows = [{"original": k[0], "policy": k[1], "suite": k[2], "fails": K(nat[(k, f"{k[1]}_orig")]),
                 "unsupported": Uu(nat[(k, f"{k[1]}_orig")]), "seconds": round(sum(x[2] for x in nat[(k, f"{k[1]}_orig")]), 2)} for k in seen]
    json.dump({"settings": {"N": N, "R": R, "theta": THETA, "val_mutant_seeds": VAL_MUT, "val_original_seeds": VAL_ORIG},
               "population": {"cases": len(rows), "corpus": sum(r["arm"] == "corpus" for r in rows), "mqt": sum(r["arm"] == "mqt" for r in rows)},
               "original_validations": origrows, "reference_generation_seconds": round(t_ref, 3),
               "diagnosis_seconds_total": round(sum(r["diag_seconds"] for r in rows), 3), "native_wall_seconds": round(wall, 1),
               "executions": sum(len(o) for o in res), "shots": N * sum(len(o) for o in res), "workers": WORKERS,
               "machine": platform.platform()}, open(OUT / "CMP_SUMMARY.json", "w"), indent=1)
    print("cases", len(rows), "jobs", len(jobs), "wall", round(wall, 1))

if __name__ == "__main__":
    main()
