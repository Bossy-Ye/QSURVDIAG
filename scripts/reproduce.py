"""Recompute the article's values from the archived records and compare them with expected/expected_results.csv.

Usage:  python3 scripts/reproduce.py [--out DIR]
Runs the five record-level engines (Python standard library only), writes their outputs and
results_verification.csv to DIR (default: ./output), and exits non-zero if any value differs.
"""
import argparse, csv, os, subprocess, sys
sys.dont_write_bytecode = True
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "output")); a = ap.parse_args()
OUT = Path(a.out).resolve(); OUT.mkdir(parents=True, exist_ok=True)
if ROOT / "data" in OUT.parents or OUT == ROOT / "data":
    sys.exit("refusing to write inside data/")
env = {**os.environ, "QSD_OUT": str(OUT)}
ENGINES = ["manuscript_checks", "ledger_checks", "protocol_checks", "extra_checks", "records_checks"]
for e in ENGINES:
    r = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/checks" / f"{e}.py")], env=env, capture_output=True, text=True)
    (OUT / f"{e}.log").write_text(r.stdout + r.stderr)
    print(f"{e:<18} exit {r.returncode}")
    if r.returncode: sys.exit(f"{e} failed; see {OUT / (e + '.log')}")

got = {}
for r in csv.DictReader(open(OUT / "manuscript_checks.csv")): got[r["check_id"]] = r["recomputed"]
for r in csv.DictReader(open(OUT / "ledger_checks.csv")): got["L-" + r["id"]] = r["recomputed_value"]
for f in ("protocol_checks.csv", "extra_checks.csv", "records_checks.csv"):
    for r in csv.DictReader(open(OUT / f)): got[r["check_id"]] = r["recomputed"]

AGG_LEVELS = ("archived aggregate", "literal", "frozen decision record", "protocol record", "recorded git history", "archived structural records")
rows, cnt = [], Counter()
for e in csv.DictReader(open(ROOT / "expected/expected_results.csv")):
    cid = e["check_id"]
    if e["engine"] == "reproduce_analytic":
        continue                                                   # reported by scripts/reproduce_analytic.py
    g = got.get(cid)
    if g is None: status = "NOT REPRODUCIBLE"
    elif str(g).startswith("SKIPPED"): status = "NOT REPRODUCED HERE (analytic tier)"
    elif str(g) != e["expected"]: status = "MISMATCH"
    elif any(e["evidence_level"].startswith(x) for x in AGG_LEVELS) or "aggregate" in e["evidence_level"]: status = "PARTIAL"
    else: status = "MATCH"
    cnt[status] += 1
    rows.append({"check_id": cid, "engine": e["engine"], "label": e["label"], "printed_in_manuscript": e["printed_in_manuscript"],
                 "evidence_level": e["evidence_level"], "inputs": e["inputs"], "command": "python3 scripts/reproduce.py",
                 "expected": e["expected"], "reproduced": g, "status": status})
with open(OUT / "results_verification.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
printed = Counter(r["status"] for r in rows if r["printed_in_manuscript"] == "yes")
print(f"\nchecks: {len(rows)}  " + "  ".join(f"{k}: {v}" for k, v in sorted(cnt.items())))
print("values printed in the article: " + "  ".join(f"{k}: {v}" for k, v in sorted(printed.items())))
print("MATCH = recomputed from per-case records or logs; PARTIAL = equal, but verified against an archived aggregate,")
print("protocol record or recorded git history. Full table: " + str(OUT / "results_verification.csv"))
sys.exit(1 if cnt["MISMATCH"] or cnt["NOT REPRODUCIBLE"] else 0)
