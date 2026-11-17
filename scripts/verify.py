"""Run every record-level verification of the package in one command.

Usage:  python3 scripts/verify.py [--out DIR] [--no-tsr]
Runs, in order: the integrity check, the value checks (reproduce.py), the conformance tests
(run_conformance_tests.py), the experiment checks (reproduce_experiments.py) and the integrity check again.
The integrity check verifies the RFC 3161 receipts when OpenSSL is installed, unless --no-tsr is given.
Outputs go to DIR (default: ./output). Each step's output is printed; a summary of the counts follows and is
compared with expected/verify_summary.txt (without the Freeze clause when the receipts are not verified).
The exit status is non-zero if any step fails or the summary differs.
"""

import argparse, re, shutil, subprocess, sys
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
failed, text = [], {}
for name, cmd in STEPS:
    print(f"== {name}: python3 scripts/{' '.join(cmd)}", flush=True)
    r = subprocess.run(
        [sys.executable, "-I", "-B", str(ROOT / "scripts" / cmd[0]), *cmd[1:]],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(r.stdout, end="", flush=True)
    text.setdefault(name, r.stdout)
    if r.returncode:
        failed.append(name)

ORDER = ("MATCH", "PARTIAL", "ANALYTIC TIER")


def counts(out, head):
    """'<head>: N  STATUS: n  ...' -> 'N checks: MATCH n, PARTIAL n, ANALYTIC TIER n'."""
    m = re.search(rf"^{head}: (\d+)  (.*)$", out, re.M)
    if not m:
        return "not available"
    c = dict(x.rsplit(": ", 1) for x in m.group(2).split("  ") if x)
    c = {("ANALYTIC TIER" if "analytic tier" in k else k): v for k, v in c.items()}
    keys = [k for k in ORDER if k in c] + sorted(k for k in c if k not in ORDER)
    return f"{m.group(1)} checks: " + ", ".join(f"{k} {c[k]}" for k in keys)


t = text.get("integrity", "")
m = [
    re.search(p, t, re.M)
    for p in (
        r"^checksums: (\d+) files listed.*?, (\d+) problems",
        r"^archived files: (\d+) identical.*?, (\d+) redacted",
    )
]
# Freezes A to D: four receipts verify, and every manifest entry matches its file or a redaction record
mf = re.findall(
    r"Freeze ([ABCD]) manifest: (\d+) entr\w+, (\d+) matching(?:, (\d+) redacted.*?, 0 other)?",
    t,
)
freeze = all(f"RFC 3161 Freeze {k}: Verification: OK" in t for k in "ABCD") and sorted(
    k for k, n, a, r in mf if int(n) == int(a) + int(r or 0)
) == list("ABCD")
integrity = (
    f"{m[0].group(1)} files, {m[0].group(2)} problems; "
    + f"{m[1].group(1)} archived files identical, {m[1].group(2)} redacted"
    + ("; Freezes A to D verified" if freeze else "; Freezes A to D not verified")
    if all(m)
    else "not available"
)
conf = re.findall(r"^\S+\.py\s+(PASS|FAIL)\b", text.get("conformance tests", ""), re.M)
summary = [
    f"{'integrity':<14}{integrity}",
    f"{'values':<14}{counts(text.get('values', ''), 'checks')}",
    f"{'conformance':<14}{conf.count('PASS')} of {len(conf)} tests pass",
    f"{'experiments':<14}{counts(text.get('experiments', ''), 'experiment checks')}",
]
print("\n" + "\n".join(summary))
expected = (ROOT / "expected/verify_summary.txt").read_text().splitlines()
if not tsr:
    clause = lambda l: l.split("; Freezes A to D", 1)[0]
    summary, expected = [clause(l) for l in summary], [clause(l) for l in expected]
    print("The RFC 3161 receipts were not verified: the summary is compared without the Freeze clause.")
if summary == expected:
    print("The summary equals expected/verify_summary.txt.")
else:
    failed.append("summary")
    print("The summary differs from expected/verify_summary.txt, which reads:")
    print("\n".join(expected))
print("\nall steps passed" if not failed else "\nFAILED: " + ", ".join(failed))
sys.exit(1 if failed else 0)
