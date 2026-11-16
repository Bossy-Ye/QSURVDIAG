"""Separating settings read off the original: for each of the 100 observation limitations (the 35 of the 20 circuits
and the 65 at later positions), the number of basis states in the original's ideal final state on the executed input,
the setting with X on every qubit in superposition in that state, whether it is the named separating setting, and
whether an instance of the declared universe separates the pair under it.

The 35 pairs of the 20 circuits come from the frozen population; the 65 later-position pairs need the programs and
gates that data/position/x4_select.py writes to $QSD_OUT/position, and are skipped when these files are absent.
Writes X1_TWO_STATE.csv.

Usage: <analytic python> -B x1_two_state.py
"""
import os, csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C

DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output"))
OUT = ROOT / "observation_change"; OUT.mkdir(parents=True, exist_ok=True)


def superposed(po, n):
    p = np.abs(po) ** 2; idx = np.arange(2 ** n)
    return "".join("X" if 1e-9 < p[((idx >> q) & 1) == 1].sum() < 1 - 1e-9 else "Z" for q in range(n))


def row(pair, pop, prog, n, og, mg, named):
    po, pm = C.sv(og, n), C.sv(mg, n); s = superposed(po, n)
    r = lambda v: np.abs(C.rotate(v, n, s)) ** 2
    return {"pair": pair, "population": pop, "program": prog, "n": n, "basis_states": int((np.abs(po) ** 2 > 1e-9).sum()),
            "x_on_superposed": s, "named_setting": named, "is_named": s == named,
            "separates": C.first_witness(r(po), r(pm), n) is not None}


orig, nq, outreg, mut = C.load_population()
rows = [row(x["pair"], "primary", x["program"], int(x["n"]), orig[x["program"]], mut[x["pair"]]["gates"], x["setting_q0_first"])
        for x in csv.DictReader(open(DIR / "X1_SETTINGS.csv"))]
sp, gp = ROOT / "position/X4_SUBJECTS.json", ROOT / "position/X4_MUTANT_GATES.json"
if sp.exists() and gp.exists():
    S, G = json.load(open(sp)), json.load(open(gp))
    for x in csv.DictReader(open(DIR / "X1_POSITION_SETTINGS.csv")):
        s = S[x["program"]]
        rows.append(row(x["pair"], x["population"], x["program"], s["n"], s["prep"] + s["gates"], s["prep"] + G[x["pair"]],
                        x["setting_q0_first"]))
with open(OUT / "X1_TWO_STATE.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "pairs")
