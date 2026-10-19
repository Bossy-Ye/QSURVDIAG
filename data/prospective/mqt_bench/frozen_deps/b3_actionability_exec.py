"""B3 arm 9 -- execute the pre-registered interventions.

CL4: maximal widening.  CL3: calibrated bounded widening on the frozen W0-W4 ladder.
Both import their suite construction, guard, repetition and verdict rules from the
frozen e15 sources.  No assertion is replaced after seeing a result.
"""
import csv, json, os, sys, time
from itertools import combinations
from multiprocessing import Pool
import numpy as np
ROOT = "/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot"
sys.path.insert(0, ROOT); sys.path.insert(0, f"{ROOT}/cross_tool_stage/qutest")
sys.path.insert(0, f"{ROOT}/confirmatory")
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Statevector
import qutest_adapter as QA

O = "definitive_rerun_b3"
R = 12
L = qasm2.LEGACY_CUSTOM_INSTRUCTIONS
LEDGER = f"{O}/B3_ACTIONABILITY_CELLS.jsonl"

SUBS = {s["subject"]: s for s in
        json.load(open(f"{ROOT}/research_repair/e13_width_extension/E13_SUBJECTS.json"))}
HSUB = {s["subject"]: s for s in
        json.load(open(f"{ROOT}/research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json"))}
SAMP = {m["mutant_id"]: m for m in csv.DictReader(
    open(f"{ROOT}/research_repair/phase5_validation/s2_cohort/S2_SAMPLED_MUTANTS.csv"))}
MIDX = {f.name: f for f in (__import__("pathlib").Path(f"{ROOT}/data/qmutbench")).glob("*/*_mutant.qasm")}


