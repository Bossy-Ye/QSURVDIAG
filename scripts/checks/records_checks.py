"""Decision-diagram equivalence check, developer tests, released defects, Listing 1, QuCheck and environment
freezes (checks N01 to N10 of expected/values.csv); width set, corpus, output-condition pool, transpiler
sweep, MQT Bench rerun and concentration of causes (X01 to X09). The MQT Bench analysis is rerun on a copy of
its stage records."""

import csv, hashlib, json, re, shutil, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import witness_order
from paths import CATALOGUE, ROOT, archived, out_dir

THETA = 0.05


def rows(path):
    with open(archived(path), newline="") as f:
        return witness_order.final(path, list(csv.DictReader(f)))


def load(path):
    with open(archived(path)) as f:
        return json.load(f)


def text(path):
    return archived(path).read_text(encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


equivalence = rows("data/certification/equivalence/QCEC_LEDGER.csv")
equivalence_run = load("data/certification/equivalence/QCEC_REGISTRY.json")
profiles = rows("data/primary/records/T1_4_INTERFACE_599.csv")
reference = rows("data/primary/records/T1_3_REFERENCE_599.csv")
output_condition = load("data/primary/records/599_OUTPUT_CONDITION.json")["at_599"]
sweep = rows("data/primary/decision/B5_A3_TRANSPILER_SWEEP.csv")
occurrences = rows("data/external/developer_tests/occurrence_classification.csv")
defects = rows("data/external/defects/B3_REAL_DEFECTS_FRESH.csv")
defect_manifest = rows("data/external/defects/E5_DEFECT_MANIFEST.csv")
listing = rows("data/certification/outcomes/R2V_WRAPPED_DEMO.csv")
listing_test = text("data/certification/outcomes/R2V_WRAPPED_DEMO_test.qasm")
rules = text("data/prospective/mqt_bench/frozen_deps/r2v_lib.py")
environments = load("data/profiles/E5_ENVIRONMENT_LOCK.json")["reproduction_environments"]
FREEZES = {
    "Q045": "environment/records/pip_freeze_qiskit_0.45.3.txt",
    "Q11": "environment/records/pip_freeze_qiskit_1.1.1.txt",
    "Q25": "environment/records/pip_freeze_qiskit_2.5.0.txt",
}
width_manifest = rows("data/scalability/E4_SCALE_MANIFEST.csv")
with open(archived("data/scalability/B2_SCALE_CELLS_FRESH.jsonl")) as f:
    width_cells = [json.loads(line) for line in f if line.strip()]
final_corpus = rows("data/certification/outcomes/R2V_FINAL_CORPUS.csv")
confirmations = rows("data/certification/outcomes/R2V_NATIVE.csv")
MQT = archived("data/prospective/mqt_bench/code/analyze.py").parents[1]
with open(ROOT / "data/inventory/out/cases_all.csv", newline="") as f:
    inventory = list(csv.DictReader(f))

verdict = Counter(r["qcec_verdict"] for r in equivalence)
reported = {r["mutant_id"] for r in profiles if r["report"] not in ("NA_KILLED", "Unresolved")}
checked = [r["mutant_id"] for r in equivalence]
hashed = all(
    re.fullmatch(r"[0-9a-f]{16}", r[k] or "")
    for r in equivalence
    for k in ("origin_qasm_sha256", "mutant_qasm_sha256")
)
occurrence = Counter(r["occurrence_class"] for r in occurrences)
pins = {(r["repository"], r["commit"]) for r in occurrences}
defect_ids = {r["defect_id"].replace("qiskit_", "") for r in defect_manifest}
run = {(r["test"].split(" ")[0], r["program"]): r for r in listing}
seeds = (
    "42-53"
    if re.search(r"MUT_SEEDS\s*=\s*\[42 \+ r for r in range\(R\)\]", rules)
    and re.search(r"N_SHOTS,\s*R,\s*GUARD_REPS\s*=\s*2000,\s*12,", rules)
    else "differs"
)
ol = [r for r in profiles if r["report"] == "CL3"]
executable = {r["pair_id"] for r in width_manifest if r["qutest_compatible"] == "True"}
executed = {c["pair_id"] for c in width_cells}
universe_seconds = defaultdict(list)
total_seconds = defaultdict(list)
for c in width_cells:
    universe_seconds[c["n"]].append(c["timings"]["B_universe"] + c["timings"]["C_relations"])
    total_seconds[c["n"]].append(c["total_seconds"])
universe_share = lambda n: median(universe_seconds[n]) / median(total_seconds[n])
pool = [r for r in reference if r["subject"].startswith(("simon", "bv")) and r["report"] != "NA_KILLED"]
agreeing = [int(r["certified"]) for r in sweep]


def withdrawal(r):
    if r["v2_report"] == "CL4":
        return "confirmed"
    if not r.get("c_kind"):
        return "no control"
    if r.get("final_OB02") == "failed":
        return "guard failure"
    if r.get("final_OB13") == "failed":
        return "split verdict"
    return "other"


confirmation = {r["case"]: r for r in confirmations if r["arm"] == "corpus" and r["purpose"] == "OB13"}
witnesses = []
for r in final_corpus:
    if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied":
        job = confirmation[r["case"]]
        if abs(float(job["inst_d"]) - float(r["w_d"])) >= 1e-12:
            sys.exit(f"{r['case']}: the confirmed assertion is not the witness of the outcome record")
        margin = abs(float(job["inst_d"]) - THETA)
        witnesses.append((r["case"].split("/")[-1], int(job["kills"]), margin, withdrawal(r)))
split = [w for w in witnesses if 0 < w[1] < 12]
split_withdrawn = [w for w in witnesses if w[3] == "split verdict"]

rerun = out_dir("mqt_bench_rerun")
for sub in ("code", "records/stage_c", "records/stage_d", "population"):
    if (rerun / sub).exists():
        shutil.rmtree(rerun / sub)
    shutil.copytree(MQT / sub, rerun / sub, ignore=shutil.ignore_patterns("mutants", "__pycache__"))
(rerun / "records/analysis").mkdir(parents=True, exist_ok=True)
shutil.copy2(MQT / "records/analysis/case_table.py", rerun / "records/analysis/case_table.py")


def reproduces(script, output, same):
    r = subprocess.run([sys.executable, "-I", "-B", script], cwd=rerun, capture_output=True, text=True)
    if r.returncode:
        return f"{Path(script).stem} failed: {r.stderr[-200:]}"
    with open(rerun / output) as a, open(MQT / output) as b:
        return same(a, b)


corpus_case = {r["case_key"]: r for r in final_corpus}
corpus = [r for r in inventory if r["population"] == "corpus"]
where = lambda population, report: [
    r for r in inventory if r["population"] == population and r["v2_report"] == report
]
suite = lambda r: (r["program"], r["declared_outputs"], r["w_kind"], r["w_key"])
site = lambda r: (r["program"], r["anchor"])
so_corpus, so_mqt, ol_external = where("corpus", "CL4"), where("MQT Bench", "CL4"), where("external", "CL3")
so_other = [r for r in where("20 circuits", "CL4") if r["subpopulation"] == "additional"]

VALUES = {
    "N01": (
        f"{len(equivalence)}/{len(equivalence) - verdict['no_information']}/{verdict['no_information']}/"
        f"{verdict['equivalent'] + verdict['equivalent_up_to_global_phase']}"
    ),
    "N02": f"{len(set(checked))}/{set(checked) == reported}/{hashed}",
    "N03": (
        f"{equivalence_run['versions'].get('mqt-qcec')}/{equivalence_run['versions'].get('mqt-core')}/"
        f"{equivalence_run.get('pinned')}"
    ),
    "N04": (
        f"{len(occurrences)}/{occurrence['structure, resources or setup']}/"
        f"{occurrence['full state vector'] + occurrence['full unitary']}/"
        f"{occurrence['computational-basis quantity']}"
    ),
    "N05": (
        f"{len({repository for repository, _ in pins})}/{len(pins)}/"
        f"{all(r['file'] and r['line'].isdigit() for r in occurrences)}"
    ),
    "N06": (
        f"{len(defect_manifest)}/{sum(r['defect_id'] in defect_ids for r in defects)}/"
        f"{all(r['repository'] and r['issue_or_thread'] and r['buggy_sha256'] for r in defect_manifest)}"
    ),
    "N07": (
        f"{run[('wrapped', 'original')]['kills']}/{run[('wrapped', 'mutant')]['kills']}/"
        f"{run[('wrapped', 'mutant')]['reps']}/{run[('S_MIN', 'original')]['kills']}/"
        f"{run[('S_MIN', 'mutant')]['kills']}"
    ),
    "N08": (
        f"{seeds}/"
        f"{'//% seed 42' in listing_test and 'h q[2];' in listing_test and 'rz(1.570796326795) q[2];' in listing_test}"
    ),
    "N09": f"{len(ol)}/{sum(r['R_O_QuCheck'] == 'True' for r in ol)}",
    "N10": (
        f"{sum(sha256(ROOT / p) == environments[k]['pip_freeze_sha256'] for k, p in FREEZES.items())}"
        f"/{len(FREEZES)}"
    ),
    "X01": (
        f"{len(width_manifest)}/{len({r['pair_id'] for r in width_manifest})}/"
        f"{len({r['original_id'] for r in width_manifest})}/{len(executable)}/"
        f"{len(executed) if executed == executable else 'differs'}"
    ),
    "X02": f"{round(median(universe_seconds[14]) / median(universe_seconds[8]))}",
    "X03": f"{len(pool)}/{output_condition['movers']}",
    "X05": (
        f"{min(agreeing)}/{max(agreeing)}/"
        f"{sweep[0]['pairs'] if len({r['pairs'] for r in sweep}) == 1 else 'varies'}/{len(sweep)}"
    ),
    "X06": f"{100 * universe_share(14):.1f}/{100 * universe_share(10) < 0.2}",
    "X07": (
        f"{len(split)}/"
        f"{len(split_withdrawn) if all(0 < w[1] < 12 for w in split_withdrawn) else 'not all split'}/"
        f"{max(w[2] for w in split_withdrawn):.4f}/"
        + ";".join(f"{w[0]}:{w[2]:.4f}:{w[3]}" for w in split if w[2] >= 0.05)
        + f"/{sum(1 for w in witnesses if w[1] == 12 and w[2] < 0.05)}"
    ),
    "X04": (
        f"{reproduces('code/analyze.py', 'records/analysis/ANALYSIS.json', lambda a, b: json.load(a) == json.load(b))}/"
        f"{reproduces('records/analysis/case_table.py', 'records/analysis/PASS3C_CASES.csv', lambda a, b: a.read() == b.read())}"
    ),
    "X08": (
        f"{len(so_corpus)}/{len(set(map(suite, so_corpus)))}/{len(set(map(site, so_corpus)))}/"
        f"{len({r['family'] for r in so_corpus})}/"
        f"{len(corpus) == len(corpus_case) and all(corpus_case[r['case']]['v2_report'] == r['v2_report'] for r in corpus)}"
    ),
    "X09": (
        f"{len(so_other)}/{len(set(map(site, so_other)))}; {len(so_mqt)}/{len(set(map(suite, so_mqt)))}; "
        f"{len(ol_external)}/{sum(r['first_gate'] == 'True' for r in ol_external)}"
    ),
}

with open(out_dir() / "records_checks.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["check_id", "label", "recomputed", "evidence_level"])
    for cid, value in VALUES.items():
        w.writerow([cid, CATALOGUE[cid]["label"], value, CATALOGUE[cid]["evidence_level"]])
        print(f"{cid}  {value:<22} {CATALOGUE[cid]['label']}")
