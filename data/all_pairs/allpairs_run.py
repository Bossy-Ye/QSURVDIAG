"""All-pairs comparison: Policy D (baseline marginals plus the archived candidate witness) against Policy A (baseline
marginals plus Z_i Z_j for every unordered pair i < j) on the 210 suite-omission candidates of the matched repair
comparison, both at N = 8,000. Design: data/all_pairs/PLAN.md (committed before the native runs).

Every execution runs through the pinned qutest CLI (verbose; the verdict of record) and through QUTest's own
discover_tests/run_test in this process with the backend's counts recorded (qutest_capture.py). The runner checks,
per execution, that the CLI verdict, the CLI's per-assertion results and values, and the in-process results agree,
and archives the histogram. Histograms are stored once per (program, seed) after checking that every execution of
that program at that seed saw the same counts.

Usage (analytic-tier environment):
  python -I allpairs_run.py <package root> <run tree> <out dir> [workers] [--semantic-only]
"""
import ast, csv, gzip, hashlib, json, re, subprocess, sys, tempfile, time, platform
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

PKG, TREE, OUT = (Path(a).resolve() for a in sys.argv[1:4])
WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 4
SEMANTIC_ONLY = "--semantic-only" in sys.argv
FROZEN = PKG / "data/prospective/mqt_bench/frozen_deps"
sys.path[:0] = [str(Path(__file__).resolve().parent), str(TREE / "study/cross_tool_stage/qutest"), str(FROZEN)]
import qutest_adapter as QA                                   # noqa: E402
from qsurvdiag_confirmatory import compare_threshold, T       # noqa: E402
from qutest_execution_adapter import adapt                    # noqa: E402
from serialization_adapter import emit_name                   # noqa: E402
from qiskit import QuantumCircuit                             # noqa: E402
from qiskit.quantum_info import Statevector                   # noqa: E402

THETA, N, R = 0.05, 8000, 12
VAL_MUT = [11042 + r for r in range(R)]; VAL_ORIG = [12042 + r for r in range(R)]     # fresh streams, paired across policies
_ns = {"np": np}
for node in ast.parse(open(PKG / "scripts/analytic/r2v_lib.py").read()).body:
    if isinstance(node, ast.FunctionDef) and node.name in ("marg", "zexp", "shannon_bits", "tvd", "hellinger", "kl", "ordered_universe"):
        exec(compile(ast.Module([node], []), "r2v_lib", "exec"), _ns)
marg, zexp, shannon, ordered_universe = _ns["marg"], _ns["zexp"], _ns["shannon_bits"], _ns["ordered_universe"]
# cohort, simulator convention, assertion text and lowering: unchanged from the matched repair comparison
_cmp = {}
src = open(PKG / "data/combined_suite/cmp_run.py").read()
for node in ast.parse(src).body:
    if isinstance(node, ast.FunctionDef) and node.name in ("sv", "lowered", "cases", "pragma", "baseline", "adjacent"):
        exec(compile(ast.Module([node], []), "cmp_run", "exec"), _cmp)
_cmp.update({"np": np, "PKG": PKG, "json": json, "csv": csv, "hashlib": hashlib, "QuantumCircuit": QuantumCircuit, "Statevector": Statevector,
             "adapt": adapt, "emit_name": emit_name, "marg": marg, "zexp": zexp, "shannon": shannon, "THETA": THETA})
sv, lowered, cases, pragma, baseline, adjacent = (_cmp[k] for k in ("sv", "lowered", "cases", "pragma", "baseline", "adjacent"))
def allpairs(n, pp): return [l for i in range(n) for j in range(i + 1, n) for l in pragma("zmask", (1 << i) | (1 << j), n, pp)]

