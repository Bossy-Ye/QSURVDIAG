"""Recompute the values of expected/values.csv from the archived records (standard library only).

Writes the output of each check module and results_verification.csv. A differing or missing value gives a
non-zero exit status."""

import argparse, csv, os, subprocess, sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from paths import CATALOGUE, ROOT, output

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--out", default=ROOT / "output", help="output directory (default: output/ in the package)")
OUT = output(ap.parse_args().out)

MODULES = {  # module: prefix of its check ids, id column and value column of its CSV
    "article_checks": ("", "check_id", "recomputed"),
    "ledger_checks": ("L-", "id", "recomputed_value"),
    "protocol_checks": ("", "check_id", "recomputed"),
    "records_checks": ("", "check_id", "recomputed"),
}
PARTIAL = (
    "archived aggregate",
    "frozen decision record",
    "protocol record",
    "recorded git history",
    "archived structural records",
)
got = {}
for module, (prefix, key, value) in MODULES.items():
    r = subprocess.run(
        [sys.executable, "-I", "-B", str(ROOT / f"scripts/checks/{module}.py")],
        env={**os.environ, "QSD_OUT": str(OUT)},
        capture_output=True,
        text=True,
    )
    (OUT / f"{module}.log").write_text(r.stdout + r.stderr)
    print(f"{module:<18} exit {r.returncode}")
    if r.returncode:
        sys.exit(f"{module} failed; see {OUT / (module + '.log')}")
    with open(OUT / f"{module}.csv") as f:
        got.update((prefix + x[key], x[value]) for x in csv.DictReader(f))


def status(check, value):
    level = check["evidence_level"]
    if value is None:
        return "NO VALUE"
    if value.startswith("SKIPPED"):
        return "ANALYTIC TIER"
    if value != check["expected"]:
        return "MISMATCH"
    return "PARTIAL" if level.startswith(PARTIAL) or "aggregate" in level else "MATCH"


DESCRIPTION = ("check_id", "module", "label", "printed_in_article", "evidence_level", "inputs")
rows = [
    {
        **{k: c[k] for k in DESCRIPTION},
        "command": "python3 scripts/reproduce.py",
        "expected": c["expected"],
        "reproduced": got.get(cid),
        "status": status(c, got.get(cid)),
    }
    for cid, c in CATALOGUE.items()
    if c["module"] != "reproduce_analytic"
]
with open(OUT / "results_verification.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
tally = lambda rs: "  ".join(f"{k}: {n}" for k, n in sorted(Counter(r["status"] for r in rs).items()))
print(f"\nchecks: {len(rows)}  {tally(rows)}")
print("values printed in the article: " + tally([r for r in rows if r["printed_in_article"] == "yes"]))
print(
    "MATCH = recomputed from per-case records or logs; "
    "PARTIAL = equal, but verified against an archived aggregate,"
)
print(f"protocol record or recorded git history. Full table: {OUT / 'results_verification.csv'}")
sys.exit(any(r["status"] in ("MISMATCH", "NO VALUE") for r in rows))
