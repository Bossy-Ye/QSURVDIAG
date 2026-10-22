"""Decisions and summaries of the separating settings (PLAN.md, section 4), of the QED-C constructed pair
(QEDC_EXTENSION.md) and of the later-position observation limitations (POSITION_EXTENSION.md) from the per-run
records. Standard library only."""
import os, csv, gzip, json, collections, statistics
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

P = list(csv.DictReader(open(DIR / "X1_POSITION_SETTINGS.csv")))
pr = [json.loads(l) for l in gzip.open(DIR / "X1_POSITION_NATIVE_RUNS.jsonl.gz", "rt")]
assert all(r["cli"] == r["inproc"] for r in pr) and not any(r["cli"] == "UNSUPPORTED" for r in pr)
g = collections.defaultdict(list)
for r in pr: g[(r["pair"], r["role"], r["arm"])].append(r)
prow = []
for s in P:
    k = lambda role, arm: sum(r["cli"] == "KILLED" for r in g[(s["pair"], role, arm)])
    if s["setting_q0_first"]:
        assert all(len(g[(s["pair"], ro, a)]) == 12 for ro, a in (("mutant", "rotated"), ("original", "rotated"), ("mutant", "control")))
    prow.append({**s, "mutant_kills": k("mutant", "rotated"), "original_failures": k("original", "rotated"),
                 "control_kills": k("mutant", "control"), "supported": k("mutant", "rotated") == 12 and k("original", "rotated") <= 1})
with open(OUT / "X1_POSITION_NATIVE_RUNS.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(prow[0])); w.writeheader(); w.writerows(prow)
ev = [int(r["settings_evaluated"]) for r in prow]
ps = {"pairs": len(prow), "with_setting": sum(bool(r["setting_q0_first"]) for r in prow), "supported": sum(r["supported"] for r in prow),
      "supported_by_population": {p: f"{sum(r['supported'] for r in prow if r['population'] == p)}/{sum(r['population'] == p for r in prow)}"
                                  for p in sorted({r["population"] for r in prow})},
      "not_supported": [(r["pair"], r["mutant_kills"], r["original_failures"]) for r in prow if not r["supported"]],
      "original_failures_total": sum(r["original_failures"] for r in prow), "control_kills_total": sum(r["control_kills"] for r in prow),
      "executions": len(pr), "by_rotated_qubits": dict(sorted(collections.Counter(int(r["rotated_qubits"]) for r in prow if r["rotated_qubits"]).items())),
      "settings_evaluated_median": statistics.median(ev), "settings_evaluated_max": max(ev),
      "search_seconds_total": round(sum(float(r["search_seconds"]) for r in prow), 1)}
json.dump(ps, open(OUT / "X1_POSITION_SUMMARY.json", "w"), indent=1)
print(json.dumps(ps, indent=1))

