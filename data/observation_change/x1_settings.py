"""X1, section 2: the separating setting of each observation limitation, from ideal states, before any native run.

Settings are enumerated by the number k of non-Z qubits (k = 1..n), then by qubit subset in lexicographic order,
then by basis tuple with X before Y. For each setting the declared QUTest universe is evaluated on the rotated joint
distribution of every qubit; the witness is the first instance in the closed witness order (v3) whose difference
exceeds theta. The separating setting is the first setting with a witness.
"""
import os, csv, itertools, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "observation_change"; OUT.mkdir(parents=True, exist_ok=True)
orig, nq, outreg, mut = C.load_population()
fin = C.final_reports()
ol = sorted((k for k, v in fin.items() if v["v2_report"] == "CL3"), key=lambda k: (mut[k]["subject"], k))
assert len(ol) == 35


def settings(n):
    for k in range(1, n + 1):
        for qs in itertools.combinations(range(n), k):
            for bs in itertools.product("XY", repeat=k):
                s = ["Z"] * n
                for q, b in zip(qs, bs): s[q] = b
                yield "".join(s), k


rows = []
for key in ol:
    m = mut[key]; p = m["subject"]; n = nq[p]
    po, pmu = C.sv(orig[p], n), C.sv(m["gates"], n)
    z = C.first_witness(np.abs(po) ** 2, np.abs(pmu) ** 2, n)
    assert z is None, (key, z)                       # observation limitation: nothing above theta unrotated
    found = None
    for s, k in settings(n):
        pp = np.abs(C.rotate(po, n, s)) ** 2; pm = np.abs(C.rotate(pmu, n, s)) ** 2
        w = C.first_witness(pp, pm, n)
        if w is not None:
            found = (s, k, w); break
    s, k, w = found
    rows.append({"pair": key, "program": p, "n": n, "setting_q0_first": s, "rotated_qubits": k,
                 "witness_kind": w[0], "witness_key": "" if w[1] is None else w[1],
                 "witness_d": f"{w[2]:.6f}", "reference": "" if w[3] is None else f"{w[3]:.6f}"})

with open(OUT / "X1_SETTINGS.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
summ = {"pairs": len(rows),
        "by_rotated_qubits": {str(k): sum(r["rotated_qubits"] == k for r in rows) for k in sorted({r["rotated_qubits"] for r in rows})},
        "by_witness_kind": {t: sum(r["witness_kind"] == t for r in rows) for t in sorted({r["witness_kind"] for r in rows})},
        "distinct_settings_per_program": {p: len({r["setting_q0_first"] for r in rows if r["program"] == p}) for p in sorted({r["program"] for r in rows})},
        "min_witness_d": min(float(r["witness_d"]) for r in rows)}
json.dump(summ, open(OUT / "X1_SETTINGS_SUMMARY.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
