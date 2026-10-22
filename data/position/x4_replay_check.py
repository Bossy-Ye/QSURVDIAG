"""Fidelity check of the X4 driver: Stage 2 of the packaged diagnose on archived pairs of each population, compared
with the archived records (relations and candidate). No native run."""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import x4_run as X
import x4_select as SEL
V, A, Fz, QA = X.setup()
D = X.PKG / "data"
S = json.load(open(X.OUTD / "X4_SUBJECTS.json"))                  # from x4_select.py
cmp_ = {"R_C", "R_S", "R_O", "R_A", "R_T"}


def check(arm, rows, gates_of, key):
    bad, n_ok = [], 0
    for r in rows:
        s = S[r["subject"]]; mg = gates_of(r)
        rec = {"v1_report": "", "native_verdict": r["native_verdict"], "kills": r["kills"], "reps": r["reps"], "guard_ok": True}
        d = A.diagnose("chk", r[key], s["n"], s["prep"] + s["gates"], s["prep"] + mg, s["outreg"],
                       "unitary" if s["contract"] == "unitary" else "fixed", rec, [], {}, r["subject"])
        same = all(d[k] == r[k] for k in cmp_) and d.get("v2_candidate", "") == r.get("v2_candidate", "")
        n_ok += same
        if not same: bad.append((r[key], {k: (d.get(k), r.get(k)) for k in sorted(cmp_) | {"v2_candidate"} if d.get(k) != r.get(k)}))
    print(arm, "pairs", len(rows), "identical", n_ok, "differences", bad[:5])


# five other circuits
fin = [r for r in csv.DictReader(open(D / "certification/outcomes/R2V_FINAL_PRIMARY.csv")) if r["population"] == "prospective"]
s2 = {r["mutant_id"]: SEL._gl(r["mutated_gates"]) for r in csv.DictReader(open(D / "prospective/mqt_bench/frozen_deps/S2_GENERATED_MUTANTS.csv")) if r.get("mutated_gates")}
check("other", [r for r in fin if r["mutant_id"] in s2], lambda r: s2[r["mutant_id"]], "mutant_id")
# external: archived allocation regenerated from the pool by hash
ext = list(csv.DictReader(open(D / "certification/outcomes/R2V_FINAL_EXTERNAL.csv")))
alloc = {r["mutant_id"]: r for r in csv.DictReader(open(D / "external/cohort/EXTERNAL_ALLOCATION.csv"))}
pools = {}
def ext_gates(r):
    a = alloc[r["case"]]; sid = a["subject"]
    if sid not in pools: pools[sid] = {m["mutated_hash"]: m["mutated_gates"] for m in SEL.pool(S[sid], sid)}
    return pools[sid][a["mutated_hash"]]
for r in ext: r["subject"] = alloc[r["case"]]["subject"]
check("external", ext, ext_gates, "case")
