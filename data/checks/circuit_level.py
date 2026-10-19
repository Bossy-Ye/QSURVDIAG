"""Circuit-level view of the matched changes of Table 5: pairs eligible to change, pairs that change, circuits contributing,
and an exact two-sided sign test over circuits (circuits whose net change is zero are dropped).

Usage: python3 -I circuit_level.py <package root>
Reads archived records only; standard library.
"""
import collections, csv, math, sys
from pathlib import Path

R = Path(sys.argv[1])
rd = lambda p: list(csv.DictReader(open(R / p, newline="")))
sub = lambda m: m.split("#")[0]


P = {}   # contingent sign tests, for the Holm adjustment at the end


def sign_test(nets):
    pos, neg = sum(1 for v in nets.values() if v > 0), sum(1 for v in nets.values() if v < 0)
    n = pos + neg
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(pos, neg) + 1)) / 2 ** n) if n else None
    return pos, neg, p


def show(label, at_risk, changed, circuits, of, nets=None):
    line = f"{label}: {changed} of {at_risk} change; circuits contributing {circuits} of {of}"
    if nets is not None:
        pos, neg, p = sign_test(nets)
        line += f"; sign test over circuits: {pos} up, {neg} down, p = {p:.4f}"
        if not label.startswith("QUTest -> pytest"): P[label.split(" (")[0]] = p
    print(line)


# measurement settings (simulated): pairs that are observation limitations under the first setting and not the second
obs = [r for r in rd("data/certification/outcomes/R2V_TABLE_X_DECISIONS.csv") if r["part"] == "observation"]
ol = lambda r, s: r["R_S_v2"] == "false" and r[f"R_O_v2_{s}"] == "true"
for a, b, label in (("Z_output", "Z_all", "Z basis: output register -> all qubits"),
                    ("Z_output", "XYZ_output", "output register: Z -> X, Y, Z bases"),
                    ("Z_all", "XYZ_all", "all qubits: Z -> X, Y, Z bases"),
                    ("XYZ_output", "XYZ_all", "X, Y, Z bases: output register -> all qubits")):
    risk = [r for r in obs if ol(r, a)]
    leave = [r for r in risk if not ol(r, b)]
    enter = [r for r in obs if ol(r, b) and not ol(r, a)]
    assert not enter
    show(label, len(risk), len(leave), len({r["subject"] for r in leave}), len({r["subject"] for r in obs}))

# suites (native, N = 8,000): baseline suite omissions and observation limitations killed by each generic suite
fin = {r["mutant_id"]: r for r in rd("data/certification/outcomes/R2V_FINAL_PRIMARY.csv")}
k = {(r["suite"], r["mutant_id"]): r["outcome"] == "KILLED" for r in rd("data/primary/records/599_B5_A1G_POPULATION.csv")}
base = [m for (s, m) in k if s == "S_MIN"]
for rep, what in (("CL4", "suite omissions"), ("CL3", "observation limitations")):
    risk = [m for m in base if fin[m]["v2_report"] == rep]
    for s, label in (("S_FAMILY", "adjacent-pair"), ("S_COVER", "all-qubit"), ("S_BOTH", "combined")):
        kill = [m for m in risk if k[(s, m)] and not k[("S_MIN", m)]]
        show(f"baseline -> {label}, {what}", len(risk), len(kill), len({sub(m) for m in kill}), len({sub(m) for m in base}))
for s, label in (("S_FAMILY", "adjacent-pair"), ("S_COVER", "all-qubit"), ("S_BOTH", "combined")):
    other = [m for m in base if fin[m]["v2_report"] not in ("CL3", "CL4") and k[(s, m)] and not k[("S_MIN", m)]]
    lost = [m for m in base if k[("S_MIN", m)] and not k[(s, m)]]
    print(f"baseline -> {label}: other newly killed {len(other)} ({', '.join(sorted(fin[m]['v2_report'] for m in other)) or '-'}); lost {len(lost)}")

# output-condition suite (native, corrected suites where rerun)
rec = {r["mutant_id"]: r for r in rd("data/primary/records/T1_4_SSPEC_599.csv")}
by = collections.defaultdict(list)
for r in rd("data/output_condition/OC_RUNS.csv"):
    if r["kind"] != "guard": by[r["case"]].append(r["verdict"])
new = {m: ("KILLED" if v.count("KILLED") == len(v) else "OTHER") for m, v in by.items()}
oc = lambda m: new.get(m, rec[m]["outcome"]) == "KILLED"
nets = collections.Counter({sub(m): 0 for m in rec})
gain = lost = 0
for m in rec:
    x = int(oc(m) and not k[("S_MIN", m)]) - int(k[("S_MIN", m)] and not oc(m))
    nets[sub(m)] += x; gain += x > 0; lost += x < 0
risk = [m for m in rec if fin[m]["v2_report"] == "CL4"]
show(f"baseline -> output-condition ({len(rec)} pairs; gained {gain}, lost {lost}), suite omissions", len(risk),
     sum(1 for m in risk if oc(m)), sum(1 for v in nets.values() if v), len(nets), nets)

# testing profiles (simulated): pairs that become distinguishable (gained) or indistinguishable (lost)
itf = [r for r in rd("data/certification/outcomes/R2V_TABLE_X_DECISIONS.csv") if r["part"] == "interface"]
for tool in ("QuCheck", "pytest"):
    nets = collections.Counter({r["subject"]: 0 for r in itf})
    g = [r for r in itf if r["R_O_v2_QUTest"] == "true" and r[f"R_O_v2_{tool}"] == "false"]
    l = [r for r in itf if r["R_O_v2_QUTest"] == "false" and r[f"R_O_v2_{tool}"] == "true"]
    for r in g: nets[r["subject"]] += 1
    for r in l: nets[r["subject"]] -= 1
    risk = [r for r in itf if fin[r["mutant_id"]]["v2_report"] == "CL3"]
    show(f"QUTest -> {tool} (gained {len(g)}, lost {len(l)}), observation limitations", len(risk),
         sum(1 for r in risk if r[f"R_O_v2_{tool}"] == "false"), sum(1 for v in nets.values() if v), len(nets), nets)

# shot budget (native): configurations leaving or entering unresolved from N = 500 to N = 8,000
g = collections.defaultdict(dict)
for r in rd("data/certification/outcomes/R2V_DECISION_GRID.csv"): g[(r["mutant_id"], r["theta"])][int(r["N"])] = r
u = lambda x: x["v2_status"].startswith("unresolved")
nets, res, cre, units = collections.Counter(), 0, 0, 0
for (m, _), v in g.items():
    if 500 in v and 8000 in v:
        units += 1; x = int(u(v[500])) - int(u(v[8000])); nets[sub(m)] += x; res += x > 0; cre += x < 0
show(f"N: 500 -> 8,000 ({units} configurations; resolved {res}, created {cre})", units, res + cre,
     sum(1 for v in nets.values() if v), len(nets), nets)

# Holm adjustment over the three contingent sign tests (output-condition suite, QuCheck profile, shot budget)
order = sorted(P, key=P.get)
adj, run = {}, 0.0
for i, k in enumerate(order):
    run = max(run, min(1.0, (len(order) - i) * P[k])); adj[k] = run
for k in P: print(f"Holm-adjusted p, {k}: {adj[k]:.4f}")
