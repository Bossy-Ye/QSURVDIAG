"""R3: the 115 survivors of the 20 circuits whose final state differs, under a contract restricted to the declared
output register (equal reduced states on the output qubits) instead of the full final state."""
import collections, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "reanalysis"; OUT.mkdir(parents=True, exist_ok=True)
EQ = 1e-9
orig, nq, outreg, mut = C.load_population()
fin = C.final_reports()


def reduced(psi, n, keep):
    t = psi.reshape([2] * n)                      # axis j is qubit n-1-j (little-endian)
    axes_keep = [n - 1 - q for q in sorted(keep, reverse=True)]
    axes_drop = [a for a in range(n) if a not in axes_keep]
    t = np.transpose(t, axes_keep + axes_drop).reshape(2 ** len(keep), -1)
    return t @ t.conj().T


rows, by = [], collections.Counter()
for k, r in fin.items():
    if r["v2_report"] not in ("CL3", "CL4", "CL5"):
        continue
    m = mut[k]; p = m["subject"]; n = nq[p]; reg = outreg[p]
    rp, rm = reduced(C.sv(orig[p], n), n, reg), reduced(C.sv(m["gates"], n), n, reg)
    d = float(np.max(np.abs(rp - rm)))
    eq = d <= EQ
    rows.append({"pair": k, "program": p, "n": n, "output_register": reg, "report": r["v2_report"], "reduced_max_diff": d,
                 "register_contract_equivalent": eq})
    by[(r["v2_report"], eq)] += 1
summ = {"pairs": len(rows), "output_register_full": sum(len(outreg[x["program"]]) == x["n"] for x in rows),
        "by_report": {o: {"equivalent_on_register": by[(o, True)], "different_on_register": by[(o, False)]} for o in ("CL3", "CL4", "CL5")},
        "equivalent_by_program": dict(collections.Counter(x["program"] for x in rows if x["register_contract_equivalent"])),
        "smallest_nonzero_diff": min((x["reduced_max_diff"] for x in rows if not x["register_contract_equivalent"]), default=None)}
json.dump({"summary": summ, "pairs": rows}, open(OUT / "R3_REGISTER_CONTRACT.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
