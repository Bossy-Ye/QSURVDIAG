"""OPERATIONAL.md (X2_OPERATIONAL, item 5): native confirmation of every suite-omission candidate among the stable survivors.

The witness context (as submitted by the suite in the first run with a witness) runs alone at 2,000 shots on the
mutant (seeds 15042-15053) and the original (seeds 16042-16053); the witness is evaluated on the measured bits with
the original's ideal value rounded to 4 decimals as reference and tolerance 0.05 (distances: at most 0.05 from the
original's ideal distribution). Supported: 12 of 12 mutant kills and at most 1 of 12 original failures.
"""
import base64, collections, gzip, io, json, os, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from x2_run import _walsh

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", HERE.parents[1] / "output")) / "developer_suites"; OUT.mkdir(parents=True, exist_ok=True)
N, THETA = 2000, 0.05
MUT_SEEDS = list(range(15042, 15054)); ORIG_SEEDS = list(range(16042, 16054))


def load(b64):
    from qiskit import qpy
    return qpy.load(io.BytesIO(base64.b64decode(b64)))[0]


def stat(kind, key, dist, n):
    idx = np.arange(len(dist))
    if kind == "marginal": return dist[((idx >> key) & 1) == 1].sum()
    if kind == "zmask": return _walsh(dist)[key]
    if kind == "prob": return dist[key]
    if kind == "entropy": q = dist[dist > 0]; return float(-(q * np.log2(q)).sum())
    raise ValueError(kind)


def counts_dist(qc, shots, seed, n_meas):
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    sim = AerSimulator(seed_simulator=seed)
    c = sim.run(transpile(qc, sim, optimization_level=0), shots=shots).result().get_counts()
    meas = sorted([(qc.find_bit(ci.qubits[0]).index, qc.find_bit(ci.clbits[0]).index) for ci in qc.data if ci.operation.name == "measure"], key=lambda t: t[1])
    clb = [cb for _, cb in meas]
    d = np.zeros(2 ** n_meas)
    for k, v in c.items():
        bits = k.replace(" ", "")[::-1]
        x = sum(int(bits[cb]) << j for j, cb in enumerate(clb))
        d[x] += v
    return d / shots


def verdict(w, dist, n):
    if w["kind"] in ("tvd", "hellinger", "kl"):
        ref = np.array(w["ref_dist"]); p = dist
        val = {"tvd": 0.5 * np.abs(p - ref).sum(), "hellinger": np.sqrt(0.5 * np.sum((np.sqrt(p) - np.sqrt(ref)) ** 2)),
               "kl": float(np.sum(np.clip(p, 1e-12, None) * np.log(np.clip(p, 1e-12, None) / np.clip(ref, 1e-12, None))))}[w["kind"]]
        return "KILLED" if val > THETA else "SURVIVED"
    return "KILLED" if abs(stat(w["kind"], w["key"], dist, n) - round(w["ref"], 4)) > THETA else "SURVIVED"


if __name__ == "__main__":
    runs = [json.loads(l) for l in gzip.open(HERE / "X2_NATIVE_RUNS.jsonl.gz", "rt")]
    g = collections.defaultdict(list)
    for r in runs:
        if r["kind"] == "pair": g[(r["suite"], r["program"], r["version"])].append(r)
    res = {}
    for (s, p, v), rs in sorted(g.items()):
        if sum(not r["passed"] for r in rs) != 0 or not all(r["aligned"] for r in rs): continue
        if all(r["observation_equal"] for r in rs): continue
        w = next((r["witness"] for r in rs if r["witness"]), None)
        if w is None: continue
        co, cm = load(w["circ_o"]), load(w["circ_m"]); n = w["n_measured"]
        mk = [verdict(w, counts_dist(cm, N, sd, n), n) for sd in MUT_SEEDS]
        of = [verdict(w, counts_dist(co, N, sd, n), n) for sd in ORIG_SEEDS]
        res[f"{s}|{p}|{v}"] = {"witness": {k: w[k] for k in ("context", "kind", "key", "d", "ref")},
                               "mutant_kills": mk.count("KILLED"), "original_failures": of.count("KILLED"),
                               "supported": mk.count("KILLED") == 12 and of.count("KILLED") <= 1}
    json.dump(res, open(OUT / "X2_CONFIRM.json", "w"), indent=1)
    print(len(res), "candidates;", sum(x["supported"] for x in res.values()), "supported")
