"""Remaining record-level checks: width listing, scale growth, output-condition pool, a rerun of the frozen MQT
Bench analysis on a copy of its stage records (the archived tree is never written) and the concentration of the
reported causes over mutation sites."""
import csv, json, os, shutil, statistics, subprocess, sys
sys.dont_write_bytecode = True
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import orig, out_dir, ROOT
import witness_order as wo

OUT = []
def chk(cid, label, value, level): OUT.append({"check_id": cid, "label": label, "recomputed": value, "evidence_level": level})
rd = lambda p: wo.final(p, list(csv.DictReader(open(orig(p)))))

# X01 width set: 162 listed pairs, 44 originals, 143 executable, 143 executed
M = rd("data/scalability/E4_SCALE_MANIFEST.csv")
cells = [json.loads(l) for l in open(orig("data/scalability/B2_SCALE_CELLS_FRESH.jsonl")) if l.strip()]
comp = {r["pair_id"] for r in M if r["qutest_compatible"] == "True"}
chk("X01", "width set: listed / unique / originals / executable / executed = executable",
    f"{len(M)}/{len({r['pair_id'] for r in M})}/{len({r['original_id'] for r in M})}/{len(comp)}/{len({c['pair_id'] for c in cells}) if {c['pair_id'] for c in cells} == comp else 'differs'}",
    "per-case records")
# X02 growth of universe + relation time, n = 8 -> 14 (median per width)
by = defaultdict(list)
for c in cells: by[c["n"]].append(c["timings"]["B_universe"] + c["timings"]["C_relations"])
chk("X02", "universe evaluation time growth from 8 to 14 qubits, ratio of medians",
    f"{round(statistics.median(by[14]) / statistics.median(by[8]))}", "per-case records")
# X03 output-condition counterfactual: pool recounted per case; movers from the archived aggregate
T13 = rd("data/primary/records/T1_3_REFERENCE_599.csv")
pool = [r for r in T13 if r["subject"].startswith(("simon", "bv")) and r["report"] != "NA_KILLED"]
OC = json.load(open(orig("data/primary/records/599_OUTPUT_CONDITION.json")))["at_599"]
chk("X03", "Simon and BV survivors (pool, per case) / contract-equivalent under output conditions (archived aggregate)",
    f"{len(pool)}/{OC['movers']}", "pool per-case; movers archived aggregate (recomputed in analytic tier)")

# X05 transpiler sweep: certified pairs per configuration (per-configuration record)
TS = rd("data/primary/decision/B5_A3_TRANSPILER_SWEEP.csv")
cert = [int(r["certified"]) for r in TS]
chk("X05", "transpiler agreement: min / max certified pairs / pairs / configurations",
    f"{min(cert)}/{max(cert)}/{TS[0]['pairs'] if len({r['pairs'] for r in TS}) == 1 else 'varies'}/{len(TS)}", "per-configuration records")

# X06 width set: share of the median case's total time spent evaluating the universe (universe + relation time, as in
# X02 and the 5.8 ms / 4.15 s medians of S2), at fourteen and at ten qubits
def _share(n):
    c = [x for x in cells if x["n"] == n]
    return (statistics.median(x["timings"]["B_universe"] + x["timings"]["C_relations"] for x in c)
            / statistics.median(x["total_seconds"] for x in c))
chk("X06", "width set: universe share of the median total time at 14 qubits, % / share at 10 qubits below 0.2 %",
    f"{100 * _share(14):.1f}/{100 * _share(10) < 0.2}", "per-case records")

# X07 corpus split verdicts (Section 7.1): from the per-case revised records and the native confirmation (OB13) jobs.
# Candidates are the corpus suite-omission candidates (v2_candidate CL4, OB03 satisfied); the withdrawal reason follows
# the breakdown order of r2v_numbers.py. Margin = d_a - theta of the distinguishing assertion, theta = 0.05.
THETA = 0.05
fin = {r["case"]: r for r in rd("data/certification/outcomes/R2V_FINAL_CORPUS.csv")}
ob13 = {r["case"]: r for r in rd("data/certification/outcomes/R2V_NATIVE.csv") if r["arm"] == "corpus" and r["purpose"] == "OB13"}
def _reason(r):
    if r["v2_report"] == "CL4": return "confirmed"
    if not r.get("c_kind"): return "no control"
    if r.get("final_OB02") == "failed": return "guard failure"
    if r.get("final_OB13") == "failed": return "split verdict"
    return "other"
