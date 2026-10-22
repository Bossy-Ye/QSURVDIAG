"""OPERATIONAL.md (X2_NEGATIVE_CONTROL): negative control of each natively confirmed suite omission.

The control is the first instance of the suite-B universe (single-qubit marginals of each measured bit, contexts in
submission order) whose difference is decided below theta, in the run that gave the witness (seed 15042). Its context
runs alone at 2,000 shots on the mutant (seeds 15042-15053) and the original (guard, seeds 16042-16044), with the
original's ideal value rounded to 4 decimals as reference and tolerance 0.05. Supported: fewer than 12 mutant kills
and no failure of the original.

Usage: X2_SRC=<QuCheck checkout> <QuCheck environment python> -B x2_control.py   (after x2_run.py has cached the
original's capture at seed 15042)
"""
import json, pickle, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import x2_capture as X
from x2_confirm import HERE, OUT, N, THETA, MUT_SEEDS, ORIG_SEEDS, counts_dist, verdict
from x2_run import RES, ordered_b, _qpy

SEED = 15042


def control(suite, program, version):
    from qiskit_aer.backends.aerbackend import AerBackend
    o = pickle.load(open(OUT / "cache" / f"{suite}_{program}_{SEED}.pkl", "rb"))
    held = []; run0 = AerBackend.run
    def keep(self, c, *a, **k):
        held.extend(c if isinstance(c, (list, tuple)) else [c]); return run0(self, c, *a, **k)
    AerBackend.run = keep
    _, ctx_m, _ = X.run_capture(suite, program, version, SEED, 20, 2500)
    AerBackend.run = run0
    for i, (c1, c2) in enumerate(zip(o["ctx"], ctx_m)):
        n = len(c1["measured"])
        for kind, key, d, ref in ordered_b(c1["dist"], c2["dist"], n):
            if d < THETA - RES:
                w = {"kind": kind, "key": key, "ref": float(ref)}
                mk = [verdict(w, counts_dist(held[i], N, sd, n), n) for sd in MUT_SEEDS]
                of = [verdict(w, counts_dist(o["circ"][i], N, sd, n), n) for sd in ORIG_SEEDS[:3]]
                return {"control": {"context": i, "kind": kind, "key": key, "d": float(d), "ref": float(ref)},
                        "mutant_kills": mk.count("KILLED"), "original_failures": of.count("KILLED"),
                        "supported": mk.count("KILLED") < 12 and of.count("KILLED") == 0,
                        "circ_o": _qpy(o["circ"][i]), "circ_m": _qpy(held[i])}


if __name__ == "__main__":
    conf = json.load(open(HERE / "X2_CONFIRM.json"))
    res = {k: control(*k.split("|")) for k, v in conf.items() if v["supported"]}
    json.dump(res, open(OUT / "X2_CONTROL.json", "w"), indent=1)
    print({k: {x: v[x] for x in ("control", "mutant_kills", "original_failures", "supported")} for k, v in res.items()})
