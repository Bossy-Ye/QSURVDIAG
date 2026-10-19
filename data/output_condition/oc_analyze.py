"""Matched analysis of the output-condition suites, recorded and corrected (plan: PLAN.md).

Usage: python3 -I oc_analyze.py <package root> <OC_RUNS.csv or -> <out json>
With '-' only the recorded suites are analysed (reproduces the archived matched-changes row).
mcnemar(), boot() and loco() are copied verbatim from data/certification/outcomes/r2v_stats.py.
"""
import csv, json, math, random, collections, sys
from pathlib import Path

PKG = Path(sys.argv[1]); RUNS = sys.argv[2]; OUTP = sys.argv[3]

def mcnemar(b, c):
    if b + c == 0: return None
    return min(1.0, 2 * sum(math.comb(b + c, i) for i in range(0, min(b, c) + 1)) / 2 ** (b + c))

def boot(pairs, clusters, B=10000, seed=20260822):
    rng = random.Random(seed)
    by = collections.defaultdict(list)
    for cl, d in zip(clusters, pairs): by[cl].append(d)
    ks = sorted(by)
    est = []
    for _ in range(B):
        s = [by[rng.choice(ks)] for _ in ks]
        flat = [x for g in s for x in g]
        est.append(sum(flat) / len(flat) if flat else 0.0)
    est.sort()
    return est[int(0.025 * B)], est[int(0.975 * B)]

def loco(pairs, clusters):
    by = collections.defaultdict(list)
    for cl, d in zip(clusters, pairs): by[cl].append(d)
    ks = sorted(by)
    vals = []
    for drop in ks:
        flat = [x for k in ks if k != drop for x in by[k]]
        if flat: vals.append(sum(flat) / len(flat))
    return min(vals), max(vals)

def row(d, cl):
    b, c = sum(1 for x in d if x == 1), sum(1 for x in d if x == -1)
    lo, hi = boot(d, cl); l1, l2 = loco(d, cl)
    return {"pairs": len(d), "clusters": len(set(cl)), "newly_killed": b, "lost_kills": c,
            "effect_pp": round(100 * sum(d) / len(d), 1), "exact_mcnemar_p": mcnemar(b, c),
            "cluster_ci95_pp": [round(100 * lo, 1), round(100 * hi, 1)], "loco_range_pp": [round(100 * l1, 1), round(100 * l2, 1)]}

pop = list(csv.DictReader(open(PKG / "data/primary/records/599_B5_A1G_POPULATION.csv")))
base = {r["mutant_id"]: r["outcome"] for r in pop if r["suite"] == "S_MIN"}
rec = {r["mutant_id"]: r for r in pop if r["suite"] == "S_SPEC"}
fin = {r["mutant_id"]: r for r in csv.DictReader(open(PKG / "data/certification/outcomes/R2V_FINAL_PRIMARY.csv"))}

def verdict(k, reps=12): return "KILLED" if k == reps else ("SURVIVED" if k == 0 else "SPLIT")
new = {}
guards = {}
if RUNS != "-":
    by = collections.defaultdict(list)
    for r in csv.DictReader(open(RUNS)): by[(r["kind"], r["case"])].append(r["verdict"])
    for (kind, case), v in by.items():
        if kind == "guard": guards[case] = {"fails": v.count("KILLED"), "unsupported": v.count("UNSUPPORTED"), "runs": len(v)}
        else: new[case] = "UNSUPPORTED" if "UNSUPPORTED" in v else verdict(v.count("KILLED"), len(v))

def suite_outcome(mid):
    if mid in new: return new[mid]
    return rec[mid]["outcome"]          # GHZ, and every pair when only the recorded suites are analysed

out = {"guards": guards}
for label, use_new in (("recorded", False), ("corrected", True)):
    if use_new and not new: continue
    d, cl, tab = [], [], collections.Counter()
    for mid, r in rec.items():
        b = base[mid]; s = suite_outcome(mid) if use_new else r["outcome"]
        x = 1 if (b != "KILLED" and s == "KILLED") else (-1 if (b == "KILLED" and s != "KILLED") else 0)
        d.append(x); cl.append(r["subject"])
        tab[(fin[mid]["v2_report"], b, s)] += 1
    res = row(d, cl)
    fig = collections.Counter()
    for mid, r in rec.items():
        rep = fin[mid]["v2_report"]
        if rep in ("CL3", "CL4"):
            s = suite_outcome(mid) if use_new else r["outcome"]
            fig[(rep, r["subject"].split("_")[0], s)] += 1
    out[label] = {"table5_row": res,
                  "by_report_baseline_suite": {f"{a}|{b}|{c}": v for (a, b, c), v in sorted(tab.items())},
                  "figure_4b_cases": {f"{a}|{b}|{c}": v for (a, b, c), v in sorted(fig.items())},
                  "figure_4b_totals": {"suite_omissions": sum(v for (a, _, _), v in fig.items() if a == "CL4"),
                                       "suite_omissions_killed": sum(v for (a, _, s), v in fig.items() if a == "CL4" and s == "KILLED"),
                                       "observation_limitations": sum(v for (a, _, _), v in fig.items() if a == "CL3"),
                                       "observation_limitations_killed": sum(v for (a, _, s), v in fig.items() if a == "CL3" and s == "KILLED")}}
json.dump(out, open(OUTP, "w"), indent=1)
print(json.dumps({k: (v["table5_row"], v["figure_4b_totals"]) if k != "guards" else v for k, v in out.items()}, indent=1))
