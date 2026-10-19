"""Shared Experiment-1 execution library.  Frozen settings only."""
import csv, json, os, sys
from pathlib import Path
ROOT = Path(os.environ.get("QSD_ROOT", "."))
OV = Path(os.environ.get("MANUSCRIPT_ROOT", "."))
sys.path.insert(0, str(ROOT / "cross_tool_stage" / "qutest"))
from qutest_adapter import make_test, run_qutest, _counts, marginal_p1, INNER_SHOTS, ATOL, SEED

REPS = 12
assert INNER_SHOTS == 2000 and ATOL == 0.05 and SEED == 42

orig, outreg, nq, subjfam = {}, {}, {}, {}
for r in csv.DictReader(open(ROOT / "final_empirical_study/PROGRAM_MANIFEST.csv")):
    orig[r["program"]] = json.loads(r["base_gates"]); nq[r["program"]] = int(r["n"])
    outreg[r["program"]] = json.loads(r["output_register_qubits"]); subjfam[r["program"]] = r["family"]
for s in json.load(open(ROOT / "research_repair/phase5_validation/s1_materialization/S1_SUBJECTS.json")):
    bg = s["base_gates"]
    orig[s["subject"]] = json.loads(bg) if isinstance(bg, str) else bg
    nq[s["subject"]] = s["n"]; outreg[s["subject"]] = s["output_register_qubits"]
    subjfam[s["subject"]] = s["subject"].split("_")[0]

MUT = {}
for r in csv.DictReader(open(ROOT / "final_empirical_study/MUTANT_POPULATION.csv")):
    MUT[r["mutant_id"]] = {"subject": r["program"], "gates": json.loads(r["mutated_gates"]),
                           "population": "construction", "order": len(MUT)}
for r in csv.DictReader(open(ROOT / "research_repair/phase5_validation/s2_cohort/S2_GENERATED_MUTANTS.csv")):
    g = r.get("mutated_gates") or r.get("gates")
    if not g:  continue
    MUT[r["mutant_id"]] = {"subject": r["subject"], "gates": json.loads(g),
                           "population": "prospective", "order": len(MUT)}

def zexp(counts, qs, shots=INNER_SHOTS):
    t = 0
    for k, v in counts.items():
        s = 1
        for q in qs:
            if k[len(k) - 1 - q] == "1": s = -s
        t += s * v
    return t / shots

def suite_terms(sub):
    n, ors = nq[sub], outreg[sub]
    smin = [(q,) for q in ors]
    return {"S_MIN":    smin,
            "S_FAMILY": smin + [(ors[i], ors[i+1]) for i in range(len(ors)-1)],
            "S_COVER":  [(q,) for q in range(n)],
            "S_BOTH":   [(q,) for q in range(n)] + [(i, i+1) for i in range(n-1)]}

def systematic_assertions(sub, terms):
    """References pinned to the ORIGINAL, exactly as the frozen rule requires."""
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

SSPEC = {m["subject"]: m["assertions"]
         for m in json.load(open("SSPEC_PROVENANCE.json"))["subjects"]
         if m["status"] == "S_SPEC_GROUNDED"}

def assertions_for(sub, suite):
    if suite == "S_SPEC":
        return list(SSPEC[sub])
    return systematic_assertions(sub, suite_terms(sub)[suite])

from e1_seed_schedule import seed_for, REFERENCE_SEED
assert REFERENCE_SEED == SEED

def execute(mutant_id, suite):
    """One (mutant, suite) cell at the frozen settings, on the RECOVERED HISTORICAL
    repetition-seed schedule for that mutant's population.  The same schedule is
    reused across every suite condition, so suite contrasts are paired on seeds."""
    m = MUT[mutant_id]; sub = m["subject"]
    A = assertions_for(sub, suite)
    reps = []
    for r in range(REPS):
        sd = seed_for(m["population"], mutant_id, r)
        v, msg = run_qutest(make_test(m["gates"], nq[sub], A, INNER_SHOTS, sd))
        reps.append({"rep": r, "seed": sd, "verdict": v, "detail": msg[:60]})
    kills = sum(1 for x in reps if x["verdict"] == "KILLED")
    unsup = sum(1 for x in reps if x["verdict"] == "UNSUPPORTED")
    native = ("KILLED" if kills == REPS else "SURVIVED" if kills == 0 else "SPLIT")
    if unsup:
        native = "UNSUPPORTED"
    return {"mutant_id": mutant_id, "subject": sub, "population": m["population"],
            "suite": suite, "n_assertions": len(A), "assertions": " | ".join(A),
            "kills_recorded": kills, "reps": REPS, "unsupported_reps": unsup,
            "native_verdict": native, "N": INNER_SHOTS, "R": REPS, "theta": ATOL,
            "seed_base": seed_for(m["population"], mutant_id, 0),
            "repetitions": reps}
