"""Concentration of causes and repair designs per population, from cases_all.csv (written by inventory.py).

Usage: python3 -I concentration.py <out_dir>/cases_all.csv <out_dir>/concentration.json
For each population and cause (CL3, CL4): pairs, distinct programs, distinct sites (program, gate index),
pairs per program (max, top-3 share), and for CL4 pairs per repaired-suite design (program, witness).
"""
import collections
import csv
import json
import sys


def main(path, outp):
    rows = list(csv.DictReader(open(path, newline="")))
    res = {}
    for pop in sorted({r["population"] for r in rows}):
        pr = [r for r in rows if r["population"] == pop]
        for cl in ("CL3", "CL4"):
            rr = [r for r in pr if r["v2_report"] == cl]
            if not rr:
                continue
            per_prog = collections.Counter(r["program"] for r in rr)
            per_site = collections.Counter((r["program"], r["anchor"]) for r in rr)
            d = {"pairs": len(rr), "programs": len(per_prog), "sites": len(per_site),
                 "max_pairs_per_program": max(per_prog.values()),
                 "top3_program_share": round(sum(v for _, v in per_prog.most_common(3)) / len(rr), 3),
                 "max_pairs_per_site": max(per_site.values()),
                 "families": len({r["family"] for r in rr}),
                 "top_programs": per_prog.most_common(3)}
            if cl == "CL4":
                per_design = collections.Counter((r["program"], r.get("declared_outputs", ""), r["w_kind"], r["w_key"]) for r in rr)
                d["designs"] = len(per_design)
                d["max_pairs_per_design"] = max(per_design.values())
                d["top3_design_share"] = round(sum(v for _, v in per_design.most_common(3)) / len(rr), 3)
                d["singleton_designs"] = sum(1 for v in per_design.values() if v == 1)
            res["%s|%s" % (pop, cl)] = d
            print(pop, cl, json.dumps(d))
    json.dump(res, open(outp, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
