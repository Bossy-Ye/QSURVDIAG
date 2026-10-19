"""PD-1 verification (Pass 3B, before Freeze A). Enumeration only: no allocation, no execution.

Compares the historical enumerator (rq3_feasibility_gate.core, QUBIT_LIMIT = 10) with the
cohort copy (rq3_cohort.core, QUBIT_LIMIT = 14; the only difference, see PD1_QUBIT_LIMIT.diff)
on the four frozen subjects:
  * for n <= 10 the full ordered candidate pools and ineligible lists must be identical;
  * for rg_mult_12 the historical pool is empty (cap) and the cohort pool must offer at least
    30 distinct candidates; per-stratum availability is recorded (no mutant is picked).
Writes cohort_enumerator/PD1_VERIFICATION.json.
"""
import collections, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); PILOT = os.path.dirname(ROOT)
sys.path.insert(0, PILOT); sys.path.insert(0, HERE)
from rq3_feasibility_gate.core import mutants as HIST
from rq3_cohort.core import mutants as COH
OPS = ("gate_deletion", "gate_insertion", "gate_replacement")
CLS = ("local_basis_amplitude", "phase_parameterized", "entangling_controlled")

def digest(pool):
    rows = [(m["op"], m["gate_class"], m["spec"], m["mutated_hash"]) for m in pool]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest(), len(rows)

def main():
    S = json.load(open(os.path.join(ROOT, "subjects", "SUBJECTS.json"))); out = {}
    for s in S:
        n, body = s["n"], s["body"]
        hp, hi = HIST.complete_pool(body, n, s["subject"]); cp, ci = COH.complete_pool(body, n, s["subject"])
        dh, dc = digest(hp), digest(cp)
        dedup = {m["mutated_hash"]: m for m in cp}
        avail = collections.Counter((m["op"], m["gate_class"]) for m in dedup.values())
        out[s["subject"]] = {"n": n, "historical_pool": dh[1], "historical_ineligible": len(hi),
                             "cohort_pool": dc[1], "cohort_ineligible": len(ci),
                             "pool_identical": dh == dc and digest(hi) == digest(ci),
                             "cohort_distinct_candidates": len(dedup),
                             "cohort_strata_available": {f"{o}/{c}": avail[(o, c)] for o in OPS for c in CLS}}
        print(s["subject"], out[s["subject"]]["historical_pool"], out[s["subject"]]["cohort_pool"],
              out[s["subject"]]["pool_identical"], len(dedup), flush=True)
    ok = (all(v["pool_identical"] for k, v in out.items() if v["n"] <= 10)
          and out["rg_mult_12"]["historical_pool"] == 0 and out["rg_mult_12"]["cohort_distinct_candidates"] >= 30)
    out["PASS"] = ok
    json.dump(out, open(os.path.join(HERE, "PD1_VERIFICATION.json"), "w"), indent=1)
    print("PD-1 verification:", ok)
    if not ok: raise SystemExit("PD-1 verification failed")

if __name__ == "__main__":
    main()
