"""R1 evidence requirements as a classifier of reliable repairs; R5 adjusted mutation scores; R6 distinct behaviors
and sites of each outcome. Existing records only; witness order v3."""
import collections, csv, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "reanalysis"; OUT.mkdir(parents=True, exist_ok=True)
D = C.PKG / "data"
V3_MOVED = "qra_cases_v1_1/QRA_360"            # certification/witness_order/IMPACT.csv: withheld -> issued under v3
res = {}

# R1
cases = list(csv.DictReader(open(D / "all_pairs/ALLPAIRS_CASES.csv")))
fin = {r["case"]: r for r in csv.DictReader(open(D / "certification/outcomes/R2V_FINAL_CORPUS.csv"))}
fin.update({r["case"]: r for r in csv.DictReader(open(D / "prospective/mqt_bench/records/stage_c/C3_REPORTS.csv"))})
issued = lambda c: c["issued"] == "True" or c["case"] == V3_MOVED
reliable = lambda c: c["D_supported"] == "True"
tp = sum(issued(c) and reliable(c) for c in cases)
withheld = [c for c in cases if not issued(c)]
reason = lambda c: fin[c["case"]]["unmet"]
res["R1"] = {
    "candidates": len(cases), "issued": sum(map(issued, cases)), "witness_suite_reliable": sum(map(reliable, cases)),
    "issued_and_reliable": tp, "issued_not_reliable": [(c["case"], c["D_reason"]) for c in cases if issued(c) and not reliable(c)],
    "precision": f"{tp}/{sum(map(issued, cases))}", "recall": f"{tp}/{sum(map(reliable, cases))}",
    "withheld": len(withheld),
    "withheld_by_unmet": dict(collections.Counter(reason(c) for c in withheld)),
    "withheld_reliable_by_unmet": dict(collections.Counter(reason(c) for c in withheld if reliable(c))),
    "withheld_not_reliable_kills": dict(collections.Counter(c["D_reason"] for c in withheld if not reliable(c)))}

# R5
def scores(rows, eq_kinds, ol="CL3"):
    k = collections.Counter(r["v2_report"] for r in rows); tot = len(rows); kill = k["NA_KILLED"]
    eq = sum(k[x] for x in eq_kinds)
    return {"pairs": tot, "killed": kill, "outcomes": dict(k),
            "raw": [kill, tot, round(kill / tot, 4)],
            "without_equivalents": [kill, tot - eq, round(kill / (tot - eq), 4)],
            "without_equivalents_and_observation_limitations": [kill, tot - eq - k[ol], round(kill / (tot - eq - k[ol]), 4)]}
prim = list(csv.DictReader(open(D / "certification/outcomes/R2V_FINAL_PRIMARY.csv")))
corp = list(csv.DictReader(open(D / "certification/outcomes/R2V_FINAL_CORPUS.csv")))
for r in corp:
    if r["case"] == V3_MOVED: r["v2_report"] = "CL4"
res["R5"] = {"twenty_circuits": scores(prim, ["CL1"]), "twenty_circuits_with_executed_input_equality": scores(prim, ["CL1", "CL2"]),
             "corpus": scores(corp, ["CL1"])}

# R6
orig, nq, outreg, mut = C.load_population()
def key(psi):
    i = int(np.argmax(np.abs(psi) > 1e-9)); ph = psi[i] / abs(psi[i])
    return tuple(np.round(psi / ph, 8).view(float))
site = lambda i: (mut[i]["subject"], mut[i]["location"].split("@")[1].split(":")[0])   # program and gate position
by = collections.defaultdict(list)
for r in prim:
    if r["v2_report"] != "NA_KILLED": by[r["v2_report"]].append(r["mutant_id"])
r6 = {}
for o, ids in sorted(by.items()):
    states = {(mut[i]["subject"], key(C.sv(mut[i]["gates"], nq[mut[i]["subject"]]))) for i in ids}
    r6[o] = {"pairs": len(ids), "programs": len({mut[i]["subject"] for i in ids}), "distinct_final_states": len(states),
             "distinct_sites": len({site(i) for i in ids})}
res["R6"] = r6
json.dump(res, open(OUT / "R156_SUMMARY.json", "w"), indent=1)
print(json.dumps(res, indent=1))
