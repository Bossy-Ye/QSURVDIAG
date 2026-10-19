"""The executed method-2 rule T (Hellinger distance <= theta to the stored exact-evolution
distribution E) is not an instance of the declared universe U(P), whose Hellinger instance is referenced to P's own
ideal distribution. This script evaluates both predicates through QUTest on the histograms of the recorded seeds:
  T  : `distribution ref <E stored>`  + `distribution hellinger <= 0.05`   (re-run, to check reproduction)
  T' : `distribution ref <P ideal>`   + `distribution hellinger <= 0.05`   (the admitted instance of U(P))
QUTest applies one reference per test, so T and T' run as two tests at the same seed. QUTest's ideal backend is
seeded, so a test at a given seed sees the histogram the recorded run saw; the script checks that by requiring every
re-run T verdict to equal the archived one, and stops otherwise. The measured Hellinger value of every run is kept.
Usage: python -I reanalysis.py <package root> <run tree> <precalculated_data.json> <out dir> [workers]
"""
import csv, json, re, subprocess, sys, tempfile, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

PKG, TREE, REFP, OUT = (Path(a).resolve() for a in sys.argv[1:5])
WORKERS = int(sys.argv[5]) if len(sys.argv) > 5 else 4
src = open(PKG / "data/qedc/case_run.py").read().split("# ------------------------------------------------------------------ native runner")[0]
sys.argv = ["x", str(PKG), str(TREE), str(REFP), str(OUT)]
g = {"__name__": "reanalysis"}; exec(src, g)
QA, np = g["QA"], g["np"]
VAL = re.compile(r"hellinger = ([0-9.eE+-]+)")

def test_text(gates, n, ref, seed):
    A = ["//% expect distribution ref " + json.dumps(ref, separators=(",", ":")), f"//% expect distribution hellinger <= {g['THETA']}"]
    return QA.make_test(gates, n, A, g["N"], seed)
def run(job):
    key, gates, n, ref, seed = job
    with tempfile.NamedTemporaryFile("w", suffix=".qasm", delete=False) as f:
        f.write(test_text(gates, n, ref, seed)); p = f.name
    r = subprocess.run([QA.QUTEST, "run", "-v", p], capture_output=True, text=True, timeout=300)
    Path(p).unlink(missing_ok=True)
    out = r.stdout + r.stderr; summ = out.strip().splitlines()[-1] if out.strip() else ""
    v = "UNSUPPORTED" if "error" in summ else ("KILLED" if "failed" in summ else ("SURVIVED" if "passed" in summ else "UNSUPPORTED"))
    m = VAL.search(out)
    return key + (seed, v, float(m.group(1)) if m else None)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    arch = {}
    for r in csv.DictReader(open(PKG / "data/qedc/NATIVE_RUNS.csv")):
        if r["run"] in ("A_orig_cert", "A_mut_cert", "A_orig_val", "A_mut_val"):
            arch[(r["pair"], int(r["n"]), r["run"], int(r["seed"]))] = r["verdict"]
    jobs = []
    for n in g["WIDTHS"]:
        pP = np.abs(g["state"](g["PROG"]["P"](n), n)) ** 2
        refP = {format(x, f"0{n}b"): float(pP[x]) for x in range(2 ** n) if pP[x] > 1e-15}
        refE = g["refdist"](n)
        for label, a, b in g["PAIRS"]:
            for stage, prog, seeds in (("A_orig_cert", a, g["CERT_SEEDS"]), ("A_mut_cert", b, g["CERT_SEEDS"]),
                                     ("A_orig_val", a, g["VAL_ORIG"]), ("A_mut_val", b, g["VAL_MUT"])):
                for sd in seeds:
                    for pol, ref in (("T", refE), ("Tprime", refP)):
                        jobs.append(((label, n, stage, pol), g["PROG"][prog](n), n, ref, sd))
    t0 = time.time()
    with ProcessPoolExecutor(WORKERS) as ex: res = list(ex.map(run, jobs))
    wall = time.time() - t0
    mism = [(lab, n, run, sd, v, arch[(lab, n, run, sd)]) for (lab, n, run, pol, sd, v, h) in res if pol == "T" and arch[(lab, n, run, sd)] != v]
    with open(OUT / "REANALYSIS_RUNS.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["pair", "n", "run", "predicate", "seed", "verdict", "hellinger"])
        for row in res: w.writerow(row)
    json.dump({"executions": len(res), "wall_seconds": round(wall, 1), "T_reproduction_mismatches": mism},
              open(OUT / "REANALYSIS_SUMMARY.json", "w"), indent=1)
    print("executions", len(res), "wall", round(wall, 1), "T mismatches", len(mism))
    if mism: sys.exit("re-run T verdicts differ from the archived ones: the histograms are not reproduced")

if __name__ == "__main__":
    main()
