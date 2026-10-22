"""Final states of the executed contexts for the observation-limitation candidates of X2.

For each candidate (suite, program, mutant) and seed 15042, the mutant's run is captured again with its submitted
circuits kept, and each context's final state (before its measurements) is compared with the original's at the same
position, up to global phase. A candidate whose context states all agree has equal final states on every executed
context, so under the paper's relation order (state before observation) it is not observation-limited."""
import gzip, json, os, pickle, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import x2_capture as X
HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QSD_OUT", HERE.parents[1] / "output")) / "developer_suites"; OUT.mkdir(parents=True, exist_ok=True)


def body(qc):
    from qiskit import QuantumCircuit
    b = QuantumCircuit(qc.num_qubits)
    for ci in qc.data:
        if ci.operation.name in ("measure", "barrier"): continue
        b.append(ci.operation, [b.qubits[qc.find_bit(q).index] for q in ci.qubits])
    return b


def state(qc):
    from qiskit import transpile
    b = transpile(body(qc), X._sv_sim(), optimization_level=0); b.save_statevector()
    return np.asarray(X._RAW_RUN(X._sv_sim(), b).result().data()["statevector"])


def same_up_to_phase(a, b):
    i = int(np.argmax(np.abs(a)))
    if abs(b[i]) < 1e-12: return False
    ph = b[i] / a[i]
    return abs(abs(ph) - 1) < 1e-9 and float(np.max(np.abs(a * ph - b))) < 1e-9


def check(suite, program, version, seed=15042, ninp=20):
    from qiskit_aer.backends.aerbackend import AerBackend
    o = pickle.load(open(OUT / "cache" / f"{suite}_{program}_{seed}.pkl", "rb"))
    held = []; run0 = AerBackend.run
    def keep(self, c, *a, **k):
        held.extend(c if isinstance(c, (list, tuple)) else [c]); return run0(self, c, *a, **k)
    AerBackend.run = keep
    X.run_capture(suite, program, version, seed, ninp, 2500)
    AerBackend.run = run0
    assert len(held) == len(o["circ"])
    eq = [same_up_to_phase(state(a), state(b)) for a, b in zip(o["circ"], held)]
    return {"contexts": len(eq), "equal_state_contexts": sum(eq)}


def candidates():
    """Survivors with equal observations in every paired context and unequal returned circuits on some executed
    argument (OPERATIONAL.md, X2_STATE_RELATION)."""
    import collections
    runs = collections.defaultdict(list)
    for l in gzip.open(HERE / "X2_NATIVE_RUNS.jsonl.gz", "rt"):
        r = json.loads(l)
        if r["kind"] == "pair": runs[(r["suite"], r["program"], r["version"])].append(r)
    out = []
    for k, rs in sorted(runs.items()):
        if (len(rs) == 12 and all(r["passed"] for r in rs) and all(r["aligned"] and r.get("observation_equal") for r in rs)
                and not all(all(r["program_equal"].values()) for r in rs)):
            out.append(k)
    return out


if __name__ == "__main__":
    f = OUT / "X2_CONTEXT_STATES.json"
    res = json.load(open(f)) if f.exists() else {}
    for s, p, v in candidates():
        key = f"{s}|{p}|{v}"
        if key in res: continue
        per = {sd: check(s, p, v, sd) for sd in range(15042, 15054)}
        res[key] = {"contexts": sum(x["contexts"] for x in per.values()),
                    "equal_state_contexts": sum(x["equal_state_contexts"] for x in per.values())}
        res[key]["all_equal"] = res[key]["contexts"] == res[key]["equal_state_contexts"]
        json.dump(res, open(f, "w"), indent=1); print(key, res[key], flush=True)
