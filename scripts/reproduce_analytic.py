"""Optional analytic tier: recompute the transpilation- and statevector-based values (no circuit is sampled or run
on a backend). Requires environment/requirements-analytic.txt and QUTest 0.1.0 (see README).

Usage:  python3 scripts/reproduce_analytic.py [--out DIR]
A01  historical gate-list and registered fixed-basis comparisons, recomputed per case and compared with the archive
A02  one fresh trial of QUTest's own gate-set check, compared with the archived trial categories of the programs
     whose original keeps its transpiled gate set (the flags of the other six are not reliable; article Section 5.1)
A03  output-condition counterfactual (8 of 47) recomputed from final states
A04  QUTest 0.1.0 documentation checks (two manuscript checks skipped by the record-level tier)
A05-A08  reruns of the archived producers r2v_stats.py, r2v_bound.py, r2v_table_x.py and r2v_numbers.py on package
     inputs; each regenerated file is compared with the archived one (PASS or FAIL): byte for byte, except
     R2V_BOUND.json without its unprinted witness_surface_v2 counts, which depend on the order of ties
     (data/checks/tie_check.py), and the margins of R2V_TABLE_X_DECISIONS.csv, compared to 1e-12
If the record tier has written results_verification.csv to the same --out directory, both tiers are merged into
results_verification_merged.csv, using expected/analytic_coverage.csv.
"""
import argparse, csv, json, os, shutil, subprocess, sys
sys.dont_write_bytecode = True
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/lib"))
from paths import orig
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "output")); a = ap.parse_args()
OUT = Path(a.out).resolve(); (OUT / "analytic").mkdir(parents=True, exist_ok=True)
# Qiskit reads ~/.qiskit/settings.conf unless QISKIT_SETTINGS names another file; use the configuration in effect when the archive was produced
env = {**os.environ, "QSD_OUT": str(OUT), "QISKIT_SETTINGS": str(ROOT / "environment/qiskit_settings.conf")}
res = {}

# A01, A02: adapted structural script (writes analytic/STRUCTURAL_DEFINITIONS.csv)
r = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/analytic/structural_definitions.py")], env=env, capture_output=True, text=True)
(OUT / "analytic/structural_definitions.log").write_text(r.stdout + r.stderr)
if r.returncode == 0:
    new = {x["mutant_id"]: x for x in csv.DictReader(open(OUT / "analytic/STRUCTURAL_DEFINITIONS.csv"))}
    old = {x["mutant_id"]: x for x in csv.DictReader(open(orig("data/structural/records/STRUCTURAL_DEFINITIONS.csv")))}
    det = ("HIST_gatelist", "HIST_depth", "P5_gateset", "P5_depth")
    same = new.keys() == old.keys() and all(new[k][c] == old[k][c] for k in new for c in det)
    c = lambda pop, col: sum(x[col] == "True" for x in new.values() if x["population"] == pop)
    res["A01"] = f"{c('construction', 'HIST_gatelist')}/{c('construction', 'P5_gateset')}/{c('prospective', 'HIST_gatelist')}/{c('prospective', 'P5_gateset')}/{same}"
    V = {x["mutant_id"]: x for x in csv.DictReader(open(orig("data/structural/records/QUTEST_GATESET_VARIABILITY.csv")))}
    cat = lambda x: "a" if x["separated_trials"] == x["trials"] else ("n" if x["separated_trials"] == "0" else "s")
    gs = defaultdict(set)                     # programs whose original's transpiled gate set varies, or with a case flagged in some trials
    for x in old.values(): gs[x["mutant_id"].split("#")[0]].add(x["QT_allowed"])
    unstable = {p for p, v in gs.items() if len(v) > 1} | {x["program"] for x in V.values() if cat(x) == "s"}
    consistent = all(cat(V[k]) == "s" or (new[k]["QT_gateset_subset"] == "True") == (cat(V[k]) == "a")
                     for k in new if V[k]["program"] not in unstable)
    res["A02"] = f"{c('prospective', 'QT_gateset_subset')}/{consistent}"