LINE = re.compile(r"^      ([✓✗!]) (.*)$")        # assertion lines (six-space indent); the test line has two
VAL = re.compile(r"= (-?[0-9.]+(?:e-?[0-9]+)?)")
def run_job(job):
    import qutest_capture as C
    gates, n, A, seeds = job; out = []
    for s in seeds:
        text = QA.make_test(lowered(gates), n, A, N, s)
        with tempfile.NamedTemporaryFile("w", suffix=".qasm", delete=False) as f:
            f.write(text); p = f.name
        t0 = time.perf_counter(); r = subprocess.run([QA.QUTEST, "run", "-v", p], capture_output=True, text=True, timeout=900); t_cli = time.perf_counter() - t0
        o = (r.stdout + r.stderr).strip(); summ = o.splitlines()[-1] if o else ""
        cli = "UNSUPPORTED" if "error" in summ else ("KILLED" if "failed" in summ else ("SURVIVED" if "passed" in summ else "UNSUPPORTED"))
        lines = [LINE.match(l) for l in o.splitlines()]; lines = [m for m in lines if m]
        cli_st = "".join({"✓": "P", "✗": "F", "!": "E"}[m.group(1)] for m in lines)
        cli_val = [float(VAL.search(m.group(2)).group(1)) if VAL.search(m.group(2)) else None for m in lines]
        from qutest.discovery import discover_tests
        import qutest.runner as RR
        tcs = discover_tests(p); C._CAP.clear(); t1 = time.perf_counter(); res = RR.run_test(tcs[0]); t_in = time.perf_counter() - t1
        Path(p).unlink(missing_ok=True)
        counts = dict(C._CAP[0]); st = {"pass": "SURVIVED", "fail": "KILLED", "error": "UNSUPPORTED"}[res.status.value]
        in_st = "".join({"pass": "P", "fail": "F", "error": "E"}[a.status.value] for a in res.assertions)
        re_st, t_eval = C.rescore(tcs[0], counts)                                 # QUTest's own functions on the archived counts
        vals_ok = len(cli_val) == len(res.assertions) and all(
            (cv is None) or (a.actual is not None and abs(round(float(a.actual), 4) - cv) <= 1.01e-4) for cv, a in zip(cli_val, res.assertions))
        hid = hashlib.sha256(json.dumps(sorted(counts.items())).encode()).hexdigest()[:20]
        out.append({"seed": s, "cli": cli, "inproc": st, "cli_assertions": cli_st, "inproc_assertions": in_st, "values_agree": vals_ok, "rescored_assertions": re_st, "eval_seconds": round(t_eval, 4),
                    "hist_id": hid, "counts": counts, "cli_seconds": round(t_cli, 3), "inproc_seconds": round(t_in, 4)})
    return out

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    arch = {r["case"]: r for r in csv.DictReader(open(PKG / "data/combined_suite/CMP_CASES.csv"))}
    Cs = cases(); rows, jobs, keys, ostate = [], [], [], {}
    t_ref = 0.0
    for c in Cs:
        n = c["n"]; a = arch[c["case"]]
        t0 = time.perf_counter()
        if c["orig_key"] not in ostate: ostate[c["orig_key"]] = np.abs(sv(c["orig"], n)) ** 2
        t_ref += time.perf_counter() - t0
        pp = ostate[c["orig_key"]]
        t1 = time.perf_counter()
        pm = np.abs(sv(c["mut"], n)) ** 2
        ordered, alld = ordered_universe(pp, pm, n)
        sk = {("marginal", q) for q in range(n)}
        w = next((x for x in ordered if (x["kind"], x["key"]) not in sk and compare_threshold(x["d"], THETA) is T), None)
        t_diag = time.perf_counter() - t1
        # the archived witness is kept; the recomputation only checks it
        assert w is not None and w["kind"] == a["w_kind"] and (str(w["key"]) if w["key"] is not None else "") == a["w_key"], (c["case"], w, a["w_kind"], a["w_key"])
        t2 = time.perf_counter()
        D = baseline(n, pp) + pragma(w["kind"], w["key"], n, pp)
        Apol = baseline(n, pp) + allpairs(n, pp)
        t_ref += time.perf_counter() - t2
        in_A = w["kind"] == "zmask" and bin(w["key"]).count("1") == 2
        a_ideal = any(compare_threshold(x["d"], THETA) is T for x in ordered if x["kind"] == "zmask" and bin(x["key"]).count("1") == 2)
        rows.append({"arm": c["arm"], "case": c["case"], "program": c["orig_key"], "n": n, "issued": a["certified_by_D"] == "True",
                     "w_kind": w["kind"], "w_key": w["key"], "w_d": w["d"], "witness_in_A": in_A, "witness_in_S": a["witness_in_S"] == "True",
                     "A_ideal_distinguishes": a_ideal, "D_assertions": len(D), "A_assertions": len(Apol), "diag_seconds": round(t_diag, 4),
                     "D_suite_id": json.dumps([c["orig_key"], w["kind"], w["key"]]), "A_suite_id": c["orig_key"]})
        c["_D"], c["_A"] = D, Apol
        if not SEMANTIC_ONLY:
            jobs.append((c["mut"], n, D, VAL_MUT)); keys.append((c["case"], "D_mut"))
            jobs.append((c["mut"], n, Apol, VAL_MUT)); keys.append((c["case"], "A_mut"))
    seen = {}
    if not SEMANTIC_ONLY:
        for c, row in zip(Cs, rows):
            for pol in ("D", "A"):
                k = (c["orig_key"], pol, row[f"{pol}_suite_id"])
                if k in seen: continue
                seen[k] = 1; jobs.append((c["orig"], c["n"], c["_" + pol], VAL_ORIG)); keys.append((json.dumps(list(k)), f"{pol}_orig"))
    json.dump({"rows": rows}, open(OUT / "ALLPAIRS_SEMANTIC.json", "w"), indent=0)
    if SEMANTIC_ONLY:
        print("cases", len(rows), "planned executions", 2 * R * len(rows) + R * sum(1 for _ in seen)); return
    order = sorted(range(len(jobs)), key=lambda i: -jobs[i][1])                    # widest first
    t0 = time.time(); res = [None] * len(jobs)
    with ProcessPoolExecutor(WORKERS) as ex:
        for i, r in zip(order, ex.map(run_job, [jobs[i] for i in order])): res[i] = r
    wall = time.time() - t0
    # histogram identity: one histogram per (program, seed) across every execution of that program
    prog_of = lambda k, role: (k if role.endswith("_mut") else json.loads(k)[0]) + ("|mut" if role.endswith("_mut") else "|orig")
    hist, ident_bad = {}, []
    by = {}
    for (k, role), out in zip(keys, res):
        for x in out:
            pk = (prog_of(k, role), x["seed"]); by.setdefault(pk, set()).add(x["hist_id"])
            hist.setdefault(x["hist_id"], x["counts"])
    ident_bad = [list(pk) + [sorted(v)] for pk, v in by.items() if len(v) != 1]
    with gzip.open(OUT / "ALLPAIRS_HISTOGRAMS.jsonl.gz", "wt") as f:
        for hid in sorted(hist): f.write(json.dumps({"hist_id": hid, "counts": hist[hid]}, sort_keys=True) + "\n")
    with open(OUT / "ALLPAIRS_NATIVE_RUNS.csv", "w", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        wr.writerow(["key", "role", "seed", "verdict", "inproc_verdict", "cli_assertions", "inproc_assertions", "rescored_assertions", "values_agree", "hist_id", "cli_seconds", "inproc_seconds", "eval_seconds"])
        for (k, role), out in zip(keys, res):
            for x in out: wr.writerow([k, role, x["seed"], x["cli"], x["inproc"], x["cli_assertions"], x["inproc_assertions"], x["rescored_assertions"], x["values_agree"], x["hist_id"], x["cli_seconds"], x["inproc_seconds"], x["eval_seconds"]])
    json.dump({"settings": {"N": N, "R": R, "theta": THETA, "val_mutant_seeds": VAL_MUT, "val_original_seeds": VAL_ORIG},
               "population": {"cases": len(rows), "corpus": sum(r["arm"] == "corpus" for r in rows), "mqt": sum(r["arm"] == "mqt" for r in rows)},
               "reference_generation_seconds": round(t_ref, 3), "diagnosis_seconds_total": round(sum(r["diag_seconds"] for r in rows), 3),
               "native_wall_seconds": round(wall, 1), "executions": sum(len(o) for o in res), "shots": N * sum(len(o) for o in res),
               "distinct_histograms": len(hist), "histogram_identity_violations": ident_bad,
               "workers": WORKERS, "machine": platform.platform()}, open(OUT / "ALLPAIRS_SUMMARY.json", "w"), indent=1)
    print("cases", len(rows), "executions", sum(len(o) for o in res), "wall", round(wall, 1), "histograms", len(hist), "identity violations", len(ident_bad))

if __name__ == "__main__":
    main()
