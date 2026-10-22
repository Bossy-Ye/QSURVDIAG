"""Native runs of the separating setting of the QED-C constructed pair (QEDC_EXTENSION.md), widths 2-8."""
import os, gzip, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C
from x1_qedc_setting import tfim_gates, TAU, J
from x1_run import job, N

DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", DIR.parents[1] / "output")) / "observation_change"; OUT.mkdir(parents=True, exist_ok=True)
MUT_SEEDS, ORIG_SEEDS = list(range(19042, 19054)), list(range(20042, 20054))
SETTING = lambda n: "X" + "Z" * (n - 1)

if __name__ == "__main__":
    jobs = []
    for n in range(2, 9):
        p, m = tfim_gates(n, 2 * TAU * J), tfim_gates(n, 2 * TAU * J, 0)
        po = C.sv(p, n); pr = np.abs(C.rotate(po, n, SETTING(n))) ** 2; pz = np.abs(po) ** 2
        ref = next(x[3] for x in C.universe(pr, pr, n) if x[:2] == ("marginal", 0))
        refz = next(x[3] for x in C.universe(pz, pz, n) if x[:2] == ("marginal", 0))
        lines, clines = C.pragma_lines("marginal", 0, n, ref, pr), C.pragma_lines("marginal", 0, n, refz, pz)
        pair = f"qedc_constructed_n{n}"
        jobs += [(pair, "original", "rotated", p, n, SETTING(n), lines, s) for s in ORIG_SEEDS]
        jobs += [(pair, "mutant", "rotated", m, n, SETTING(n), lines, s) for s in MUT_SEEDS]
        jobs += [(pair, "mutant", "control", m, n, None, clines, s) for s in MUT_SEEDS]
    t0 = time.time()
    with ProcessPoolExecutor(2) as ex: res = list(ex.map(job, jobs, chunksize=4))
    with gzip.open(OUT / "X1_QEDC_NATIVE_RUNS.jsonl.gz", "wt") as f:
        for x in res: f.write(json.dumps(x, separators=(",", ":")) + "\n")
    summ = {}
    for n in range(2, 9):
        R = [x for x in res if x["pair"] == f"qedc_constructed_n{n}"]
        k = lambda role, arm: sum(x["cli"] == "KILLED" for x in R if x["role"] == role and x["arm"] == arm)
        summ[n] = {"mutant_kills": k("mutant", "rotated"), "original_failures": k("original", "rotated"), "control_kills": k("mutant", "control"),
                   "unsupported": sum(x["cli"] == "UNSUPPORTED" for x in R), "cli_equals_inproc": all(x["cli"] == x["inproc"] for x in R)}
        summ[n]["supported"] = summ[n]["mutant_kills"] == 12 and summ[n]["original_failures"] <= 1
    json.dump({"setting": "X on qubit 0, Z elsewhere", "witness": "marginal q0", "N": N, "by_width": summ,
               "seconds": round(time.time() - t0, 1)}, open(OUT / "X1_QEDC_SUMMARY.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))
