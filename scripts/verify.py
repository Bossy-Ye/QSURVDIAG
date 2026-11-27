"""Run every record-tier check: integrity, values, conformance tests, experiments, then integrity again.

The summary printed at the end must equal expected/verify_summary.txt. A failed step or a different summary
gives a non-zero exit status."""

import argparse, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--out", default=ROOT / "output", help="output directory (default: output/ in the package)")
ap.add_argument("--no-tsr", action="store_true", help="skip the RFC 3161 receipts, which need OpenSSL")
args = ap.parse_args()
out = str(Path(args.out).resolve())
tsr = not args.no_tsr and shutil.which("openssl") is not None
if not tsr and not args.no_tsr:
    print("OpenSSL not found: the RFC 3161 receipts are not verified")

STEPS = {
    "integrity": ["verify_integrity.py"] + ["--tsr"] * tsr,
    "values": ["reproduce.py", "--out", out],
    "conformance tests": ["run_conformance_tests.py", "--out", out],
    "experiments": ["reproduce_experiments.py", "--out", out],
    "integrity after the runs": ["verify_integrity.py"],
}
failed, text = [], {}
for step, (script, *arguments) in STEPS.items():
    print(f"== {step}: python3 scripts/{' '.join([script, *arguments])}", flush=True)
    r = subprocess.run(
        [sys.executable, "-I", "-B", str(ROOT / "scripts" / script), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(r.stdout, end="", flush=True)
    text[step] = r.stdout
    if r.returncode:
        failed.append(step)


def tally(output, head, order=("MATCH", "PARTIAL", "ANALYTIC TIER")):
    """'<head>: N  STATUS: n  ...' as 'N checks: MATCH n, PARTIAL n, ANALYTIC TIER n'."""
    m = re.search(rf"^{head}: (\d+)  (.*)$", output, re.M)
    if not m:
        return "not available"
    n = dict(x.rsplit(": ", 1) for x in m[2].split("  ") if x)
    return f"{m[1]} checks: " + ", ".join(f"{k} {n[k]}" for k in [*order, *sorted(set(n) - set(order))] if k in n)


def integrity(output):
    files = re.search(r"^checksums: (\d+) files listed.*?, (\d+) problems", output, re.M)
    archived = re.search(r"^archived files: (\d+) identical.*?, (\d+) redacted", output, re.M)
    if not (files and archived):
        return "not available"
    # A freeze is verified when its receipt verifies and each manifest entry matches a file or a redaction.
    manifests = re.findall(
        r"Freeze ([ABCD]) manifest: (\d+) entr\w+, (\d+) matching(?:, (\d+) redacted.*?, 0 other)?", output
    )
    whole = lambda entries, matching, redacted: int(entries) == int(matching) + int(redacted or 0)
    verified = all(f"RFC 3161 Freeze {k}: Verification: OK" in output for k in "ABCD") and sorted(
        k for k, *counts in manifests if whole(*counts)
    ) == list("ABCD")
    return (
        f"{files[1]} files, {files[2]} problems; {archived[1]} archived files identical, {archived[2]} "
        f"redacted; "
        f"Freezes A to D {'verified' if verified else 'not verified'}"
    )


tests = re.findall(r"^\S+\.py\s+(PASS|FAIL)\b", text["conformance tests"], re.M)
summary = [
    f"{'integrity':<14}{integrity(text['integrity'])}",
    f"{'values':<14}{tally(text['values'], 'checks')}",
    f"{'conformance':<14}{tests.count('PASS')} of {len(tests)} tests pass",
    f"{'experiments':<14}{tally(text['experiments'], 'experiment checks')}",
]
print("\n" + "\n".join(summary))
expected = (ROOT / "expected/verify_summary.txt").read_text().splitlines()
if not tsr:
    without_freezes = lambda lines: [line.split("; Freezes A to D", 1)[0] for line in lines]
    summary, expected = without_freezes(summary), without_freezes(expected)
    print("The RFC 3161 receipts were not verified: the summary is compared without the Freeze clause.")
if summary == expected:
    print("The summary equals expected/verify_summary.txt.")
else:
    failed.append("summary")
    print("The summary differs from expected/verify_summary.txt, which reads:")
    print("\n".join(expected))
print("\nall steps passed" if not failed else "\nFAILED: " + ", ".join(failed))
sys.exit(1 if failed else 0)