def probs(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        getattr(qc, g["gate"])(*g.get("angles", []), *g["q"])
    return np.abs(np.asarray(Statevector.from_instruction(qc).data)) ** 2


def marg(p, n, q): return float(sum(p[i] for i in range(2 ** n) if (i >> q) & 1))
def obs_z(p, n, m): return float(sum(p[i] * (-1) ** bin(i & m).count("1") for i in range(2 ** n)))
def zassert(n, m, v):
    zs = " ".join(f"Z{i}" for i in range(n) if (m >> i) & 1)
    return f'//% expect observable "{zs}" ~= {round(v, 4)} atol={QA.ATOL}'


def maximal_suite(base, n):
    """e15_run.maximal_suite verbatim: every marginal, every basis-state probability,
    every Z-observable mask, references from the original at ATOL."""
    p = probs(base, n); a = []
    for q in range(n):
        a.append(QA.marginal_assertion(q, round(marg(p, n, q), 4)))
    for x in range(2 ** n):
        a.append(f'//% expect probability "{format(x, "0%db" % n)}" ~= {round(float(p[x]), 4)} atol={QA.ATOL}')
    for m in range(1, 2 ** n):
        a.append(zassert(n, m, obs_z(p, n, m)))
    return a


def ladder(base, n, outq):
    """e15b_bounded.ladder verbatim: W0..W4, each a superset of the last."""
    p = probs(base, n)
    w0 = [QA.marginal_assertion(q, round(marg(p, n, q), 4)) for q in outq]
    w1 = w0 + [QA.marginal_assertion(q, round(marg(p, n, q), 4)) for q in range(n) if q not in outq]
    def masks(w):
        out = []
        for c in combinations(range(n), w):
            m = 0
            for q in c: m |= 1 << q
            out.append(m)
        return out
    w2 = w1 + [zassert(n, m, obs_z(p, n, m)) for m in masks(2)]
    w3 = w2 + [zassert(n, m, obs_z(p, n, m)) for m in masks(3)]
    w4 = w3 + [f'//% expect probability "{format(x, "0%db" % n)}" ~= {round(float(p[x]), 4)} atol={QA.ATOL}'
               for x in range(2 ** n)]
    return [("W0", w0), ("W1", w1), ("W2", w2), ("W3", w3), ("W4", w4)]


def native(gates, n, a, reps=R):
    return [QA.run_qutest(QA.make_test(gates, n, a, seed=QA.SEED + r))[0] for r in range(reps)]


def resolve(case, arm, source):
    if source == "prospective_reference":
        m = SAMP[case]; s = HSUB[m["subject"]]
        return s["base_gates"], json.loads(m["mutated_gates"]), s["n"], s["output_register_qubits"]
    s = SUBS[[k for k in SUBS if case.startswith(k) or True and k == _sub_of(case)][0]]
    return None


def _sub_of(case):
    return case.split("#")[0]


def widths_case(case, sub):
    """widths-8-10 case: subject named by the scale manifest, mutant from the QASM,
    resolved by content hash exactly as e4_worker.py does."""
    s = SUBS[sub]
    bg = s["base_gates"]; base = json.loads(bg) if isinstance(bg, str) else bg
    import hashlib, glob
    man = {r["study_case_id"]: r for r in csv.DictReader(
        open(f"{ROOT}/REAL_STUDY_500_CASE_MANIFEST.csv"))}
    want = man[case]["raw_sha256"]; mp = None
    for d in ("holdout_cases", "sbs_cases", "qra_cases", "qra_cases_v1_1", "preflight_cases"):
        for q in glob.glob(f"{ROOT}/data/qmutbench/{d}/{case}_mutant.qasm"):
            if hashlib.sha256(open(q, "rb").read()).hexdigest() == want: mp = q; break
        if mp: break
    if mp is None: raise FileNotFoundError(f"mutant for {case} not resolvable by hash")
    qm = qasm2.load(mp, custom_instructions=L)
    mut = [{"gate": i.operation.name, "q": [qm.find_bit(b).index for b in i.qubits],
            **({"angles": [float(x) for x in i.operation.params]} if i.operation.params else {})}
           for i in qm.data if i.operation.name not in ("measure", "barrier")]
    return base, mut, s["n"], s["output_register_qubits"]


def run(rec):
    case, arm, source = rec["case"], rec["arm"], rec["source"]
    try:
        if source == "prospective_reference":
            m = SAMP[case]; s = HSUB[m["subject"]]
            bg = s["base_gates"]
            base = json.loads(bg) if isinstance(bg, str) else bg
            mut = json.loads(m["mutated_gates"]); n = int(m["n"]); outq = s["output_register_qubits"]
        else:
            base, mut, n, outq = widths_case(case, rec["subject"])

        if arm == "CL4":
            a = maximal_suite(base, n); rung = "MAXIMAL"
            # e15_run.py:104 verbatim -- the CL4 maximal-widening guard runs 3
            # repetitions, not R.  The CL3 ladder calibration below runs the full R.
            gv = native(base, n, a, reps=3)
            guard_fails = sum(1 for v in gv if v == "KILLED")
            if guard_fails:
                return {"case": case, "arm": arm, "source": source, "rung": rung,
                        "assertions": len(a), "guard_false_fails": guard_fails,
                        "outcome": "VOID_NOT_EVALUABLE", "reason": "original-program guard failed"}
        else:
            rungs = ladder(base, n, outq)
            chosen = None
            for name, a in rungs:
                if all(v == "SURVIVED" for v in native(base, n, a, reps=R)):
                    chosen = (name, a)
                else:
                    break
            if chosen is None:
                return {"case": case, "arm": arm, "source": source, "rung": None,
                        "assertions": 0, "guard_false_fails": R,
                        "outcome": "VOID_NOT_EVALUABLE", "reason": "original fails even W0"}
            rung, a = chosen; guard_fails = 0

        mv = native(mut, n, a, reps=R)
        kills = sum(1 for v in mv if v == "KILLED")
        inval = sum(1 for v in mv if v == "UNSUPPORTED")
        outcome = ("NOT_ELIGIBLE" if inval else "KILLED" if kills == R
                   else "SURVIVED" if kills == 0 else "UNSTABLE")
        return {"case": case, "arm": arm, "source": source, "rung": rung,
                "assertions": len(a), "guard_false_fails": guard_fails,
                "kills": kills, "reps": R, "invalid": inval, "outcome": outcome,
                "verdicts": mv}
    except Exception as e:
        return {"case": case, "arm": arm, "source": source,
                "outcome": "EXECUTION_FAILURE", "error": f"{type(e).__name__}: {e}"[:200]}


if __name__ == "__main__":
    pop = list(csv.DictReader(open(f"{O}/B3_ACTIONABILITY_POPULATION.csv")))
    done = set()
    if os.path.exists(LEDGER):
        for ln in open(LEDGER):
            try: done.add(json.loads(ln)["case"])
            except Exception: pass
    todo = [r for r in pop if r["case"] not in done]
    print(f"population {len(pop)}, to run {len(todo)}", flush=True)
    t0 = time.time()
    with open(LEDGER, "a") as fh, Pool(4) as pool:
        for i, rec in enumerate(pool.imap_unordered(run, todo), 1):
            fh.write(json.dumps(rec) + "\n"); fh.flush()
            print(f"  [{i}/{len(todo)}] {rec['case']:14} {rec['arm']:4} "
                  f"rung={str(rec.get('rung')):8} {rec['outcome']}", flush=True)
    print(f"\ndone in {(time.time()-t0)/60:.1f} min", flush=True)
