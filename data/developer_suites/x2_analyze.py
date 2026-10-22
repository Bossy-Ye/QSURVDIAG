"""PLAN.md, sections 4 and 6: outcomes per suite, contract equivalence against the authors' labels, cross-suite survivors.

Reads the archived X2_NATIVE_RUNS.jsonl.gz, X2_CONFIRM.json and X2_CONTEXT_STATES.json. Outcome rules: OPERATIONAL.md
(X2_OPERATIONAL, X2_STATE_RELATION).
"""
import collections, csv, gzip, json, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", HERE.parents[1] / "output")) / "developer_suites"; OUT.mkdir(parents=True, exist_ok=True)
runs = [json.loads(l) for l in gzip.open(HERE / "X2_NATIVE_RUNS.jsonl.gz", "rt")]
conf = json.load(open(HERE / "X2_CONFIRM.json"))
cstates = json.load(open(HERE / "X2_CONTEXT_STATES.json"))
guards = collections.defaultdict(list); pairs = collections.defaultdict(list)
for r in runs:
    (guards[(r["suite"], r["program"])] if r["kind"] == "guard" else pairs[(r["suite"], r["program"], r["version"])]).append(r)

# program equality over F (both suites) and over X_S
eqF = collections.defaultdict(dict); eqS = collections.defaultdict(dict)
for (s, p, v), rs in pairs.items():
    for r in rs:
        for sig, e in r["program_equal"].items():
            eqF[(p, v)][sig] = eqF[(p, v)].get(sig, True) and e
            eqS[(s, p, v)][sig] = eqS[(s, p, v)].get(sig, True) and e

rows = []
for (s, p, v), rs in sorted(pairs.items()):
    assert len(rs) == 12, (s, p, v, len(rs))
    kills = sum(not r["passed"] for r in rs)
    row = {"suite": s, "program": p, "mutant": v, "label": "em" if v.startswith("em") else "m", "kills": kills,
           "contract_equivalent_F": all(eqF[(p, v)].values()), "inputs_F": len(eqF[(p, v)]), "inputs_S": len(eqS[(s, p, v)])}
    if kills == 12: row["outcome"] = "killed"
    elif kills > 0: row["outcome"] = "unresolved: split verdict"
    elif not all(r["aligned"] for r in rs): row["outcome"] = "unresolved: alignment"
    elif row["contract_equivalent_F"]: row["outcome"] = "contract equivalence"
    elif all(eqS[(s, p, v)].values()): row["outcome"] = "executed-input equality"
    elif all(r["observation_equal"] for r in rs):             # OPERATIONAL.md, X2_STATE_RELATION
        st = cstates.get(f"{s}|{p}|{v}")
        row["outcome"] = ("unresolved: context states" if st is None else
                          "executed-input equality" if st["all_equal"] else "observation limitation")
    else:
        w = next((r["witness"] for r in rs if r["witness"]), None)
        if w is None: row["outcome"] = "below-tolerance difference"
        else:
            row.update({"witness": f"{w['kind']}:{w['key']}@{w['context']}", "witness_d": round(w["d"], 6)})
            c = conf.get(f"{s}|{p}|{v}")
            row["outcome"] = ("suite omission" if c and c["supported"] else
                              "unresolved: confirmation" if c else "suite omission candidate")
    rows.append(row)
fields = ["suite", "program", "mutant", "label", "kills", "outcome", "contract_equivalent_F", "inputs_F", "inputs_S", "witness", "witness_d"]
with open(OUT / "X2_DIAGNOSIS.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

by = {(r["suite"], r["program"], r["mutant"]): r for r in rows}
labels = collections.Counter()
for (p, v), d in eqF.items():
    labels[("em" if v.startswith("em") else "m", "equivalent" if all(d.values()) else "not equivalent")] += 1
cross = []
for (s, p, v), r in by.items():
    o = by.get(("B" if s == "A" else "A", p, v))
    if o and r["outcome"] != "killed" and o["outcome"] == "killed":
        cross.append({"survives": s, "program": p, "mutant": v, "outcome_under_surviving_suite": r["outcome"]})
summ = {"guard_failures": {f"{s}:{p}": sum(not r["passed"] for r in rs) for (s, p), rs in guards.items()},
        "outcomes": {s: dict(collections.Counter(r["outcome"] for r in rows if r["suite"] == s)) for s in "AB"},
        "contract_equivalence_vs_labels": {f"{a}/{b}": n for (a, b), n in labels.items()},
        "survive_one_suite_killed_by_other": cross}
json.dump(summ, open(OUT / "X2_SUMMARY.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
