"""Pass 3C, Stage D: independent native validation with fresh, pre-fixed seeds.

Runs only after the Stage-C records are committed (checked below). Separate runner, separate
records (records/stage_d/). No Stage-C run is reused. Certification outcomes (Stage C) and
validation outcomes (Stage D) are recorded separately and only cross-tabulated in the analysis.
Validity criterion used throughout: the existing OB02 rule, original false-failure rate <= 0.10,
i.e. at most 1 failure in 12 runs. No other threshold is introduced.

D1  Suite-omission repair, for every v2 CL4 candidate with stable survival (certified or not).
    Repaired suite = S_MIN + w* (w* as named in Stage C; analytic reference from the original,
    rounded as the adapter rounds).
      mutant   : 12 runs, seeds 2042-2053  -> k = kills
      original : 12 runs, seeds 6042-6053  -> f = false failures (independent of the mutant seeds)
    Outcome (exactly one):
      void                    any UNSUPPORTED or execution error
      original_false_failure  f >= 2: the repaired suite is not a valid test on fresh seeds
      supported_repair        f <= 1 and k = 12
      kill_failure            f <= 1 and k < 12
    k and f are reported with exact (Clopper-Pearson) 95% intervals.

D2  Observation limitation, for every v2 CL3 candidate with stable survival: an implementation-
    consistency check, NOT a statistical test of distributional equivalence (equivalence of the
    observation is established analytically, R_O within 1e-10, and is not re-decided here).
      calibration : bounded ladder W0-W4 (E15b rule, functions extracted unchanged from the frozen
                    B3 runner) on the ORIGINAL, seeds 3042-3053; operative rung = highest rung on
                    which the original survives all 12 (void if W0 fails)
      validity    : original at the operative rung, seeds 5042-5053 -> f; valid iff f <= 1
      paired      : mutant at the SAME seeds 5042-5053 -> per-seed verdict agreement a/12 with the
                    original (equal observation vectors and equal seeds give equal samples, up to
                    floating-point boundary effects)
      independent : mutant at seeds 4042-4053 -> k; reported with its interval, never used to classify
    Outcome (exactly one):
      void                          any UNSUPPORTED or execution error, or W0 fails calibration
      suite_invalid_on_fresh_seeds  f >= 2: not counted as a successful validation; the
                                    structural diagnosis is unchanged and reported separately
      implementation_inconsistent   valid suite and a < 12: native discrepancy, reported in full
      consistent                    valid suite and a = 12
Environment: .venv-qutest-audit; QSD_ROOT set. --dry-run: original self-pairs (and, for D2, an
original-only equivalent variant) from the dry-run Stage C only.
"""
import ast, csv, hashlib, json, os, subprocess, sys, time
from itertools import combinations
from multiprocessing import Pool
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import deps; deps.verify()
REV2 = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/revision2"
os.chdir(REV2)                      # the revised-analysis modules are run from revision2/ (e1_lib reads SSPEC_PROVENANCE.json)
sys.path.insert(0, REV2)
import r2v_lib as V
QA = V.QA
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from scipy.stats import beta

D1_MUT = [2042 + r for r in range(12)]; D1_ORIG = [6042 + r for r in range(12)]
D2_CAL = [3042 + r for r in range(12)]; D2_IND = [4042 + r for r in range(12)]; D2_PAIR = [5042 + r for r in range(12)]
VALID_MAX_FAILS = 1                  # OB02: false-failure rate <= 0.10 over 12 runs

# ---- E15b ladder, extracted unchanged from the frozen B3 runner
B3 = os.path.join(ROOT, "frozen_deps", "b3_actionability_exec.py")
_src = open(B3).read(); _t = ast.parse(_src); NS = {"QA": QA, "np": np, "combinations": combinations,
                                                  "QuantumCircuit": QuantumCircuit, "Statevector": Statevector}
for name in ("probs", "marg", "obs_z", "zassert", "ladder"):
    f = next(n for n in _t.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[f], type_ignores=[]), B3, "exec"), NS)
ladder = NS["ladder"]

def cp95(k, n):
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return [round(lo, 4), round(hi, 4)]

def committed(src):
    d = os.path.join(ROOT, "records", src)
    r = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", d], capture_output=True, text=True)
    t = subprocess.run(["git", "-C", ROOT, "ls-files", "--", d], capture_output=True, text=True)
    return r.stdout.strip() == "" and t.stdout.strip() != ""

def runs(gates, n, lines, seeds):
    return [QA.run_qutest(QA.make_test(V.to_text(gates), n, lines, V.N_SHOTS, sd))[0] for sd in seeds]

def _qc(gl, n):
    qc = QuantumCircuit(n)
    for x in gl: getattr(qc, x["gate"])(*x.get("angles", []), *x["q"])
    return qc

def ref_of(kind, key, pp, n):
    if kind == "marginal": return V.marg(pp, n, key)
    if kind == "zmask": return V.zexp(pp, n, key)
    if kind == "prob": return float(pp[key])
    if kind == "entropy": return V.shannon_bits(pp)
    return None

