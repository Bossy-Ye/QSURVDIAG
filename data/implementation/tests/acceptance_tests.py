"""Environment acceptance tests for CONFIRMATORY_QUTEST_ENV.

Eight gates, all on original or synthetic programs.  No mutant is loaded, and no
mutant outcome decides acceptance.
"""
import sys, json, csv, time, inspect, hashlib
from pathlib import Path
import os
ROOT = Path(os.environ.get("QSD_ROOT", "."))
sys.path.insert(0, str(ROOT / "cross_tool_stage" / "qutest"))

RES, T0 = [], time.time()
def rec(gate, name, ok, detail=""):
    RES.append({"gate": gate, "check": name, "status": "PASS" if ok else "FAIL",
                "detail": str(detail)[:220]})

# ---- gate 1: import -------------------------------------------------------
try:
    import qutest
    from qutest.models import PragmaKind
    from qutest.parser import pragma as pragma_mod
    rec(1, "qutest imports", True, qutest.__file__)
except Exception as e:
    rec(1, "qutest imports", False, e); print(json.dumps(RES, indent=1)); sys.exit(1)

from qutest_adapter import make_test, run_qutest, _counts, marginal_p1, INNER_SHOTS, ATOL, SEED

# ---- gate 2: QUTest's own test suite, if shipped --------------------------
sp = Path(qutest.__file__).parent
shipped = list(sp.rglob("test_*.py")) + list(sp.rglob("tests"))
rec(2, "QUTest ships no in-package test suite (nothing to run)", len(shipped) == 0,
    f"{len(shipped)} candidate test paths inside the installed package")

# ---- gate 3: profile-recovery reconstruction ------------------------------
kinds = [k.name for k in PragmaKind]
expect_kinds = [k for k in kinds if k.startswith("EXPECT_")]
src = (sp / "parser" / "pragma.py").read_text()
has_fallthrough_raise = "unrecognized expect assertion" in src
ep = (sp.parent / "qutest-0.1.0.dist-info" / "entry_points.txt")
ep_txt = ep.read_text() if ep.exists() else ""
no_plugin_group = "console_scripts" in ep_txt and ep_txt.count("[") == 1
rec(3, "PragmaKind is a closed enum with 13 EXPECT_ members", len(expect_kinds) == 13,
    ",".join(expect_kinds))
rec(3, "parser raises on an unrecognized assertion (no fall-through)",
    has_fallthrough_raise, "parser/pragma.py")
rec(3, "entry_points declares only console_scripts (no plugin group)",
    no_plugin_group, ep_txt.strip().replace("\n", " "))

# ---- gate 4: assertion-family enumeration ---------------------------------
FAMILIES = {"EXPECT_OUTPUT", "EXPECT_DISTRIBUTION", "EXPECT_MARGINAL", "EXPECT_OBSERVABLE",
            "EXPECT_ENTROPY", "EXPECT_CORRELATION", "EXPECT_PROBABILITY",
            "EXPECT_FIDELITY", "EXPECT_ENTANGLED", "EXPECT_MOST_FREQUENT",
            "EXPECT_GATESET", "EXPECT_DEPTH"}
CERTIFYING = {"EXPECT_MARGINAL", "EXPECT_OBSERVABLE", "EXPECT_PROBABILITY",
              "EXPECT_ENTROPY", "EXPECT_DISTRIBUTION"}
rec(4, "12 assertion families recovered", FAMILIES <= set(expect_kinds), len(FAMILIES))
rec(4, "5 certifying families present", CERTIFYING <= FAMILIES, sorted(CERTIFYING))

# ---- gate 5: Section III / Fig. 1 minimal examples ------------------------
# The Fig. 1 CL4 pair: marginals agree at 0.5, <Z0Z1> separates 1.0 against 0.0.
BASE = [{"gate": "h", "q": [0]}, {"gate": "cx", "q": [0, 1]}]              # Bell
ALT  = [{"gate": "h", "q": [0]}, {"gate": "h", "q": [1]}]                  # product
for nm, gates, asrt, want in [
    ("marginal agrees on the base program", BASE,
     ["//% expect marginal m[0] p1 ~= 0.5 atol=0.05"], "SURVIVED"),
    ("marginal agrees on the alternative too", ALT,
     ["//% expect marginal m[0] p1 ~= 0.5 atol=0.05"], "SURVIVED"),
    ("<Z0Z1> holds on the base program", BASE,
     ['//% expect observable "Z0 Z1" ~= 1.0 atol=0.05'], "SURVIVED"),
    ("<Z0Z1> separates the alternative", ALT,
     ['//% expect observable "Z0 Z1" ~= 1.0 atol=0.05'], "KILLED"),
]:
    v, msg = run_qutest(make_test(gates, 2, asrt))
    rec(5, nm, v == want, f"{v} :: {msg}")

# ---- gates 6 and 7: the 20 primary originals under the frozen suite rules --
orig, outreg, nq = {}, {}, {}
for r in csv.DictReader(open(ROOT / "final_empirical_study/PROGRAM_MANIFEST.csv")):
    orig[r["program"]] = json.loads(r["base_gates"]); nq[r["program"]] = int(r["n"])
    outreg[r["program"]] = json.loads(r["output_register_qubits"])