cands = [r for r in fin.values() if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"]
rows7 = []
for r in cands:
    j = ob13[r["case"]]
    assert abs(float(j["inst_d"]) - float(r["w_d"])) < 1e-12        # one distinguishing assertion per candidate
    rows7.append((r["case"].split("/")[-1], int(j["kills"]), float(j["inst_d"]) - THETA, _reason(r)))   # case, kills of 12, margin, reason
split7 = [x for x in rows7 if 0 < x[1] < 12]
wd7 = [x for x in rows7 if x[3] == "split verdict"]
beyond = [x for x in split7 if abs(x[2]) >= 0.05]
near_full = [x for x in rows7 if x[1] == 12 and abs(x[2]) < 0.05]
chk("X07", "corpus: split witness verdicts / candidates withdrawn for a split verdict / their largest |d_a - theta| /"
    "split witness with |d_a - theta| >= 0.05 (withdrawal reason) / witnesses within 0.05 of theta killing 12 of 12",
    f"{len(split7)}/{len(wd7) if all(0 < x[1] < 12 for x in wd7) else 'not all split'}/{max(abs(x[2]) for x in wd7):.4f}/"
    + ";".join(f"{x[0]}:{abs(x[2]):.4f}:{x[3]}" for x in beyond) + f"/{len(near_full)}", "per-case records")

# X04 MQT Bench: rerun the frozen analysis and reporting join on a copy of the stage records
src = orig("data/prospective/mqt_bench/code/analyze.py").parents[1]
dst = out_dir("mqt_bench_rerun")
for sub in ("code", "records/stage_c", "records/stage_d", "population"):
    if (dst / sub).exists(): shutil.rmtree(dst / sub)
    shutil.copytree(src / sub, dst / sub, ignore=shutil.ignore_patterns("mutants", "__pycache__"))
(dst / "records/analysis").mkdir(parents=True, exist_ok=True)
shutil.copy2(src / "records/analysis/case_table.py", dst / "records/analysis/case_table.py")
py = sys.executable
r1 = subprocess.run([py, "-I", "-B", "code/analyze.py"], cwd=dst, capture_output=True, text=True)
r2 = subprocess.run([py, "-I", "-B", "records/analysis/case_table.py"], cwd=dst, capture_output=True, text=True)
same_a = json.load(open(dst / "records/analysis/ANALYSIS.json")) == json.load(open(src / "records/analysis/ANALYSIS.json")) if r1.returncode == 0 else f"analyze failed: {r1.stderr[-200:]}"
same_c = open(dst / "records/analysis/PASS3C_CASES.csv").read() == open(src / "records/analysis/PASS3C_CASES.csv").read() if r2.returncode == 0 else f"case_table failed: {r2.stderr[-200:]}"
chk("X04", "MQT Bench: frozen analyze.py and case_table.py rerun on stage records reproduce ANALYSIS.json / PASS3C_CASES.csv",
    f"{same_a}/{same_c}", "rerun of frozen analysis code on per-case stage records")

# X08-X09 concentration of the reported causes (Section 7.3), from the per-case inventory table of data/inventory/
CA = list(csv.DictReader(open(ROOT / "data/inventory/out/cases_all.csv", newline="")))
fin_c = {r["case_key"]: r for r in rd("data/certification/outcomes/R2V_FINAL_CORPUS.csv")}
corp = [r for r in CA if r["population"] == "corpus"]
so = [r for r in corp if r["v2_report"] == "CL4"]
same = len(corp) == len(fin_c) and all(fin_c[r["case"]]["v2_report"] == r["v2_report"] for r in corp)
design = lambda r: (r["program"], r["declared_outputs"], r["w_kind"], r["w_key"])
chk("X08", "corpus suite omissions: pairs / distinct suites / sites / families; inventory outcomes equal the final records",
    f"{len(so)}/{len({design(r) for r in so})}/{len({(r['program'], r['anchor']) for r in so})}/{len({r['family'] for r in so})}/{same}",
    "per-case records")
add = [r for r in CA if r["population"] == "20 circuits" and r["subpopulation"] == "additional" and r["v2_report"] == "CL4"]
mq = [r for r in CA if r["population"] == "MQT Bench" and r["v2_report"] == "CL4"]
ex = [r for r in CA if r["population"] == "external" and r["v2_report"] == "CL3"]
chk("X09", "repairs of the five other circuits / their sites; MQT Bench repairs / distinct suites; Q# and QASMBench observation limitations / at the first gate",
    f"{len(add)}/{len({(r['program'], r['anchor']) for r in add})}; {len(mq)}/{len({design(r) for r in mq})}; {len(ex)}/{sum(r['first_gate'] == 'True' for r in ex)}",
    "per-case records")

with open(out_dir() / "extra_checks.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["check_id", "label", "recomputed", "evidence_level"]); w.writeheader(); w.writerows(OUT)
for r in OUT: print(f"{r['check_id']}  {r['recomputed']:<16} {r['label']}")
