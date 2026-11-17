"""Run every record-level verification of the package in one command.

Usage:  python3 scripts/verify.py [--out DIR] [--no-tsr]
Runs, in order: the integrity check, the value checks (reproduce.py), the conformance tests
(run_conformance_tests.py), the experiment checks (reproduce_experiments.py) and the integrity check again.
The integrity check verifies the RFC 3161 receipts when OpenSSL is installed, unless --no-tsr is given.
Outputs go to DIR (default: ./output). The exit status is non-zero if any step fails.
"""

import argparse, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(ROOT / "output"))
ap.add_argument("--no-tsr", action="store_true")
a = ap.parse_args()
OUT = Path(a.out).resolve()
tsr = [] if a.no_tsr or shutil.which("openssl") is None else ["--tsr"]
if not tsr and not a.no_tsr:
    print("OpenSSL not found: the RFC 3161 receipts are not verified")

STEPS = [
    ("integrity", ["verify_integrity.py", *tsr]),
    ("values", ["reproduce.py", "--out", str(OUT)]),
    ("conformance tests", ["run_conformance_tests.py", "--out", str(OUT)]),
    ("experiments", ["reproduce_experiments.py", "--out", str(OUT / "experiments")]),
    ("integrity after the runs", ["verify_integrity.py"]),
]
failed = []
for name, cmd in STEPS:
    print(f"== {name}: python3 scripts/{' '.join(cmd)}", flush=True)
    r = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts" / cmd[0]), *cmd[1:]])
    if r.returncode:
        failed.append(name)
print("\nall steps passed" if not failed else "\nFAILED: " + ", ".join(failed))
sys.exit(1 if failed else 0)
