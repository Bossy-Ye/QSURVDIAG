"""Analytic tier: recompute the values that need transpilation or a statevector (checks A01 to A08 of
expected/values.csv). No circuit is sampled or run on a backend. Needs the environment of
environment/setup.sh.

A01, A02  gate-list and gate-set comparisons per case; one trial of QUTest's own gate-set check
A03       output-condition counterfactual from final states
A04       the two QUTest documentation checks that the record tier leaves out
A05-A08   archived producers r2v_stats.py, r2v_bound.py, r2v_table_x.py and r2v_numbers.py, each rerun and
          compared with its archived output
With results_verification.csv of the record tier in the same --out, also writes
results_verification_merged.csv."""

import argparse, csv, json, os, shutil, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from paths import CATALOGUE, ROOT, archived, output

FROZEN = "data/prospective/mqt_bench/frozen_deps/"
VALIDATION = "research_repair/phase5_validation/"
OUTCOMES = "data/certification/outcomes/"
STRUCTURAL = "data/structural/records/"
# The archived study code reads its inputs under these paths, relative to $QSD_ROOT.
STUDY_TREE = {
    "final_empirical_study/PROGRAM_MANIFEST.csv": FROZEN + "PROGRAM_MANIFEST.csv",
    "final_empirical_study/MUTANT_POPULATION.csv": FROZEN + "MUTANT_POPULATION.csv",
    VALIDATION + "s1_materialization/S1_SUBJECTS.json": FROZEN + "S1_SUBJECTS.json",
    VALIDATION + "s2_cohort/S2_GENERATED_MUTANTS.csv": FROZEN + "S2_GENERATED_MUTANTS.csv",
    "cross_tool_stage/qutest/qutest_adapter.py": FROZEN + "qutest_adapter.py",
    "confirmatory/e1_lib.py": FROZEN + "e1_lib.py",
    "confirmatory/e1_relations.py": FROZEN + "e1_relations.py",
    "confirmatory/qsurvdiag_confirmatory.py": FROZEN + "qsurvdiag_confirmatory.py",
    "confirmatory/SSPEC_PROVENANCE.json": FROZEN + "SSPEC_PROVENANCE.json",
    "confirmatory/e1_seed_schedule.py": "data/primary/implementation/e1_seed_schedule.py",
}
PRODUCERS = {
    "A05": ("r2v_stats.py", ["R2V_STATISTICS.json"]),
    "A06": ("r2v_bound.py", ["R2V_BOUND.json"]),
    "A07": ("r2v_table_x.py", ["R2V_TABLE_X.json", "R2V_TABLE_X_DECISIONS.csv"]),
    "A08": ("r2v_numbers.py", ["R2V_NUMBERS.json"]),
}
COMMAND = "python3 scripts/reproduce_analytic.py"

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--out", default=ROOT / "output", help="output directory (default: output/ in the package)")
OUT = output(ap.parse_args().out)
ANALYTIC = OUT / "analytic"
ANALYTIC.mkdir(exist_ok=True)
# Without QISKIT_SETTINGS, Qiskit reads ~/.qiskit/settings.conf. The records were produced under this file.
env = {**os.environ, "QSD_OUT": str(OUT), "QISKIT_SETTINGS": str(ROOT / "environment/qiskit_settings.conf")}
got = {}


def run(script, log=None, **options):
    r = subprocess.run([sys.executable, "-I", "-B", str(script)], capture_output=True, text=True, **options)
    if log:
        (ANALYTIC / log).write_text(r.stdout + r.stderr)
    return r.returncode == 0


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def category(r):
    if r["separated_trials"] == r["trials"]:
        return "all"
    return "none" if r["separated_trials"] == "0" else "some"


if run(ROOT / "scripts/analytic/structural_definitions.py", "structural_definitions.log", env=env):
    by_id = lambda rs: {r["mutant_id"]: r for r in rs}
    recomputed = by_id(rows(ANALYTIC / "STRUCTURAL_DEFINITIONS.csv"))
    recorded = by_id(rows(archived(STRUCTURAL + "STRUCTURAL_DEFINITIONS.csv")))
    trials = by_id(rows(archived(STRUCTURAL + "QUTEST_GATESET_VARIABILITY.csv")))
    same = recomputed.keys() == recorded.keys() and all(
        recomputed[k][c] == recorded[k][c]
        for k in recomputed
        for c in ("HIST_gatelist", "HIST_depth", "P5_gateset", "P5_depth")
    )
    flagged = lambda population, column: sum(
        r[column] == "True" for r in recomputed.values() if r["population"] == population
    )
    got["A01"] = (
        f"{flagged('construction', 'HIST_gatelist')}/{flagged('construction', 'P5_gateset')}/"
        f"{flagged('prospective', 'HIST_gatelist')}/{flagged('prospective', 'P5_gateset')}/{same}"
    )
    # A program is unstable when the transpiled gate set of its original varies or some trials flag a case.
    gate_sets = defaultdict(set)
    for r in recorded.values():
        gate_sets[r["mutant_id"].split("#")[0]].add(r["QT_allowed"])
    unstable = {p for p, sets in gate_sets.items() if len(sets) > 1} | {
        r["program"] for r in trials.values() if category(r) == "some"
    }
    consistent = all(
        category(trials[k]) == "some"
        or (recomputed[k]["QT_gateset_subset"] == "True") == (category(trials[k]) == "all")
        for k in recomputed
        if trials[k]["program"] not in unstable
    )
    got["A02"] = f"{flagged('prospective', 'QT_gateset_subset')}/{consistent}"
else:
    got["A01"] = got["A02"] = "FAILED: see analytic/structural_definitions.log"