def d1(task):
    case, s, mg, kind, key, d = task; n = s["n"]; og = s["prep"] + s["body"]
    pp = np.abs(np.asarray(Statevector(_qc(og, n)).data)) ** 2
    inst = {"kind": kind, "key": key, "d": d, "ref": ref_of(kind, key, pp, n)}
    lines = [QA.marginal_assertion(q, round(s["analytic_marginals_p1"][q], 4)) for q in s["outreg"]] + V.pragmas(inst, n, pp)
    t = time.time(); m = runs(s["prep"] + mg, n, lines, D1_MUT); o = runs(og, n, lines, D1_ORIG)
    k = sum(v == "KILLED" for v in m); f = sum(v == "KILLED" for v in o)
    if "UNSUPPORTED" in m + o: out = "void"
    elif f > VALID_MAX_FAILS: out = "original_false_failure"
    elif k == 12: out = "supported_repair"
    else: out = "kill_failure"
    return {"case": case, "w_kind": kind, "w_key": key, "w_d": d, "mutant_kills": k, "mutant_kills_ci95": json.dumps(cp95(k, 12)),
            "original_false_failures": f, "original_ff_ci95": json.dumps(cp95(f, 12)),
            "mutant_verdicts": ";".join(m), "original_verdicts": ";".join(o), "outcome": out,
            "seconds": round(time.time() - t, 1)}

def d2(task):
    case, s, mg = task; n = s["n"]; og = s["prep"] + s["body"]
    rungs = ladder(og, n, s["outreg"]); op = None; cal = {}; bad = False
    for name, a in rungs:
        v = runs(og, n, a, D2_CAL); cal[name] = sum(x == "KILLED" for x in v); bad |= "UNSUPPORTED" in v
        if cal[name] == 0 and "UNSUPPORTED" not in v: op = (name, a)
    if op is None or bad:
        return {"case": case, "operative_rung": op[0] if op else "", "calibration": json.dumps(cal), "outcome": "void"}
    o = runs(og, n, op[1], D2_PAIR); mp = runs(s["prep"] + mg, n, op[1], D2_PAIR); mi = runs(s["prep"] + mg, n, op[1], D2_IND)
    f = sum(v == "KILLED" for v in o); a = sum(x == y for x, y in zip(o, mp)); k = sum(v == "KILLED" for v in mi)
    if "UNSUPPORTED" in o + mp + mi: out = "void"
    elif f > VALID_MAX_FAILS: out = "suite_invalid_on_fresh_seeds"
    elif a < 12: out = "implementation_inconsistent"
    else: out = "consistent"
    return {"case": case, "operative_rung": op[0], "assertions": len(op[1]), "calibration": json.dumps(cal),
            "original_false_failures": f, "original_ff_ci95": json.dumps(cp95(f, 12)),
            "paired_agreement": a, "mutant_paired_kills": sum(v == "KILLED" for v in mp),
            "mutant_independent_kills": k, "mutant_independent_ci95": json.dumps(cp95(k, 12)),
            "original_verdicts": ";".join(o), "mutant_paired_verdicts": ";".join(mp),
            "mutant_independent_verdicts": ";".join(mi), "outcome": out}

def main(dry):
    src = "dry_run_stage_c" if dry else "stage_c"
    if not dry and not committed(src):
        raise SystemExit("Stage-C records are not committed and clean: Stage D must not start")
    S = {s["subject"]: s for s in json.load(open(os.path.join(ROOT, "subjects", "SUBJECTS.json")))}
    rows = list(csv.DictReader(open(os.path.join(ROOT, "records", src, "C3_REPORTS.csv"))))
    if dry:
        gl = {f"{k}#self": s["body"] for k, s in S.items()}
        t1 = [(c, S[c.split("#")[0]], gl[c], "marginal", 0, 0.0) for c in gl]
        # D2 dry run: the original against an original-only equivalent variant (two trailing Z gates)
        t2 = [(f"{k}#zz", S[k], S[k]["body"] + [{"gate": "z", "q": [0]}, {"gate": "z", "q": [0]}]) for k in S]
    else:
        man = {r["mutant_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "population", "MUTANT_MANIFEST.csv")))}
        gl = {k: json.load(open(os.path.join(ROOT, "population", r["gates_path"]))) for k, r in man.items()}
        t1 = [(r["case"], S[r["subject"]], gl[r["case"]], r["w_kind"], None if r["w_key"] == "" else int(r["w_key"]),
               float(r["w_d"])) for r in rows if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied" and r["w_kind"]]
        t2 = [(r["case"], S[r["subject"]], gl[r["case"]]) for r in rows
              if r.get("v2_candidate") == "CL3" and r.get("OB03") == "satisfied"]
    W = int(os.environ.get("WORKERS", "6"))
    with Pool(W) as p: r1 = p.map(d1, t1); r2 = p.map(d2, t2)
    out = os.path.join(ROOT, "records", "dry_run_stage_d" if dry else "stage_d"); os.makedirs(out, exist_ok=True)
    hs = {}
    for name, rr in (("D1_REPAIR.csv", r1), ("D2_OBSERVATION.csv", r2)):
        if not rr: continue
        p = os.path.join(out, name)
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted({k for r in rr for k in r})); w.writeheader(); w.writerows(rr)
        hs[name] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    json.dump({"dry_run": dry, "hashes": hs, "valid_max_fails": VALID_MAX_FAILS,
               "seeds": {"D1_mut": D1_MUT, "D1_orig": D1_ORIG, "D2_cal": D2_CAL, "D2_pair": D2_PAIR, "D2_ind": D2_IND}},
              open(os.path.join(out, "STAGE_D_RECORD.json"), "w"), indent=1)
    import collections
    print("D1", collections.Counter(r["outcome"] for r in r1), "D2", collections.Counter(r["outcome"] for r in r2))
    for r in r2: print({k: r[k] for k in r if "verdicts" not in k})

if __name__ == "__main__":
    main("--dry-run" in sys.argv)