else:
    res["A01"] = res["A02"] = "FAILED: see analytic/structural_definitions.log"

# A03: output-condition counterfactual on a temporary root assembled from package files
qr = OUT / "analytic/qsd_root"
if qr.exists(): shutil.rmtree(qr)
F = "data/prospective/mqt_bench/frozen_deps/"
place = {"final_empirical_study/PROGRAM_MANIFEST.csv": "data/prospective/mqt_bench/frozen_deps/PROGRAM_MANIFEST.csv",
         "final_empirical_study/MUTANT_POPULATION.csv": "data/prospective/mqt_bench/frozen_deps/MUTANT_POPULATION.csv",
         "research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json": "data/prospective/mqt_bench/frozen_deps/S1_SUBJECTS.json",
         "research_repair/phase5_validation/s2_cohort/S2_GENERATED_MUTANTS.csv": "data/prospective/mqt_bench/frozen_deps/S2_GENERATED_MUTANTS.csv",
         "cross_tool_stage/qutest/qutest_adapter.py": F + "qutest_adapter.py",
         "confirmatory/e1_lib.py": F + "e1_lib.py", "confirmatory/e1_relations.py": F + "e1_relations.py",
         "confirmatory/qsurvdiag_confirmatory.py": F + "qsurvdiag_confirmatory.py", "confirmatory/SSPEC_PROVENANCE.json": F + "SSPEC_PROVENANCE.json",
         "confirmatory/e1_seed_schedule.py": "data/primary/implementation/e1_seed_schedule.py"}
for dst, src in place.items():
    (qr / dst).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(orig(src), qr / dst)
r = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/analytic/output_condition.py")], cwd=qr / "confirmatory",
                   env={**env, "QSD_ROOT": str(qr), "POP": "599"}, capture_output=True, text=True)
(OUT / "analytic/output_condition.log").write_text(r.stdout + r.stderr)
if r.returncode == 0:
    j = json.load(open(OUT / "analytic/outcond_599.json")); res["A03"] = f"{j['pool']}/{j['movers']}/{j['out']}"
else:
    res["A03"] = "FAILED: see analytic/output_condition.log"

# A04: QUTest documentation checks via the record-level engine, now with QUTest installed
r = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/checks/manuscript_checks.py")], env={**env, "QSD_OUT": str(OUT / "analytic")},
                   capture_output=True, text=True)
if r.returncode == 0:
    rows = {x["check_id"]: x["recomputed"] for x in csv.DictReader(open(OUT / "analytic/manuscript_checks.csv"))}
    res["A04"] = f"{rows['M309']}/{rows['M310']}"
else:
    res["A04"] = "FAILED"

# A05-A08: archived producers rerun on an input tree assembled from package files (looked up by SHA-256)
rt = OUT / "analytic/r2v_root"
if rt.exists(): shutil.rmtree(rt)
byhash = {}
for m in csv.DictReader(open(ROOT / "provenance/source_manifest.csv")): byhash.setdefault(m["sha256"], ROOT / m["package_path"])
for x in csv.DictReader(open(ROOT / "scripts/analytic/r2v_inputs.csv")):
    d = rt / x["path"]; d.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(byhash[x["sha256"]], d)
