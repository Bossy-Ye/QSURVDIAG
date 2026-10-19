"""Pass 3C, Stage C: survival, diagnosis and certification under the frozen v2 procedure.

Reuses unchanged: r2v_lib (V2_SPECIFICATION.md, hash-checked), r2v_arms.diagnose,
r2v_lib.native_check (OB13/OB15, seeds 42-53, guards 42-44), r2v_finalize.finalize_row.
New code here only executes the frozen steps for this cohort:
  C0  parse trial without assertions (outcome-blind exclusion; no replacement),
  C1  baseline suite S_MIN (one Z marginal per output qubit, analytic reference from the
      original, rounded to 4 decimals) on the original (12 reps, guard ok iff <= 1 failure, i.e.
      false-failure rate <= 0.10) and on every mutant (12 reps); seeds 42-53, N = 2000,
  C2  v2 diagnosis (diagnose) and native OB13/OB15 jobs (native_check),
  C3  v2 report (finalize_row) and the B/B' comparison inputs.
Outputs go to records/stage_c/ and are hashed; Stage D must not start before they are committed.
--dry-run: runs every step on (original, original) self-pairs only; touches no mutant.
Environment: .venv-qutest-audit; env QSD_ROOT=/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot.
"""
import csv, hashlib, json, os, sys, time
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import deps; deps.verify()
REV2 = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/revision2"
os.chdir(REV2)                      # the revised-analysis modules are run from revision2/ (e1_lib reads SSPEC_PROVENANCE.json)
sys.path.insert(0, REV2)
import r2v_lib as V
import r2v_arms, r2v_finalize
QA = V.QA
assert V.spec_unchanged()

ARM = "mqt"
OUT = None
SEEDS = [42 + r for r in range(12)]

def smin_lines(s):
    return [QA.marginal_assertion(q, round(s["analytic_marginals_p1"][q], 4)) for q in s["outreg"]]

def run_suite(gates, n, lines, seeds):
    return [QA.run_qutest(QA.make_test(V.to_text(gates), n, lines, V.N_SHOTS, sd))[0] for sd in seeds]

def c0_c1(task):
    mid, s, mg = task
    n, prep = s["n"], s["prep"]
    trial = QA.run_qutest(QA.make_test(V.to_text(prep + mg), n, [], V.N_SHOTS, SEEDS[0]))[0]
    if trial == "UNSUPPORTED":
        return {"mutant_id": mid, "parse_trial": "UNSUPPORTED", "excluded": True}
    v = run_suite(prep + mg, n, smin_lines(s), SEEDS)
    k = sum(x == "KILLED" for x in v)
    return {"mutant_id": mid, "parse_trial": trial, "excluded": False, "kills": k, "reps": len(v),
            "unsupported": sum(x == "UNSUPPORTED" for x in v), "verdicts": ";".join(v),
            "native_verdict": "KILLED" if k == len(v) else ("SURVIVED" if k == 0 else "SPLIT")}

def native(job):
    t = time.time(); res = V.native_check(job["mut_gates"], job["orig_gates"], job["n"], job["lines"])
    return {"job_id": job["job_id"], "case": job["case"], "purpose": job["purpose"], "n": job["n"],
            "inst_kind": job["inst"]["kind"], "inst_key": job["inst"]["key"], "inst_d": job["inst"]["d"],
            **res, "seconds": round(time.time() - t, 2)}

def wcsv(name, rows):
    os.makedirs(OUT, exist_ok=True); p = os.path.join(OUT, name)
    keys = sorted({k for r in rows for k in r})
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def main(dry):
    global OUT
    OUT = os.path.join(ROOT, "records", "dry_run_stage_c" if dry else "stage_c")
    S = {s["subject"]: s for s in json.load(open(os.path.join(ROOT, "subjects", "SUBJECTS.json")))}
    if dry:
        tasks = [(f"{k}#self", s, s["body"]) for k, s in S.items()]
    else:
        man = list(csv.DictReader(open(os.path.join(ROOT, "population", "MUTANT_MANIFEST.csv"))))
        tasks = [(r["mutant_id"], S[r["subject"]], json.load(open(os.path.join(ROOT, "population", r["gates_path"]))))
                 for r in man]
    W = int(os.environ.get("WORKERS", "6"))
    # C1 original guards
    guards = {}
    for k, s in S.items():
        v = run_suite(s["prep"] + s["body"], s["n"], smin_lines(s), SEEDS)
        guards[k] = {"subject": k, "fails": sum(x == "KILLED" for x in v), "verdicts": ";".join(v),
                     "guard_ok": sum(x == "KILLED" for x in v) <= 1}
    with Pool(W) as p: base = p.map(c0_c1, tasks)
    # C2 diagnosis
    rows, jobs, uc = [], [], {}
    bymid = {b["mutant_id"]: b for b in base}
    for mid, s, mg in tasks:
        b = bymid[mid]
        if b["excluded"]: continue
        rec = {"v1_report": "n/a (prospective)", "native_verdict": b["native_verdict"], "kills": b["kills"],
               "reps": b["reps"], "guard_ok": guards[s["subject"]]["guard_ok"]}
        row = r2v_arms.diagnose(ARM, mid, s["n"], s["prep"] + s["body"], s["prep"] + mg, s["outreg"],
                                s["contract"], rec, jobs, uc, s["subject"])
        row["subject"], row["family"] = s["subject"], s["family"]
        rows.append(row)
    with Pool(W) as p: nat_rows = p.map(native, jobs)
    nat = {r["job_id"]: r for r in nat_rows}
    final = [{**r, **r2v_finalize.finalize_row(ARM, r["case"], r, nat)} for r in rows]
    hashes = {"C1_GUARDS.csv": wcsv("C1_GUARDS.csv", list(guards.values())),
              "C1_BASELINE.csv": wcsv("C1_BASELINE.csv", base),
              "C2_NATIVE.csv": wcsv("C2_NATIVE.csv", nat_rows) if nat_rows else None,
              "C3_REPORTS.csv": wcsv("C3_REPORTS.csv", final)}
    json.dump({"dry_run": dry, "hashes": hashes, "spec_sha": V.SPEC_SHA},
              open(os.path.join(OUT, "STAGE_C_RECORD.json"), "w"), indent=1)
    import collections
    print("guards", {k: g["guard_ok"] for k, g in guards.items()})
    print("reports", collections.Counter(r["v2_report"] for r in final))

if __name__ == "__main__":
    main("--dry-run" in sys.argv)