study = ANALYTIC / "qsd_root"
if study.exists():
    shutil.rmtree(study)
for target, source in STUDY_TREE.items():
    (study / target).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archived(source), study / target)
if run(
    ROOT / "scripts/analytic/output_condition.py",
    "output_condition.log",
    cwd=study / "confirmatory",
    env={**env, "QSD_ROOT": str(study)},
):
    with open(ANALYTIC / "outcond_599.json") as f:
        movers = json.load(f)
    got["A03"] = f"{movers['pool']}/{movers['movers']}/{movers['out']}"
else:
    got["A03"] = "FAILED: see analytic/output_condition.log"

if run(ROOT / "scripts/checks/article_checks.py", env={**env, "QSD_OUT": str(ANALYTIC)}):
    documentation = {r["check_id"]: r["recomputed"] for r in rows(ANALYTIC / "article_checks.csv")}
    got["A04"] = f"{documentation['M309']}/{documentation['M310']}"
else:
    got["A04"] = "FAILED"

# The archived producers run in the folder layout of the study; input_tree.csv rebuilds it from package files.
tree = ANALYTIC / "r2v_root"
if tree.exists():
    shutil.rmtree(tree)
by_hash = {}
for r in rows(ROOT / "provenance/source_manifest.csv"):
    by_hash.setdefault(r["sha256"], ROOT / r["package_path"])
for r in rows(ROOT / "scripts/analytic/input_tree.csv"):
    (tree / r["path"]).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(by_hash[r["sha256"]], tree / r["path"])
workdir = tree / "artifact/outcomes"
shutil.copy2(ROOT / "scripts/analytic/r2v_lib.py", workdir / "r2v_lib.py")
producer_env = {**env, "R2V_PA": str(tree / "artifact") + "/", "QSD_ROOT": str(tree / "study")}


def compare(name):
    """PASS for equal bytes, and for R2V_BOUND.json equal outside witness_surface_v2, whose counts depend on
    the order of ties, and R2V_TABLE_X_DECISIONS.csv with margins within 1e-12."""
    new, old = workdir / name, archived(OUTCOMES + name)
    if not new.is_file():
        return "FAIL"
    if new.read_bytes() == old.read_bytes():
        return "PASS"
    if name == "R2V_BOUND.json":
        a, b = json.load(open(new)), json.load(open(old))
        a.pop("witness_surface_v2")
        b.pop("witness_surface_v2")
        return "PASS" if a == b else "FAIL"
    if name == "R2V_TABLE_X_DECISIONS.csv":
        a, b = list(csv.reader(open(new))), list(csv.reader(open(old)))
        return (
            "PASS"
            if len(a) == len(b)
            and a[0] == b[0]
            and all(
                x == y or (h.startswith("margin_") and abs(float(x) - float(y)) <= 1e-12)
                for p, q in zip(a[1:], b[1:])
                for h, x, y in zip(a[0], p, q)
            )
            else "FAIL"
        )
    return "FAIL"


for cid, (script, outputs) in PRODUCERS.items():
    ran = run(script, f"{script[:-3]}.log", cwd=workdir, env=producer_env)
    got[cid] = "/".join(compare(name) if ran else "FAIL" for name in outputs)

expected = {cid: c for cid, c in CATALOGUE.items() if c["module"] == "reproduce_analytic"}
table = []
for cid, c in expected.items():
    value = got.get(cid, "NOT RUN")
    table.append(
        {
            "check_id": cid,
            "evidence_level": c["evidence_level"],
            "command": COMMAND,
            "expected": c["expected"],
            "reproduced": value,
            "status": "MATCH" if value == c["expected"] else "MISMATCH",
        }
    )
    print(f"{cid}  expected {c['expected']:<16} reproduced {value:<16} {table[-1]['status']}")


def write(name, rs):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rs[0]))
        w.writeheader()
        w.writerows(rs)


write("results_verification_analytic.csv", table)

# A record-tier row that an analytic check covers becomes MATCH only if that check matched.
if (OUT / "results_verification.csv").is_file():
    status = {r["check_id"]: r["status"] for r in table}
    covered_by = {r["check_id"]: r["covered_by"] for r in rows(ROOT / "expected/analytic_coverage.csv")}
    a04 = got.get("A04", "").split("/")
    documentation = {"M309": a04[0], "M310": a04[-1]}
    merged = rows(OUT / "results_verification.csv")
    for r in merged:
        check = covered_by.get(r["check_id"])
        if check is None or status[check] != "MATCH":
            continue
        value = documentation.get(r["check_id"], r["reproduced"])
        r["command"] = COMMAND
        r["reproduced"] = f"{value} ({check})"
        r["status"] = f"MATCH (analytic tier {check})" if value == r["expected"] else "MISMATCH"
    merged += [
        {
            "check_id": r["check_id"],
            "module": "reproduce_analytic",
            "label": "",
            "printed_in_article": expected[r["check_id"]]["printed_in_article"],
            "evidence_level": r["evidence_level"],
            "inputs": "",
            "command": r["command"],
            "expected": r["expected"],
            "reproduced": r["reproduced"],
            "status": r["status"],
        }
        for r in table
    ]
    write("results_verification_merged.csv", merged)
    kind = lambda status: "MATCH" if status.startswith("MATCH") else status
    tally = lambda rs: "  ".join(f"{k}: {n}" for k, n in sorted(Counter(kind(r["status"]) for r in rs).items()))
    print(f"\nmerged with the record tier: {len(merged)} checks  {tally(merged)}")
    print("values printed in the article: " + tally([r for r in merged if r["printed_in_article"] == "yes"]))
sys.exit(0 if all(r["status"] == "MATCH" for r in table) else 1)