H = rt / "artifact/outcomes"
shutil.copy2(ROOT / "scripts/analytic/r2v_lib.py", H / "r2v_lib.py")
renv = {**env, "R2V_PA": str(rt / "artifact") + "/", "QSD_ROOT": str(rt / "study")}
def compare(o):
    new, old = H / o, orig(f"data/certification/outcomes/{o}")
    if not new.is_file(): return "FAIL"
    if new.read_bytes() == old.read_bytes(): return "PASS"
    if o == "R2V_BOUND.json":
        a, b = json.load(open(new)), json.load(open(old)); a.pop("witness_surface_v2"); b.pop("witness_surface_v2")
        return "PASS" if a == b else "FAIL"
    if o == "R2V_TABLE_X_DECISIONS.csv":
        a, b = list(csv.reader(open(new))), list(csv.reader(open(old)))
        return "PASS" if len(a) == len(b) and a[0] == b[0] and all(x == y or (h.startswith("margin_") and abs(float(x) - float(y)) <= 1e-12)
                                                                   for p, q in zip(a[1:], b[1:]) for h, x, y in zip(a[0], p, q)) else "FAIL"
    return "FAIL"
for cid, script, outputs in (("A05", "r2v_stats.py", ["R2V_STATISTICS.json"]), ("A06", "r2v_bound.py", ["R2V_BOUND.json"]),
                             ("A07", "r2v_table_x.py", ["R2V_TABLE_X.json", "R2V_TABLE_X_DECISIONS.csv"]),
                             ("A08", "r2v_numbers.py", ["R2V_NUMBERS.json"])):
    r = subprocess.run([sys.executable, "-I", "-B", script], cwd=H, env=renv, capture_output=True, text=True)
    (OUT / f"analytic/{script[:-3]}.log").write_text(r.stdout + r.stderr)
    res[cid] = "/".join(compare(o) if r.returncode == 0 else "FAIL" for o in outputs)

exp = {e["check_id"]: e for e in csv.DictReader(open(ROOT / "expected/expected_results.csv")) if e["engine"] == "reproduce_analytic"}
out = []
for cid, e in exp.items():
    g = res.get(cid, "NOT RUN")
    out.append({"check_id": cid, "evidence_level": e["evidence_level"], "command": "python3 scripts/reproduce_analytic.py",
                "expected": e["expected"], "reproduced": g, "status": "MATCH" if g == e["expected"] else "MISMATCH"})
    print(f"{cid}  expected {e['expected']:<16} reproduced {g:<16} {out[-1]['status']}")
with open(OUT / "results_verification_analytic.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

# merge with the record tier: a record-tier row becomes MATCH only if the analytic check covering it matched
if (OUT / "results_verification.csv").is_file():
    st = {x["check_id"]: x for x in out}
    cov = {c["check_id"]: c["covered_by"] for c in csv.DictReader(open(ROOT / "expected/analytic_coverage.csv"))}
    a04 = res.get("A04", "").split("/")
    rows = list(csv.DictReader(open(OUT / "results_verification.csv")))
    for r in rows:
        k = cov.get(r["check_id"])
        if k is None or st[k]["status"] != "MATCH": continue
        v = {"M309": a04[0], "M310": a04[-1]}.get(r["check_id"], r["reproduced"])
        r["command"] = "python3 scripts/reproduce_analytic.py"; r["reproduced"] = f"{v} ({k})"
        r["status"] = f"MATCH (analytic tier {k})" if v == r["expected"] else "MISMATCH"
    for x in out:
        rows.append({"check_id": x["check_id"], "engine": "reproduce_analytic", "label": "", "printed_in_manuscript": exp[x["check_id"]]["printed_in_manuscript"],
                     "evidence_level": x["evidence_level"], "inputs": "", "command": x["command"], "expected": x["expected"],
                     "reproduced": x["reproduced"], "status": x["status"]})
    with open(OUT / "results_verification_merged.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    k = lambda s: "MATCH" if s.startswith("MATCH") else s
    print(f"\nmerged with the record tier: {len(rows)} checks  " + "  ".join(f"{a}: {b}" for a, b in sorted(Counter(k(r['status']) for r in rows).items())))
    print("values printed in the article: " + "  ".join(f"{a}: {b}" for a, b in sorted(Counter(k(r['status']) for r in rows if r['printed_in_manuscript'] == 'yes').items())))
sys.exit(0 if all(x["status"] == "MATCH" for x in out) else 1)
