"""Reconstruct relations and run corrected QSurvDiag for every executed cell."""
import csv, json, numpy as np
from collections import Counter
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qsurvdiag_confirmatory import Tri, T, F, U, certify, empirical
import e1_relations as REL
from e1_lib import MUT, nq, orig
import os

def _resolve(candidates, what, env_hint):
    """First existing candidate, or a loud error naming what to set.

    Path resolution only: the file contents loaded are unchanged, and every
    shipped copy of each input is byte-identical.  Failing loudly matters here
    because an unresolved contract ledger would otherwise leave CONTRACT empty
    and silently default every subject to C_FIXED_INPUT_STATE.
    """
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError(
        f"{what} not found. Tried: {[c for c in candidates if c]}. Set {env_hint}.")

_MR = os.environ.get("MANUSCRIPT_ROOT", ".")
_QR = os.environ.get("QSD_ROOT", ".")
_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONSTRUCTION_MATRIX = _resolve(
    [f"{_MR}/data/construction_matrix.csv",
     f"{_PKG}/inputs/manifests/construction_matrix.csv",
     "data/construction_matrix.csv"],
    "construction_matrix.csv", "MANUSCRIPT_ROOT to the manuscript repository root")
S1_SUBJECTS = _resolve(
    [f"{_QR}/research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json",
     f"{_PKG}/inputs/manifests/S1_SUBJECTS.json",
     "inputs/manifests/S1_SUBJECTS.json"],
    "S1_SUBJECTS.json", "QSD_ROOT to the study tree, or run from the package root")

CONTRACT = {}
for r in csv.DictReader(open(CONSTRUCTION_MATRIX)):
    CONTRACT[r["program"]] = r["contract_id"] or "C_FIXED_INPUT_STATE"
for _s in json.load(open(S1_SUBJECTS)):
    CONTRACT[_s["subject"]] = _s["contract_id"]
UNITARY_CONTRACTS = {"C_UNITARY", "C_ARBITRARY_INPUT_UNITARY"}

def _unitary(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", [])
        (getattr(qc, g["gate"])(*a, *[int(x) for x in g["q"]]) if a
         else getattr(qc, g["gate"])(*[int(x) for x in g["q"]]))
    return Operator(qc).data

_uc = {}
def contract_equivalent(mutant_id):
    """R_C from the declared contract, computed exactly."""
    m = MUT[mutant_id]; sub = m["subject"]; n = nq[sub]
    if sub not in CONTRACT:
        raise KeyError(
            f"no declared contract for subject {sub!r}. Contracts come from "
            f"{CONSTRUCTION_MATRIX} and {S1_SUBJECTS}; a missing entry must not be "
            f"silently defaulted, because the default would decide R_C.")
    c = CONTRACT[sub]
    if c in UNITARY_CONTRACTS:
        if sub not in _uc: _uc[sub] = _unitary(orig[sub], n)
        um = _unitary(m["gates"], n)
        tr = abs(np.trace(_uc[sub].conj().T @ um)) / (2 ** n)
        return bool(abs(tr - 1.0) < 1e-9)
    sva, _, _ = REL._orig_cache(sub)
    return REL.state_equal(sva, REL._sv(m["gates"], n))

def evidence_for(pop, native, suite):
    """Same availability model as the frozen recertification, plus OB03 from the
    executed verdict.  Enumeration evidence exists for every executed cell because
    the universe is enumerated analytically here."""
    ev = {o: "satisfied" for o in
          ("OB01","OB02","OB04","OB05","OB06","OB07","OB08","OB09","OB10",
           "OB11","OB12","OB13","OB14","OB15","OB16","OB17","OB18","OB19")}
    ev["OB03"] = "satisfied" if native in ("SURVIVED", "KILLED") else "failed"
    return ev

def diagnose(mutant_id, suite, native, kills, reps):
    if native == "KILLED":
        return {"diagnostic_outcome": "NA_KILLED", "candidate": "", "required": "",
                "failed": "", "unknown": "", "unresolved_reason": ""}
    rc = contract_equivalent(mutant_id)
    rel = REL.relations(mutant_id, suite, rc)
    tri = {k: (T if rel[k] else F) for k in ("R_C","R_S","R_O","R_A","R_T")}
    res = certify(tri, evidence_for(None, native, suite),
                  empirical_verdict=empirical(kills, reps))
    return {"diagnostic_outcome": res["report"], "candidate": res["candidate"] or "",
            "required": ";".join(res["required"]), "failed": ";".join(res["failed"]),
            "unknown": ";".join(res["unknown"]),
            "unresolved_reason": res["unresolved_reason"] or "", **rel}

if __name__ == "__main__":
    BASE = json.load(open("E1_BASELINE_SMIN.json"))
    RECERT = {r["case"]: r for r in csv.DictReader(open("RECERTIFICATION.csv"))}
    rows = []
    # baseline S_MIN, from the archive
    for mid, b in BASE.items():
        if b["native_verdict"] == "KILLED":
            d = {"diagnostic_outcome": "NA_KILLED", "candidate": ""}
        else:
            rr = RECERT.get(mid)
            d = {"diagnostic_outcome": rr["corrected_report"] if rr else "Unresolved",
                 "candidate": rr["candidate"] if rr else ""}
        rc = contract_equivalent(mid)
        rel = REL.relations(mid, "S_MIN", rc)
        rows.append({"mutant_id": mid, "subject": b["subject"], "population": b["population"],
                     "suite": "S_MIN", "native_verdict": b["native_verdict"],
                     "kills_recorded": b["kills_recorded"], "reps": b["reps"],
                     "source": "archive", **d, **rel})
    # executed richer suites
    for ln in open("E1_RAW_EXECUTIONS.jsonl"):
        e = json.loads(ln)
        d = diagnose(e["mutant_id"], e["suite"], e["native_verdict"],
                     e["kills_recorded"], e["reps"])
        rows.append({"mutant_id": e["mutant_id"], "subject": e["subject"],
                     "population": e["population"], "suite": e["suite"],
                     "native_verdict": e["native_verdict"],
                     "kills_recorded": e["kills_recorded"], "reps": e["reps"],
                     "source": "executed", **d})
    keys = sorted({k for r in rows for k in r})
    with open("E1_DIAGNOSTIC_TABLE.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows: w.writerow(r)
    print("rows:", len(rows))
    for s in ("S_MIN","S_FAMILY","S_COVER","S_BOTH","S_SPEC"):
        sub = [r for r in rows if r["suite"] == s]
        if sub:
            print(f"  {s:9s} n={len(sub):4d} native={dict(Counter(r['native_verdict'] for r in sub))}"
                  f" diag={dict(Counter(r['diagnostic_outcome'] for r in sub))}")
