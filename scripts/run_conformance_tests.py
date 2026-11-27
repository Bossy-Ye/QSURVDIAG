"""Run the three archived conformance tests of the implementation (standard library only).

Each test and the two modules it imports are copied unchanged to <out>/conformance/ and run there. The tests
use synthetic two-qubit cases; none loads a study mutant or executes a circuit."""

import argparse, csv, hashlib, re, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from paths import ROOT, archived, output

TESTS = (
    "data/implementation/tests/test_minimal_conformance.py",
    "data/implementation/tests/test_conformance_789.py",
    "data/implementation/tests/test_decision_bound.py",
)
# The imported modules are located by content: identical copies are archived with the MQT Bench dependencies.
MODULES = {
    "qsurvdiag_confirmatory.py": "e3ce722200edde2f13674dd4377db212bba6b1c6eb8bafd49ca4d7d2e88cbb50",
    "decision_bound.py": "f0cf288d6560cc2d80ba937fbc5c1a1d0344dccdf2967b9b2308b9b585150306",
}

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--out", default=ROOT / "output", help="output directory (default: output/ in the package)")
OUT = output(ap.parse_args().out) / "conformance"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

with open(ROOT / "provenance/source_manifest.csv") as f:
    by_hash = {r["sha256"]: ROOT / r["package_path"] for r in csv.DictReader(f)}
for name, digest in MODULES.items():
    if hashlib.sha256(by_hash[digest].read_bytes()).hexdigest() != digest:
        sys.exit(f"{by_hash[digest]} differs from its hash in provenance/source_manifest.csv")
    shutil.copy2(by_hash[digest], OUT / name)
for test in TESTS:
    shutil.copy2(archived(test), OUT / Path(test).name)
failed = False
for name in (Path(test).name for test in TESTS):
    # -E -s leave out PYTHON* variables and the user site-packages; the test's directory stays importable.
    r = subprocess.run([sys.executable, "-B", "-E", "-s", name], cwd=OUT, capture_output=True, text=True)
    (OUT / f"{Path(name).stem}.log").write_text(r.stdout + r.stderr)
    last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    m = re.search(r"(\d+)/(\d+)", last)
    print(f"{name:30s} {'FAIL' if r.returncode else 'PASS'}   {f'{m[1]}/{m[2]} checks passed' if m else last}")
    failed |= bool(r.returncode)
sys.exit(failed)