for s in json.load(open(ROOT / "research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json")):
    bg = s["base_gates"]
    orig[s["subject"]] = json.loads(bg) if isinstance(bg, str) else bg
    nq[s["subject"]] = s["n"]; outreg[s["subject"]] = s["output_register_qubits"]
SUBJECTS = sorted(orig)
rec(6, "20 primary subjects resolved", len(SUBJECTS) == 20, len(SUBJECTS))

def zexp(counts, qs, shots=INNER_SHOTS):
    t = 0
    for k, v in counts.items():
        s = 1
        for q in qs:
            if k[len(k) - 1 - q] == "1":
                s = -s
        t += s * v
    return t / shots

def suites(sub):
    n, ors = nq[sub], outreg[sub]
    smin = [(q,) for q in ors]
    sfam = smin + [(ors[i], ors[i + 1]) for i in range(len(ors) - 1)]
    scov = [(q,) for q in range(n)]
    sboth = scov + [(i, i + 1) for i in range(n - 1)]
    return {"S_MIN": smin, "S_FAMILY": sfam, "S_COVER": scov, "S_BOTH": sboth}

def assertions(sub, terms):
    c = _counts(orig[sub], nq[sub], INNER_SHOTS, SEED)
    out = []
    for t in terms:
        if len(t) == 1:
            out.append(f"//% expect marginal m[{t[0]}] p1 ~= "
                       f"{round(marginal_p1(c, t[0], INNER_SHOTS), 4)} atol={ATOL}")
        else:
            out.append(f'//% expect observable "{" ".join(f"Z{q}" for q in t)}" ~= '
                       f'{round(zexp(c, list(t)), 4)} atol={ATOL}')
    return out

REPS = 12

def guard_cell(args):
    """One (subject, suite) guard.  Seeds are SEED + r, so parallelism is exact."""
    sub, sname, terms = args
    A = assertions(sub, terms)
    fails = sum(1 for r in range(REPS)
                if run_qutest(make_test(orig[sub], nq[sub], A, INNER_SHOTS, SEED + r))[0] == "KILLED")
    return {"subject": sub, "suite": sname, "n_assertions": len(A),
            "false_fails": fails, "reps": REPS,
            "guard": "CLEAN" if fails == 0 else "FALSE_FAIL",
            "rate": round(fails / REPS, 4)}

if __name__ == "__main__":
    from multiprocessing import Pool
    cells = [(sub, sn, tm) for sub in SUBJECTS for sn, tm in suites(sub).items()]
    with Pool(6) as pool:
        guard_rows = []
        for i, g in enumerate(pool.imap_unordered(guard_cell, cells), 1):
            guard_rows.append(g)
            print(f"  [{i}/{len(cells)}] {g['subject']}/{g['suite']} "
                  f"false-fails {g['false_fails']}/{REPS}", flush=True)
    guard_rows.sort(key=lambda g: (g["subject"], g["suite"]))
    smin_clean = all(g["false_fails"] == 0 for g in guard_rows if g["suite"] == "S_MIN")
    rec(6, "all 20 originals CLEAN under S_MIN", smin_clean,
        f"{sum(1 for g in guard_rows if g['suite']=='S_MIN' and g['false_fails']==0)}/20")
    allowed = 0.10                      # OB02 threshold, frozen
    within = [g for g in guard_rows if g["rate"] <= allowed]
    rec(7, "every (subject, suite) guard within the frozen OB02 threshold 0.10",
        len(within) == len(guard_rows),
        f"{len(within)}/{len(guard_rows)} cells; exceedances: " +
        ",".join(f"{g['subject']}/{g['suite']}={g['rate']}" for g in guard_rows if g["rate"] > allowed))

    # ---- gate 8: certificate / replay smoke test, synthetic only --------------
    sys.path.insert(0, str(Path(__file__).parent))
    from qsurvdiag_confirmatory import T, F, certify
    ALL = {f"OB{i:02d}": "satisfied" for i in range(1, 20)}
    a = certify({"R_C": F, "R_S": F, "R_O": F, "R_A": T, "R_T": F}, ALL)
    b = certify({"R_C": F, "R_S": F, "R_O": F, "R_A": T, "R_T": F}, ALL)
    rec(8, "synthetic certificate replays identically",
        a == b and a["report"] == "CL4", a["report"])
    h1 = hashlib.sha256(json.dumps(a, sort_keys=True, default=str).encode()).hexdigest()
    h2 = hashlib.sha256(json.dumps(b, sort_keys=True, default=str).encode()).hexdigest()
    rec(8, "replay hash is stable", h1 == h2, h1[:16])

    json.dump({"environment": "CONFIRMATORY_QUTEST_ENV",
               "elapsed_s": round(time.time() - T0, 1),
               "results": RES, "guard_ledger": guard_rows},
              open("ACCEPTANCE_TESTS.json", "w"), indent=1)
    with open("SUITE_GUARD_LEDGER.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(guard_rows[0].keys()))
        w.writeheader(); w.writerows(guard_rows)

    npass = sum(1 for r in RES if r["status"] == "PASS")
    for r in RES:
        print(f"  gate {r['gate']}  {r['status']}  {r['check']}")
    print(f"\nacceptance: {npass}/{len(RES)} checks passed in {time.time()-T0:.0f}s")
    sys.exit(0 if npass == len(RES) else 1)
