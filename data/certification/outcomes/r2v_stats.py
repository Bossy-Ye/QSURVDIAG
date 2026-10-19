"""The shot-budget contrast of Table X under v2 (V2_SPECIFICATION.md section 7).

mcnemar(), boot() and loco() are copied verbatim from github/code/analysis/b2_statistics.py
(frozen estimator: exact McNemar on the discordant cells; circuit-cluster percentile
bootstrap, B = 10000, seed 20260822; leave-one-circuit-out range). The v1 row is recomputed
first from the recorded ledger to show the copy reproduces it; the v2 row uses v2 statuses,
under which a natively killed cell stops at its verdict instead of counting as Unresolved.
"""
import csv, json, math, random, collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V

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
    return {"pairs": len(d), "clusters": len(set(cl)), "resolved": b, "created": c,
            "effect": sum(d) / len(d), "exact_mcnemar_p": mcnemar(b, c),
            "cluster_ci95": [lo, hi], "loco_range": [l1, l2]}

def main():
    S = list(csv.DictReader(open(V.PA + "github/results/recovered/599_B2_SHOT_FRESH.csv")))
    by = collections.defaultdict(dict)
    for r in S: by[(r["mutant_id"], r["theta"])][int(r["N"])] = r
    d1, c1 = [], []
    for k, v in by.items():
        if 500 in v and 8000 in v:
            d1.append(int(v[500]["supported_report"] == "Unresolved") - int(v[8000]["supported_report"] == "Unresolved"))
            c1.append(v[500]["subject"])
    G = list(csv.DictReader(open(os.path.join(V.HERE, "R2V_DECISION_GRID.csv"))))
    sub = {r["mutant_id"]: r["subject"] for r in S}
    g = collections.defaultdict(dict)
    for r in G: g[(r["mutant_id"], r["theta"])][int(r["N"])] = r
    d2, c2 = [], []
    for k, v in g.items():
        if 500 in v and 8000 in v:
            u = lambda x: x["v2_status"].startswith("unresolved")
            d2.append(int(u(v[500])) - int(u(v[8000]))); c2.append(sub[k[0]])
    out = {"v1_recomputed": row(d1, c1), "v2": row(d2, c2)}
    json.dump(out, open(os.path.join(V.HERE, "R2V_STATISTICS.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
