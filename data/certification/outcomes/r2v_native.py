"""v2 native evidence runs (V2_SPECIFICATION.md section 9): OB13 and OB15 for every CL4
certificate without a qualifying recorded run.

Jobs come from R2V_REPORTS_PRIMARY.csv (built here from the frozen gate lists) and
R2V_NATIVE_JOBS_ARMS.jsonl (width, corpus, external). Each job runs the single assertion
alone: a guard on the original at seeds 42-44, then the mutant at seeds 42-53, N = 2000.
Results append to R2V_NATIVE.csv; a job already recorded there is skipped, so the run is
resumable. Nothing outside revision2/ is written.
"""
import csv, json, os, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V

OUT = os.path.join(V.HERE, "R2V_NATIVE.csv")
FIELDS = ["job_id", "arm", "case", "purpose", "n", "inst_kind", "inst_key", "inst_d", "lines",
          "guard_fails", "guard_unsupported", "kills", "unsupported", "guard_verdicts", "verdicts", "seconds"]

def primary_jobs():
    from e1_lib import MUT, orig, nq
    import e1_relations as REL
    import numpy as np
    jobs = []
    for r in csv.DictReader(open(os.path.join(V.HERE, "R2V_REPORTS_PRIMARY.csv"))):
        if r.get("v2_candidate") != "CL4" or r["OB03"] != "satisfied": continue
        mid = r["mutant_id"]; m = MUT[mid]; sub = m["subject"]; n = nq[sub]
        pp = np.abs(REL._sv(orig[sub], n)) ** 2
        for purpose, kind, key, d in (("OB13", r["w_kind"], r["w_key"], r["w_d"]), ("OB15", r["c_kind"], r["c_key"], r["c_d"])):
            if purpose == "OB13" and r["OB13"] != "pending": continue
            if not kind: continue
            inst = {"kind": kind, "key": None if key == "" else int(key), "d": float(d),
                    "ref": None}
            # reference from the original, exactly as r2v_lib.ordered_universe computes it
            if kind == "marginal": inst["ref"] = V.marg(pp, n, inst["key"])
            elif kind == "zmask": inst["ref"] = V.zexp(pp, n, inst["key"])
            elif kind == "prob": inst["ref"] = float(pp[inst["key"]])
            elif kind == "entropy": inst["ref"] = V.shannon_bits(pp)
            jobs.append({"job_id": f"primary|{mid}|{purpose}", "arm": "primary", "case": mid, "purpose": purpose,
                         "n": n, "orig_gates": orig[sub], "mut_gates": m["gates"],
                         "lines": V.pragmas(inst, n, pp), "inst": {"kind": kind, "key": inst["key"], "d": inst["d"]}})
    return jobs

def run(job):
    t = time.time()
    res = V.native_check(job["mut_gates"], job["orig_gates"], job["n"], job["lines"])
    return {"job_id": job["job_id"], "arm": job["arm"], "case": job["case"], "purpose": job["purpose"], "n": job["n"],
            "inst_kind": job["inst"]["kind"], "inst_key": job["inst"]["key"], "inst_d": job["inst"]["d"],
            "lines": " | ".join(l if len(l) < 200 else l[:200] + "..." for l in job["lines"]), **res,
            "seconds": round(time.time() - t, 2)}

def main():
    assert V.spec_unchanged()
    jobs = primary_jobs() + [json.loads(l) for l in open(os.path.join(V.HERE, "R2V_NATIVE_JOBS_ARMS.jsonl"))]
    done = set()
    if os.path.exists(OUT):
        done = {r["job_id"] for r in csv.DictReader(open(OUT))}
    todo = [j for j in jobs if j["job_id"] not in done]
    print(f"jobs {len(jobs)}, done {len(done)}, to run {len(todo)}", flush=True)
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f, Pool(int(os.environ.get("R2V_WORKERS", "6"))) as pool:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        for k, row in enumerate(pool.imap_unordered(run, todo), 1):
            w.writerow(row); f.flush()
            if k % 20 == 0 or k == len(todo):
                print(f"[{k}/{len(todo)}] {row['job_id']} kills={row['kills']} guard={row['guard_fails']} {row['seconds']}s", flush=True)

if __name__ == "__main__":
    main()
