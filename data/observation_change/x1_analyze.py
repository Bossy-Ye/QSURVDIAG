"""Decisions and summaries of the separating settings (PLAN.md, section 4) and of the QED-C constructed pair
(QEDC_EXTENSION.md) from the per-run records. Standard library only."""
import os, csv, gzip, json, collections
from pathlib import Path

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "observation_change"; OUT.mkdir(parents=True, exist_ok=True)
S = {r["pair"]: r for r in csv.DictReader(open(DIR / "X1_SETTINGS.csv"))}
runs = [json.loads(l) for l in gzip.open(DIR / "X1_NATIVE_RUNS.jsonl.gz", "rt")]
assert all(r["cli"] == r["inproc"] for r in runs), "CLI and in-process verdicts disagree"
assert not any(r["cli"] == "UNSUPPORTED" for r in runs)
g = collections.defaultdict(list)
for r in runs: g[(r["pair"], r["role"], r["arm"])].append(r)
rows = []
for p, s in S.items():
    mk = sum(r["cli"] == "KILLED" for r in g[(p, "mutant", "rotated")])
    of = sum(r["cli"] == "KILLED" for r in g[(p, "original", "rotated")])
    ck = sum(r["cli"] == "KILLED" for r in g[(p, "mutant", "control")])
    assert len(g[(p, "mutant", "rotated")]) == len(g[(p, "original", "rotated")]) == len(g[(p, "mutant", "control")]) == 12
    rows.append({**s, "mutant_kills": mk, "original_failures": of, "control_kills": ck,
                 "supported": mk == 12 and of <= 1})
with open(OUT / "X1_NATIVE_RUNS.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
summ = {"pairs": len(rows), "supported": sum(r["supported"] for r in rows),
        "not_supported": [(r["pair"], r["mutant_kills"], r["original_failures"]) for r in rows if not r["supported"]],
        "original_failures_total": sum(r["original_failures"] for r in rows),
        "control_kills_total": sum(r["control_kills"] for r in rows),
        "executions": len(runs),
        "by_rotated_qubits": dict(collections.Counter(int(r["rotated_qubits"]) for r in rows)),
        "distinct_settings_per_program": {p: len({r["setting_q0_first"] for r in rows if r["program"] == p}) for p in sorted({r["program"] for r in rows})}}
json.dump(summ, open(OUT / "X1_SUMMARY.json", "w"), indent=1)
print(json.dumps(summ, indent=1))

q = [json.loads(l) for l in gzip.open(DIR / "X1_QEDC_NATIVE_RUNS.jsonl.gz", "rt")]
assert all(r["cli"] == r["inproc"] for r in q)
qs = {}
for n in range(2, 9):
    R = [r for r in q if r["pair"] == f"qedc_constructed_n{n}"]
    k = lambda role, arm: sum(r["cli"] == "KILLED" for r in R if r["role"] == role and r["arm"] == arm)
    qs[str(n)] = {"mutant_kills": k("mutant", "rotated"), "original_failures": k("original", "rotated"), "control_kills": k("mutant", "control"),
                  "unsupported": sum(r["cli"] == "UNSUPPORTED" for r in R), "cli_equals_inproc": all(r["cli"] == r["inproc"] for r in R)}
    qs[str(n)]["supported"] = qs[str(n)]["mutant_kills"] == 12 and qs[str(n)]["original_failures"] <= 1
json.dump(qs, open(OUT / "X1_QEDC_BY_WIDTH.json", "w"), indent=1)
print(json.dumps(qs))
