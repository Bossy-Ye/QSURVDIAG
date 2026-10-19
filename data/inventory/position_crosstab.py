"""Observation limitations (CL3) and suite omissions (CL4) by mutation position, with contributing programs and
sites. Usage: python3 -I position_crosstab.py out/cases_all.csv"""
import csv, sys
r = list(csv.DictReader(open(sys.argv[1])))
def pos(x): return "first gate" if x["first_gate"] == "True" else x["third"] + " (not first)"
print("population | outcome | total | first gate | early (not first) | middle | late   (each: pairs / programs / sites)")
for pop in ("20 circuits", "external", "MQT Bench", "width set", "corpus"):
    for rep, lab in (("CL3", "observation limitation"), ("CL4", "suite omission")):
        c = [x for x in r if x["population"] == pop and x["v2_report"] == rep]
        cells = []
        for p in ("first gate", "early (not first)", "middle (not first)", "late (not first)"):
            s = [x for x in c if pos(x) == p]
            cells.append(f"{len(s)} / {len({x['program'] for x in s})} / {len({(x['program'], x['anchor']) for x in s})}")
        print(f"{pop} | {lab} | {len(c)} | " + " | ".join(cells))
