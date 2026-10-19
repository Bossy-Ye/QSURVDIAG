"""v2 reprocessing of the width set, the corpus frame and the external cohort, plus the
native-job list for every arm (V2_SPECIFICATION.md sections 3-9).

Each pair is rebuilt from the gate lists its recorded arm executed; analytic states are
computed from those same gate lists, so the native jobs and the analytic record describe
one object. Recomputed R_S and R_O decisions are checked against the recorded ledger
before any evidence status is written.
"""
import csv, glob, hashlib, json, os, sys
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Statevector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from r2v_lib import T, F, U, THETA, exists_above
from qsurvdiag_confirmatory import candidate
import r2_external as X

QSD = V.QSD; G = V.PA + "github/results/"
L = qasm2.LEGACY_CUSTOM_INSTRUCTIONS

def sv(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", [])
        (getattr(qc, g["gate"])(*a, *[int(i) for i in g["q"]]) if a else getattr(qc, g["gate"])(*[int(i) for i in g["q"]]))
    return np.asarray(Statevector.from_int(0, dims=(2,) * n).evolve(qc).data)

def qasm_gates(path):
    qc = qasm2.load(path, custom_instructions=L)
    return [{"gate": i.operation.name, "q": [qc.find_bit(b).index for b in i.qubits],
             **({"angles": [float(p) for p in i.operation.params]} if i.operation.params else {})}
            for i in qc.data if i.operation.name not in ("measure", "barrier")], qc.num_qubits

def unitary(gates, n):
    from qiskit.quantum_info import Operator
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", [])
        (getattr(qc, g["gate"])(*a, *[int(i) for i in g["q"]]) if a else getattr(qc, g["gate"])(*[int(i) for i in g["q"]]))
    return Operator(qc).data

def diagnose(arm, case, n, og, mg, suite_q, contract, rec, jobs, uc_cache=None, sub=None):
    """One pair under the v2 specification. rec: v1_report, native_verdict, kills, reps, guard_ok."""
    sa, sb = sv(og, n), sv(mg, n); pp, pm = np.abs(sa) ** 2, np.abs(sb) ** 2
    ms = abs(abs(np.vdot(sa, sb)) - 1.0); mo = float(np.max(np.abs(pp - pm)))
    if contract == "unitary":
        if sub not in uc_cache: uc_cache[sub] = unitary(og, n)
        mc = abs(abs(np.trace(uc_cache[sub].conj().T @ unitary(mg, n))) / 2 ** n - 1.0)
    else:
        mc = ms
    ordered, alld = V.ordered_universe(pp, pm, n)
    sdiffs = [abs(V.marg(pp, n, q) - V.marg(pm, n, q)) for q in suite_q]
    rel = {"R_C": V.eq_decision(mc), "R_S": V.eq_decision(ms), "R_O": V.eq_decision(mo),
           "R_A": exists_above(alld, THETA), "R_T": exists_above(sdiffs, THETA) if sdiffs else F}
    row = {"arm": arm, "case": case, "n": n, "v1_report": rec["v1_report"], "native_verdict": rec["native_verdict"],
           "kills": rec["kills"], "reps": rec["reps"], "contract": contract, "margin_contract": mc,
           "margin_state": ms, "margin_obs": mo, "universe_size": len(alld), **{k: V.tri_s(v) for k, v in rel.items()}}
    if rec["native_verdict"] == "KILLED":
        row["v2_report"] = "NA_KILLED"; return row
    cand, _, und = candidate(rel)
    sk = V.suite_keys_marginals(suite_q)
    w = V.select(ordered, sk, T) if cand == "CL4" else None
    c = V.select(ordered, sk, F) if cand == "CL4" else None
    dec = (w["d"] if w else None) if cand == "CL4" else (max(alld) if cand == "CL5" else None)
    grid = []
    for th in ("0.01", "0.025", "0.05", "0.1", "0.25", "0.5"):
        t = float(th); relt = dict(rel, R_A=exists_above(alld, t), R_T=exists_above(sdiffs, t) if sdiffs else F)
        grid.append((th, candidate(relt)[0] == cand))
    ok03 = int(rec["kills"]) in (0, int(rec["reps"]))
    ev = {"OB01": "satisfied", "OB02": "satisfied" if rec["guard_ok"] else "failed",
          "OB03": "satisfied" if ok03 else "failed", "OB04": "satisfied", "OB05": "satisfied",
          "OB06": "satisfied", "OB07": "satisfied", "OB08": "satisfied", "OB09": "satisfied",
          "OB10": "satisfied" if len(alld) == 2 ** (n + 1) + n + 3 else "failed",
          "OB11": "satisfied" if w is not None else "failed", "OB12": "satisfied", "OB14": "satisfied",
          "OB16": ("n/a" if cand not in ("CL4", "CL5") else
                   "satisfied" if dec is not None and abs(dec - THETA) > V.THRESHOLD_RESOLUTION else "failed"),
          "OB17": "satisfied", "OB18": "satisfied", "OB19": "satisfied" if V.spec_unchanged() else "failed",
          "OB13": "pending", "OB15": "pending"}
    row.update({"v2_candidate": cand or "", "undecided_relation": und or "",
                "w_kind": w["kind"] if w else "", "w_key": "" if not w or w["key"] is None else w["key"],
                "w_d": w["d"] if w else "", "c_kind": c["kind"] if c else "",
                "c_key": "" if not c or c["key"] is None else c["key"], "c_d": c["d"] if c else "",
                "decisive_d": "" if dec is None else dec, "grid_interval": V.grid_interval(grid) if cand else "",
                "ob13_source": "", **ev})
    if cand == "CL4" and ok03:
        for purpose, inst in (("OB13", w), ("OB15", c)):
            if inst is not None:
                jobs.append({"job_id": f"{arm}|{case}|{purpose}", "arm": arm, "case": case, "purpose": purpose,
                             "n": n, "orig_gates": og, "mut_gates": mg,
                             "lines": V.pragmas(inst, n, pp), "inst": {k: inst[k] for k in ("kind", "key", "d")}})
    return row

def width(jobs):
    man = {r["pair_id"]: r for r in csv.DictReader(open(f"{QSD}/confirmatory/E4_SCALE_MANIFEST.csv"))}
    subs = {s["subject"]: s for s in json.load(open(f"{QSD}/research_repair/e13_width_extension/E13_SUBJECTS.json"))}
    raw = {r["study_case_id"]: r for r in csv.DictReader(open(f"{QSD}/REAL_STUDY_500_CASE_MANIFEST.csv"))}
    paths = {}
    for d in ("sbs_cases", "preflight_cases", "qra_cases", "qra_cases_v1_1", "holdout_cases"):
        for p in glob.glob(f"{QSD}/data/qmutbench/{d}/*.qasm"): paths.setdefault(p.split("/")[-1], p)
    rows = []
    for r in csv.DictReader(open(G + "scale/B2_SCALE_FRESH.csv")):
        pid = r["pair_id"]; m = man[pid]; n = int(r["n"])
        if m["source"] == "width_set_E13":
            s = subs[m["original_id"]]; bg = s["base_gates"]
            og = json.loads(bg.replace("'", '"')) if isinstance(bg, str) else bg
            want = raw[pid]["raw_sha256"]; mp = None
            for d in ("holdout_cases", "sbs_cases", "qra_cases", "qra_cases_v1_1", "preflight_cases"):
                for q in glob.glob(f"{QSD}/data/qmutbench/{d}/{pid}_mutant.qasm"):
                    if hashlib.sha256(open(q, "rb").read()).hexdigest() == want: mp = q; break
                if mp: break
            mg, _ = qasm_gates(mp); outq = s["output_register_qubits"]
        else:
            og, _ = qasm_gates(paths[m["original_id"]]); mg, _ = qasm_gates(paths[m["mutant_id"]]); outq = list(range(n))
        rec = {"v1_report": r["report"], "native_verdict": r["native_verdict"], "kills": r["kills"],
               "reps": r["reps"], "guard_ok": r["original_guard_ok"] == "True"}
        row = diagnose("width", pid, n, og, mg, outq, "fixed", rec, jobs)
        assert (row["R_S"] == "true") == (r["R_S"] == "true") or row["R_S"] == "undecided", pid
        assert (row["R_O"] == "true") == (r["R_O"] == "true") or row["R_O"] == "undecided", pid
        rows.append(row)
    return rows

def corpus(jobs):
    rows = []
    for r in (json.loads(l) for l in open(G + "corpus/T2A_STRATIFIED_RAW.jsonl")):
        base = f"{QSD}/data/qmutbench/{r['case_set']}/{r['pair_id']}"
        og, n = qasm_gates(base + "_origin.qasm"); mg, _ = qasm_gates(base + "_mutant.qasm")
        rec = {"v1_report": r["diagnostic_outcome"], "native_verdict": r["native_verdict"], "kills": r["kills"],
               "reps": r["reps"], "guard_ok": bool(r["guard_ok"])}
        row = diagnose("corpus", f"{r['case_set']}/{r['pair_id']}", n, og, mg, list(range(n)), "fixed", rec, jobs)
        assert (row["R_S"] == "true") == bool(r["R_S"]) or row["R_S"] == "undecided", r["pair_id"]
        assert (row["R_O"] == "true") == bool(r["R_O"]) or row["R_O"] == "undecided", r["pair_id"]
        rows.append(row)
    return rows

def external(jobs):
    alloc = list(csv.DictReader(open(X.EXT + "/EXTERNAL_ALLOCATION.csv")))
    cert = {r["mutant_id"]: r for r in csv.DictReader(open(X.EXT + "/RUN_002/L5_CERTIFICATES.csv"))}
    guard = {g["subject"]: g for g in json.load(open(X.EXT + "/RUN_002/L1_ORIGINAL_GUARD.json"))}
    OUTREG = {"ParityPhase": list(range(6)), "Is2PowerPhase": list(range(6)), "LessThanPhase": list(range(5)),
              "DiagonalZHamiltonian": [0, 1, 2], "IsingEvolution": list(range(7)), "DraperAdder": [5, 6, 7, 8, 9],
              "AdderHamiltonianMixture": [5, 6, 7, 8, 9], "qft_n4": [0, 1, 2, 3], "deutsch_n2": [0]}
    FIXED = {"qft_n4", "deutsch_n2"}
    originals = {}
    for s in sorted({a["subject"] for a in alloc}):
        recon, n = set(), None
        for a in alloc:
            if a["subject"] != s or a["operator"] != "gate_insertion": continue
            gl, n = X.gates_of(os.path.join(X.EXT, a["mutant_path"]))
            k = int(a["location"].split("@")[1].split(":")[0]); recon.add(json.dumps(gl[:k] + gl[k + 1:], sort_keys=True))
        assert len(recon) == 1, s
        originals[s] = (json.loads(recon.pop()), n)
    rows, uc = [], {}
    for a in alloc:
        mid, s = a["mutant_id"], a["subject"]; og, n = originals[s]
        prep = X.prep_gates(*X.PAIRS[s], n) if s in X.PAIRS else []
        mg, _ = X.gates_of(os.path.join(X.EXT, a["mutant_path"]))
        c = cert[mid]
        rec = {"v1_report": c["diagnostic_outcome"], "native_verdict": c["native_verdict"],
               "kills": c["kills_recorded"], "reps": c["reps"], "guard_ok": guard[s]["OB02"] == "satisfied"}
        rows.append(diagnose("external", mid, n, prep + og, prep + mg, OUTREG[s],
                             "fixed" if s in FIXED else "unitary", rec, jobs, uc, s))
    return rows

def main():
    assert V.spec_unchanged()
    jobs = []
    out = {"WIDTH": width(jobs), "CORPUS": corpus(jobs), "EXTERNAL": external(jobs)}
    for name, rows in out.items():
        keys = sorted({k for r in rows for k in r})
        with open(os.path.join(V.HERE, f"R2V_REPORTS_{name}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    with open(os.path.join(V.HERE, "R2V_NATIVE_JOBS_ARMS.jsonl"), "w") as f:
        for j in jobs: f.write(json.dumps(j) + "\n")
    import collections
    for name, rows in out.items():
        print(name, collections.Counter((r["v1_report"], r.get("v2_candidate", r.get("v2_report"))) for r in rows))
    print("native jobs:", collections.Counter((j["arm"], j["purpose"]) for j in jobs))

if __name__ == "__main__":
    main()
