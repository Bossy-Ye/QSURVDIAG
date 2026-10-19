"""Run the archived conformance tests of the implementation (Python standard library only).

Usage:  python3 scripts/run_conformance_tests.py [--out DIR]

The three tests use synthetic two-qubit cases and the per-case decision bound; none loads a study mutant or executes a
circuit. Each test and the two modules it imports are copied unchanged from the package into <out>/conformance/ and
run there. The two other archived test files (test_qutest_adapter.py, acceptance_tests.py) drive QUTest itself and are
kept as archived evidence only.
"""
import argparse, csv, hashlib, re, shutil, subprocess, sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/lib"))
from paths import orig
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "output")); a = ap.parse_args()
OUT = Path(a.out).resolve() / "conformance"
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True)

# modules imported by the tests, located by content (identical copies sit in the MQT Bench frozen dependencies)
MODULES = {"qsurvdiag_confirmatory.py": "e3ce722200edde2f13674dd4377db212bba6b1c6eb8bafd49ca4d7d2e88cbb50",
           "decision_bound.py": "f0cf288d6560cc2d80ba937fbc5c1a1d0344dccdf2967b9b2308b9b585150306"}
byhash = {m["sha256"]: ROOT / m["package_path"] for m in csv.DictReader(open(ROOT / "provenance/source_manifest.csv"))}
for name, h in MODULES.items():
    p = byhash[h]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == h
    shutil.copy2(p, OUT / name)
TESTS = ["data/implementation/tests/test_minimal_conformance.py", "data/implementation/tests/test_conformance_789.py", "data/implementation/tests/test_decision_bound.py"]
for t in TESTS:
    shutil.copy2(orig(t), OUT / Path(t).name)

ok = True
for t in (Path(t).name for t in TESTS):
    # -E -s: ignore PYTHON* variables and user site-packages; the test's own directory stays on the import path
    r = subprocess.run([sys.executable, "-B", "-E", "-s", t], cwd=OUT, capture_output=True, text=True)
    (OUT / f"{t[:-3]}.log").write_text(r.stdout + r.stderr)
    last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    m = re.search(r"(\d+)/(\d+)", last); last = f"{m.group(1)}/{m.group(2)} checks passed" if m else last
    print(f"{t:30s} {'PASS' if r.returncode == 0 else 'FAIL'}   {last}")
    ok &= r.returncode == 0
sys.exit(0 if ok else 1)
