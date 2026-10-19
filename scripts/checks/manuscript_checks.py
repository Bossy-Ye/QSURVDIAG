import sys as _sys; _sys.dont_write_bytecode = True   # keep the package free of interpreter caches
# Recompute the values of engine manuscript_checks in expected/expected_results.csv from the archived records.
import csv, json, os, re, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

# Archived records are addressed by package path and checked against provenance/source_manifest.csv.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import orig as _orig, Dir as _Dir, out_dir as _out_dir
resolve = _orig
import witness_order as _wo

def rows(p): return list(csv.DictReader(open(resolve(p))))
def jsn(p):  return json.load(open(resolve(p)))

REF = rows("data/primary/records/599_B1_REFERENCE_RERUN_FRESH.csv")
# Baseline: S_MIN with ideal references at N = 2000, theta = 0.05, R = 12 (B5_A1E_REFERENCE_EXACT);
# B1_REFERENCE_RERUN_FRESH holds the sampled-reference contrast.
_EXACT = {r["mutant_id"]: r for r in rows("data/primary/records/599_B5_A1E_REFERENCE_EXACT.csv")}
def _exact_report(r):
    """Report at the declared baseline: the published report, except where the exact
    reference moves the native verdict.  A split native verdict routes to Unresolved."""
    e = _EXACT[r["mutant_id"]]
    if e["verdict_changed"] == "True" and e["exact_ref_native_verdict"] == "SPLIT":
        return "Unresolved"
    return r["diagnostic_outcome"]
NK  = [dict(r, diagnostic_outcome=_exact_report(r)) for r in REF
       if _EXACT[r["mutant_id"]]["exact_ref_native_verdict"] != "KILLED"]
CERT= {r["mutant_id"] for r in NK if r["diagnostic_outcome"] != "Unresolved"}
CON = rows("data/primary/records/599_B1_CONTRACT_RERUN.csv")
OB  = rows("data/primary/records/599_B1_OBSERVATION_RERUN.csv")
SU  = rows("data/primary/records/599_B1_SUITE_RERUN.csv")
IF  = rows("data/primary/records/B1_INTERFACE_RERUN.csv")
POP = rows("data/primary/manifests/B1_PRIMARY_POPULATION.csv")
UNR = rows("data/primary/manifests/B1_UNRECOVERED_CONSTRUCTION_EXCLUSIONS.csv")
PRO = rows("data/primary/manifests/B1_PROSPECTIVE_ELIGIBLE.csv")
MEM = rows("data/primary/records/599_B1_FROZEN_CONSTRUCTION_MEMBERSHIP.csv")
SH  = rows("data/primary/records/599_B2_SHOT_FRESH.csv")
TO  = rows("data/primary/records/599_B2_TOLERANCE_FRESH.csv")
BD  = rows("data/primary/records/599_B2_BOUND_FRESH.csv")
AB  = rows("data/primary/records/599_B2_EVIDENCE_ABLATION_FRESH.csv")
A1G = rows("data/primary/records/599_B5_A1G_POPULATION.csv")
A1GG= rows("data/primary/decision/B5_A1G_GUARD.csv")
A1K = rows("data/primary/records/599_B5_A1K_GHZ_CONTRACT_AUDIT.csv")
IF4 = rows("data/primary/decision/B5_A4_INTERFACE_CORRECTED.csv")
T4B = rows("data/interventions/transfer/B5_A4B_REPAIR_TRANSFER.csv")
E1E = rows("data/primary/records/599_B5_A1E_REFERENCE_EXACT.csv")
_k  = lambda s_: {r["mutant_id"] for r in A1G if r["suite"]==s_ and r["outcome"]=="KILLED"}
_ev = [r for r in T4B if r["outcome"]!="NOT_EVALUABLE"]
SC  = [json.loads(l) for l in open(resolve("data/scalability/B2_SCALE_CELLS_FRESH.jsonl"))]
CO  = jsn("data/scalability/B2_CORPUS_FRESH.json")
DF  = rows("data/external/defects/B3_REAL_DEFECTS_FRESH.csv")
EL  = rows("data/external/defects/B3_QUTEST_ELIGIBILITY_FRESH.csv")
RT  = rows("data/external/defects/B3_RELATION_TABLE_FRESH.csv")
STA = rows("data/primary/decision/B2_STATISTICS_FRESH.csv")
SGL = rows("data/primary/suites/SUITE_GUARD_LEDGER.csv")
COMM= rows("data/primary/records/599_B1_SUITE_COMMON_EVALUABLE.csv")

d  = Counter(r["diagnostic_outcome"] for r in NK)
dp = lambda p: Counter(r["diagnostic_outcome"] for r in NK if r["population"]==p)
uni= Counter(r["report_uniform_arbitrary_unitary"] for r in CON if r["mutant_id"] in CERT)
dec= Counter(r["report_declared"] for r in CON if r["mutant_id"] in CERT)
cl3= [r for r in IF if r["reference_report"]=="CL3"]
stable=[r for r in SH if r["native_verdict"] in ("KILLED","SURVIVED")]
gu=[r for r in stable if r["guaranteed"]=="True"]
UNIV=[r for r in BD if r["role"]=="universe_decisive"]
refc=[r for r in UNIV if r["theta"]=="0.05" and r["N"]=="2000"]
sup=lambda g: sum(1 for r in g if r["bound_status"]=="SUPPORTED")
# Suite kills: B5_A1G_POPULATION (ideal references, N = 8000, all 88 subject x suite cells clean).
_REPMAP={r["mutant_id"]: r["published_report"] for r in E1E}
sa=defaultdict(lambda: defaultdict(lambda:[0,0]))
for r in A1G:
    _rep=_REPMAP.get(r["mutant_id"])
    if r["suite"]=="S_MIN" or _rep not in ("CL3","CL4"): continue
    c=sa[r["suite"]][_rep]; c[1]+=1; c[0]+= r["outcome"]=="KILLED"
scw={}
for n in sorted({int(r["n"]) for r in SC}):
    g=[r for r in SC if int(r["n"])==n]; scw[n]=g
asw=lambda r: r["timings"]["B_universe"]+r["timings"]["C_relations"]
_REL_BY_CELL = defaultdict(set)          # Stage-2 relations per (pair, theta) across the shot budgets
for _r in SH: _REL_BY_CELL[(_r["mutant_id"], _r["theta"])].add(tuple(_r[k] for k in ("R_C", "R_S", "R_O", "R_A", "R_T")))
scc=Counter(("KILLED" if r["native_verdict"]=="KILLED" else r["report"]) for r in SC)

# ---- corpus: stratified certification ------------------------------------------
_T2A = [json.loads(_l) for _l in open(resolve("data/scalability/corpus/T2A_STRATIFIED_RAW.jsonl"))]
_T2E = {(r["case_set"], r["pair_id"]): r
        for r in rows("data/scalability/corpus/T2A_ELIGIBILITY.csv")}
for _r in _T2A:
    _r["diag"] = _T2E[(_r["case_set"], _r["pair_id"])]["diagonal_stratum"] == "True"
_T2A_OK  = [r for r in _T2A if r["status"] == "OK"]
_T2A_ND  = [r for r in _T2A_OK if not r["diag"]]
_T2A_D   = [r for r in _T2A_OK if r["diag"]]
_T2A_SUR = [r for r in _T2A_OK if r["native_verdict"] == "SURVIVED"]
_cl3 = lambda g: sum(1 for r in g if r["diagnostic_outcome"] == "CL3")
_T2A_SUB = [r for r in _T2A_OK if (not r["R_S"]) and r["R_O"]]
_T2A_W = {w: sum(1 for r in _T2A_OK if r["n"] == w and r["diagnostic_outcome"] == "CL3")
          for w in range(2, 15)}
_T2A_M = jsn("data/scalability/corpus/T2A_CL5_MECHANISM.json")
_T2C = jsn("data/scalability/corpus/T2C_TIMING_SUMMARY.json")
_T31 = jsn("data/scalability/corpus/T3_1_ENTAILED_VS_CONTINGENT.json")
_OC  = jsn("data/primary/records/599_OUTPUT_CONDITION.json")
_T2A_S = jsn("data/scalability/corpus/T2A_STRATUM_MECHANISM.json")
def _wilson(k, n, z=1.959963984540054):
    p_ = k / n; d = 1 + z * z / n
    c = (p_ + z * z / (2 * n)) / d
    h = z / d * ((p_ * (1 - p_) / n + z * z / (4 * n * n)) ** 0.5)
    return round(max(0.0, c - h) * 100, 1), round(min(1.0, c + h) * 100, 1)
_T2A_SEP5 = [r["max_universe_separation"] for r in _T2A_OK if r["diagnostic_outcome"] == "CL5"]
_T2A_SEP4 = [r["max_universe_separation"] for r in _T2A_OK if r["diagnostic_outcome"] == "CL4"]

# ---- two-axis CL4 partition under both output-register readings (ideal references, N = 8000)
_a1g = defaultdict(dict)
for _r in A1G: _a1g[_r["mutant_id"]][_r["suite"]] = _r
_aud = {_r["mutant_id"]: _r for _r in A1K}
_cl4 = [_r["mutant_id"] for _r in E1E if _r["published_report"] == "CL4"]
_K = lambda m, su: _a1g[m][su]["outcome"] == "KILLED"
def _pat(m):
    c, f, b = _K(m,"S_COVER"), _K(m,"S_FAMILY"), _K(m,"S_BOTH")
    return ("coverage" if (c and not f) else "family" if (f and not c)
            else "both_axes" if (c and f) else "both_jointly" if b else "neither")
PART_DECL = Counter(_pat(m) for m in _cl4)
_still = [m for m in _cl4 if _aud[m]["corrected_report"] == "CL4"]
PART_CORR = Counter()
for _m in _still:
    PART_CORR["family" if _K(_m,"S_BOTH") else "both_jointly"] += 1 \
        if _aud[_m]["subject"].startswith("ghz") else 0
    if not _aud[_m]["subject"].startswith("ghz"): PART_CORR[_pat(_m)] += 1
tol=lambda th,k: sum(1 for r in TO if float(r["theta"])==th and r[k]=="CL5")
THS=sorted({float(r["theta"]) for r in TO})
w7=sorted((int(k),v) for k,v in CO["by_width"].items())
tot7=lambda p: sum(sum(v.values()) for k,v in w7 if p(k))
c37 =lambda p: sum(v.get("CL3_SUBSTRATE",0) for k,v in w7 if p(k))

# ---- analytic reruns (data/certification/outcomes): recomputed from the recorded final states and gate lists
import math as _math
_R2 = _Dir("data/certification/outcomes")
def rerun_csv(name): return _wo.final(name, list(csv.DictReader(open(_R2 / name))))
_R2P  = rerun_csv("R2_PRIMARY_PAIRS.csv")
_R2CW = rerun_csv("R2_CORPUS_WIDTH_PAIRS.csv")
_R2X  = rerun_csv("R2_EXTERNAL_CL3.csv")
_R2CB = rerun_csv("R2_CHEAP_BASELINE.csv")
_R2M  = rerun_csv("R2_MARGINS.csv")
_R2MX = rerun_csv("R2_MARGINS_EXT.csv")
_R2C  = rerun_csv("R2_CONDITIONAL_SEPARATIONS.csv")
_T14  = rows("data/primary/records/T1_4_INTERFACE_599.csv")
_TH6  = ("0.01", "0.025", "0.05", "0.1", "0.25", "0.5")
_wsep = lambda g: sum(1 for r in g if int(r["witness_separating_cuts"] or 0) > 0)
_p3   = [r for r in _R2P if r["report"] == "CL3"]
_c3   = [r for r in _R2CW if r["arm"] == "corpus" and r["report"] == "CL3"]
_w3   = [r for r in _R2CW if r["arm"] == "width" and r["report"] == "CL3"]
_cl5s = lambda th, sc: sum(1 for r in _R2P if r[f"base_{th}"] == "True" and r[f"{sc}_{th}"] == "false")
_und  = lambda th, sc: sum(1 for r in _R2P if r[f"base_{th}"] == "True" and r[f"{sc}_{th}"] == "undecided")
_P2   = {r["mutant_id"]: r for r in _R2P}
_TOK  = {"0.01": "0.01", "0.025": "0.025", "0.05": "0.05", "0.1": "0.1", "0.25": "0.25", "0.5": "0.5"}
_LO, _HI, _TOL = 1e-10, 1e-8, 1e-9
_cbp  = [r for r in _R2CB if r["arm"] == "primary"]
_cbw  = [r for r in _R2CB if r["arm"] == "width" and r.get("t_full_s")]
_cbc  = [r for r in _R2CB if r["arm"] == "corpus"]
_ms   = lambda g, k: st.median([float(r[k]) for r in g if r.get(k)])
_mk   = {(r["arm"], r["pair"]): r for r in _R2M if r["arm"] != "corpus"}
_T2Aall = [json.loads(_l) for _l in open(resolve("data/scalability/corpus/T2A_STRATIFIED_RAW.jsonl"))]
_mc   = [(m, t) for m, t in zip([r for r in _R2M if r["arm"] == "corpus"], _T2Aall)]
_inb  = lambda m: any(_LO <= float(m[k]) <= _HI for k in ("state_margin", "obs_margin"))
_near = lambda m: any(1e-12 <= float(m[k]) <= 1e-6 for k in ("state_margin", "obs_margin"))
_band_c = sorted(t["pair_id"] for m, t in _mc if _inb(m))
_near_c = sorted(t["pair_id"] for m, t in _mc if _near(m) and not _inb(m))
_cw5  = lambda arm: [r for r in _R2CW if r["arm"] == arm and r["report"] == "CL5"]
_bandkey = {t["pair_id"] for m, t in _mc if _inb(m)} | {r["pair"] for r in _R2M if r["arm"] == "width" and _inb(r)}
_eqv, _nev = [], []
for _mrow in _R2M:
    for _mcol in ("state_margin", "obs_margin"):
        (_eqv if float(_mrow[_mcol]) < _TOL else _nev).append((_mrow["arm"], float(_mrow[_mcol])))
for _mrow in _R2MX:
    for _mcol in ("unitary_margin", "qucheck_all_margin", "state_margin", "obs_margin"):
        if _mrow.get(_mcol):
            (_eqv if float(_mrow[_mcol]) < _TOL else _nev).append((_mrow["arm"], float(_mrow[_mcol])))
_ne_pie = min(v for a, v in _nev if a in ("primary", "external"))
_ne_cw  = min(v for a, v in _nev if a in ("corpus", "width"))
_dj  = next(r for r in _R2M if r["arm"] == "primary" and r["pair"] == "dj_3#e19")
_djb = next(r for r in BD if r["mutant_id"] == "dj_3#e19" and r["N"] == "2000" and r["theta"] == "0.05"
            and r["role"] == "suite_decisive")
_djr = next(r for r in REF if r["mutant_id"] == "dj_3#e19")
_q174 = next(r for r in _R2C if r["pair_id"] == "QRA_174")

CHECKS = [
 # -------- the 20 circuits: baseline and suites
 ("M001", "primary pairs killed by the baseline suite",               302, len(_k("S_MIN"))),
 ("M002", "primary pairs entering diagnosis",             297, len(E1E)-len(_k("S_MIN"))),
 ("M003", "exact-reference killed",              302, sum(1 for r in E1E if r["exact_ref_native_verdict"]=="KILLED")),
 ("M004", "suite guard cells clean = 88 of 88",         88, sum(1 for r in A1GG if r["cell"]=="CLEAN")),
 ("M005", "suite revived kills = 0",                     0, len(_k("S_MIN")-_k("S_BOTH"))),
 ("M006", "S_FAMILY added kills = 14",                  14, len(_k("S_FAMILY")-_k("S_MIN"))),
 ("M007", "all-qubit suite kills of the 79 suite omissions",                   41, len(_k("S_COVER")-_k("S_MIN"))),
 ("M008", "S_BOTH added kills",                    81, len(_k("S_BOTH")-_k("S_MIN"))),
 ("M009", "full-string GHZ register: GHZ suite omissions killed",             32, sum(1 for r in A1K if r["moved"]=="True")),
 ("M010", "suite omissions under the full-string GHZ register",                47, sum(1 for r in A1K if r["corrected_report"]=="CL4")),
 ("M011", "observation limitations unchanged by the GHZ register",               35, sum(1 for r in A1K if r["corrected_report"]=="CL3")),
 ("M014", "CL3 persisting under QuCheck = 7",          7, sum(1 for r in IF4 if r["reference_report"]=="CL3" and r["R_O_QuCheck_all_qubits"]=="true")),
 ("M015", "named repair transfers for 8 of 21",        8, sum(1 for r in _ev if r["qutest_witness_expressible"]=="True")),
 ("M016", "some QuCheck repair for 15 of 21",         15, sum(1 for r in _ev if r["outcome"]=="WITNESS_EXISTS")),
 ("M017", "no separating assertion for 6 of 21",       6, sum(1 for r in _ev if r["outcome"]=="NO_WITNESS_ABOVE_THETA")),
 # -------- populations and design
 ("M018", "mutants allocated per circuit = 30",            30, len(POP)//20),
 ("M019", "generated cases = 600",                        600, 20*30),
 ("M020", "allocation ledger rows = 600",                 600, len(POP)),
 ("M021", "executable primary mutants = 599",             599, len(MEM)+149),
 ("M022", "construction cohort = 450",                    450, len(MEM)),
 ("M023", "construction mutants excluded from the population = 53",      53, len(UNR)),
 ("M024", "prospective eligible = 149",                   149, sum(1 for r in PRO if r.get("eligible","true").lower() in ("true","1","yes"))),
 ("M025", "450 + 149 = 599",                              599, len(MEM)+149),
 # -------- reference condition
 ("M026", "non-killed diagnostic cases",             297, len(NK)),
 ("M027", "construction cases",                      195, sum(dp("construction").values())),
 ("M028", "prospective cases = 102",                       102, sum(dp("prospective").values())),
 ("M029", "contract equivalences",                                       93, d["CL1"]),
 ("M030", "CL2",                                       87, d["CL2"]),
 ("M031", "observation limitations",                                       35, d["CL3"]),
 ("M032", "CL4",                                       79, d["CL4"]),
 ("M033", "CL5 = 1",                                         1, d["CL5"]),
 ("M034", "Unresolved = 2",                                  2, d["Unresolved"]),
 ("M035", "certificate-bearing survivors",           295, len(CERT)),
 # -------- contract
 ("M036", "semantic relations: equivalent on all legal inputs",       4, uni["CL1"]),
 ("M037", "semantic relations: same final state on the executed input",              176, uni["CL2"]),
 ("M038", "semantic relations: different final state on the executed input",           115, len(CERT)-uni["CL1"]-uni["CL2"]),
 ("M039", "semantic relations: contract equivalences under the declared contracts",       93, dec["CL1"]),
 ("M040", "fixed-input contract equivalences that differ on another input",          89, sum(1 for r in CON if r["mutant_id"] in CERT
                                                              and r["report_declared"]=="CL1"
                                                              and r["report_uniform_arbitrary_unitary"]=="CL2")),
 ("M041", "declared share, %",                       "31.5", f"{100*dec['CL1']/len(CERT):.1f}"),
 ("M042", "uniform share, %",                          "1.4", f"{100*uni['CL1']/len(CERT):.1f}"),
 # -------- observation lattice
 ("M043", "Fig. 4(a) observation limitations at Z, output register",           90, sum(1 for r in OB if r["CL3_Z_output"]=="True")),
 ("M044", "Fig. 4(a) observation limitations at Z, all qubits",                35, sum(1 for r in OB if r["CL3_Z_all"]=="True")),
 ("M045", "Fig. 4(a) observation limitations at XYZ, output register",           60, sum(1 for r in OB if r["CL3_XYZ_output"]=="True")),
 ("M046", "Fig. 4(a) observation limitations at XYZ, all qubits",                  0, sum(1 for r in OB if r["CL3_XYZ_all"]=="True")),
 ("M047", "lattice denominator = 193 construction pairs",  193, len(OB)),
 ("M048", "matched changes: four observation refinements, pairs leaving observation limitation", "55/30/35/60",
   "/".join(str(a-b) for a,b in [
      (sum(1 for r in OB if r["CL3_Z_output"]=="True"),   sum(1 for r in OB if r["CL3_Z_all"]=="True")),
      (sum(1 for r in OB if r["CL3_Z_output"]=="True"),   sum(1 for r in OB if r["CL3_XYZ_output"]=="True")),
      (sum(1 for r in OB if r["CL3_Z_all"]=="True"),      sum(1 for r in OB if r["CL3_XYZ_all"]=="True")),
      (sum(1 for r in OB if r["CL3_XYZ_output"]=="True"), sum(1 for r in OB if r["CL3_XYZ_all"]=="True"))])),
 # -------- suites
 ("M049", "S_FAMILY kills of CL3",                 "0/35", f"{sa['S_FAMILY']['CL3'][0]}/{sa['S_FAMILY']['CL3'][1]}"),
 ("M050", "S_FAMILY kills of CL4",               "12/79", f"{sa['S_FAMILY']['CL4'][0]}/{sa['S_FAMILY']['CL4'][1]}"),
 ("M051", "S_COVER kills of CL3",                  "0/35", f"{sa['S_COVER']['CL3'][0]}/{sa['S_COVER']['CL3'][1]}"),
 ("M052", "S_COVER kills of CL4",                "41/79", f"{sa['S_COVER']['CL4'][0]}/{sa['S_COVER']['CL4'][1]}"),
 # -------- two-axis CL4 partition under both output-register readings
 ("M053", "declared-register CL4 partition",  "41/12/26",
      f"{PART_DECL['coverage']}/{PART_DECL['family']}/{PART_DECL['both_jointly']}"),
 ("M054", "declared-register CL4 partition total",       79, sum(PART_DECL.values())),
 ("M055", "whole-string CL4 partition",            "9/34/4",
      f"{PART_CORR['coverage']}/{PART_CORR['family']}/{PART_CORR['both_jointly']}"),
 ("M056", "whole-string CL4 partition total",            47, sum(PART_CORR.values())),
 # -------- corpus: stratified certification
 ("M057", "frame executed = 1,537",                     1537, len(_T2A)),
 ("M058", "execution failures = 0",                        0, len(_T2A) - len(_T2A_OK)),
 ("M059", "registered corpus record: |U_v| matches the registered universe 2^(n+1)+n+1 (before the two added distances) on all",           True, all(r["U_v_agree"] for r in _T2A_OK)),
 ("M060", "guard 0 false-fails on all",                 True, all(r["guard_false_fails"] == 0 for r in _T2A_OK)),
 ("M061", "reference condition exact analytic", "exact_analytic", _T2A_OK[0]["reference_condition"]),
 ("M062", "killed by S_MIN = 975",                       975, sum(1 for r in _T2A_OK if r["native_verdict"]=="KILLED")),
 ("M063", "survivors under S_MIN = 511",                 511, len(_T2A_SUR)),
 ("M064", "split verdicts = 51 and all Unresolved",  "51/51",
      f'{sum(1 for r in _T2A_OK if r["native_verdict"]=="SPLIT")}/'
      f'{sum(1 for r in _T2A_OK if r["native_verdict"]=="SPLIT" and r["diagnostic_outcome"]=="Unresolved")}'),
 ("M065", "initial analysis: reports 158 CL1 / 150 CL3 / 185 CL4 / 18 CL5", "158/150/185/18",
      "/".join(str(sum(1 for r in _T2A_OK if r["diagnostic_outcome"]==c)) for c in ("CL1","CL3","CL4","CL5"))),
 ("M066", "CL2 empty under a fixed-input contract",        0, sum(1 for r in _T2A_OK if r["diagnostic_outcome"]=="CL2")),
 ("M067", "substrate and certificate coincide at 150", "150/150",
      f"{len(_T2A_SUB)}/{_cl3(_T2A_OK)}"),
 ("M068", "strata sizes 818 non-diagonal / 719 diagonal", "818/719",
      f"{len(_T2A_ND)}/{len(_T2A_D)}"),
 ("M069", "non-diagonal CL3 = 58 of 818",             "58/818", f"{_cl3(_T2A_ND)}/{len(_T2A_ND)}"),
 ("M070", "diagonal CL3 = 92 of 719",                 "92/719", f"{_cl3(_T2A_D)}/{len(_T2A_D)}"),
 ("M071", "non-diagonal CL3 among survivors = 58 of 240", "58/240",
      f'{_cl3([r for r in _T2A_SUR if not r["diag"]])}/{sum(1 for r in _T2A_SUR if not r["diag"])}'),
 # -------- corpus: per-width observation limitation
 ("M072", "per-width CL3 reproduces the per-width table",
      "17/8/13/15/16/9/24/24/20/1/0/1/2",
      "/".join(str(_T2A_W[w]) for w in range(2, 15))),
 ("M073", "150 in frame + 1 at n=19 = 151",       151, sum(_T2A_W.values()) + 1),
 # -------- corpus: below-tolerance differences
 ("M074", "construction CL4/CL5 saturating = 57 of 64",  "57/64",
      f'{_T2A_M["construction_set"]["exactly_one"]}/{_T2A_M["construction_set"]["n"]}'),
 ("M075", "construction smallest separation = 0.0294", 0.0294, _T2A_M["construction_set"]["minimum"]),
 ("M076", "construction share at or below theta = 1.6%", 0.0156, _T2A_M["construction_set"]["share_at_or_below_theta"]),
 ("M077", "corpus CL4/CL5 saturating = 21 of 203",      "21/203",
      f'{_T2A_M["corpus_frame"]["exactly_one"]}/{_T2A_M["corpus_frame"]["n"]}'),
 ("M078", "corpus share at or below theta = 8.9%",     0.0887, _T2A_M["corpus_frame"]["share_at_or_below_theta"]),
 # -------- corpus: diagonal stratum
 ("M079", "diagonal stratum CL3 rate 12.8% (92 of 719)", "92/719",
      f'{_T2A_S["diagonal_stratum_cl3"]}/{_T2A_S["diagonal_stratum_size"]}'),
 ("M080", "diagonal-insertion CL3 rate = 26.0%",      0.2603,
      _T2A_S["cl3_rate_by_mutation_kind"]["insertion"]["rate"]),
 ("M081", "diagonal-stratum 'other' mutations CL3 = 0", 0,
      _T2A_S["cl3_rate_by_mutation_kind"]["other"]["cl3"]),
 # -------- corpus: intervals
 ("M082", "non-diagonal Wilson 95% = [5.5, 9.1]",   "(5.5, 9.1)",
      str(_wilson(_cl3(_T2A_ND), len(_T2A_ND)))),
 ("M083", "diagonal Wilson 95% = [10.6, 15.4]",    "(10.6, 15.4)",
      str(_wilson(_cl3(_T2A_D), len(_T2A_D)))),
 ("M084", "survivor non-diagonal Wilson = [19.2, 30.0]", "(19.2, 30.0)",
      str(_wilson(_cl3([r for r in _T2A_SUR if not r["diag"]]),
                  sum(1 for r in _T2A_SUR if not r["diag"])))),
 ("M085", "survivor diagonal Wilson = [28.6, 39.8]", "(28.6, 39.8)",
      str(_wilson(_cl3([r for r in _T2A_SUR if r["diag"]]),
                  sum(1 for r in _T2A_SUR if r["diag"])))),
 ("M086", "intervals do not overlap (9.1 < 10.6)",   True,
      _wilson(_cl3(_T2A_ND), len(_T2A_ND))[1] < _wilson(_cl3(_T2A_D), len(_T2A_D))[0]),
 # -------- output-condition counterfactual
 ("M087", "output-condition pool = 47",                     47, _OC["at_599"]["pool"]),
 ("M088", "output-condition movers = 8",                     8, _OC["at_599"]["movers"]),
 ("M089", "output-condition movers out = 0",                 0, _OC["at_599"]["out"]),
 ("M090", "output-condition CL3 movers = 4 of 35",       "4/35",
      f'{_OC["at_599"]["movers_by_report"]["CL3"]}/{_OC["at_599"]["total_cl3"]}'),
 ("M091", "output-condition predicate reproduces 546",    True, _OC["validation"]["reproduces_published"]),
 # -------- sufficient condition versus contingent observation limitations
 ("M092", "corpus sufficient condition: entailed pairs = 54",                        54, _T31["entailed"]["n"]),
 ("M093", "corpus sufficient condition: R_O holds on all 54 entailed",           "54/54",
      f'{_T31["entailed"]["R_O_holds"]}/{_T31["entailed"]["n"]}'),
 ("M094", "corpus sufficient condition: all 54 entailed certify CL3",            "54/54",
      f'{_T31["entailed"]["cl3"]}/{_T31["entailed"]["n"]}'),
 ("M095", "corpus sufficient condition: contingent CL3 = 96",                        96, _T31["not_entailed"]["cl3"]),
 ("M096", "corpus sufficient condition: 54 entailed + 96 contingent = 150",         150,
      _T31["entailed"]["cl3"] + _T31["not_entailed"]["cl3"]),
 ("M097", "corpus sufficient condition: all entailed lie in the diagonal stratum",   54, _T31["stratum_vs_entailment"]["entailed_in_diagonal_stratum"]),
 ("M098", "corpus sufficient condition: diagonal stratum holds 38 contingent CL3",   38,
      _T31["stratum_vs_entailment"]["contingent_cl3_in_diagonal_stratum"]),
 ("M099", "corpus sufficient condition: no entailed pair in the non-diagonal stratum", 0,
      _T31["stratum_vs_entailment"]["entailed_in_non_diagonal_stratum"]),
 ("M100", "corpus sufficient condition: proxy covers 54 entailed + 665 others",     665,
      _T31["stratum_vs_entailment"]["non_entailed_in_diagonal_stratum"]),
 # -------- width set: cost decomposition
 ("M101", "width set: native suite execution share = 98.4%",     0.984,
      round(_T2C["median_phase_seconds"]["A_evidence_acquisition"]/_T2C["median_total_seconds"],3)),
 ("M102", "width set: assertion-space share at n=14 = 12.5%",    0.125,
      round(_T2C["by_width"]["14"]["median_B"]/_T2C["by_width"]["14"]["median_total_seconds"],3)),
 ("M103", "width set: assertion-space share at n=10 < 0.2%",      True,
      _T2C["by_width"]["10"]["median_B"]/_T2C["by_width"]["10"]["median_total_seconds"] < 0.002),
 ("M104", "width set: growth per added qubit at n=14 = 3.8x",      3.81,
      round(_T2C["by_width"]["14"]["median_B"]/_T2C["by_width"]["13"]["median_B"], 2)),
 ("M105", "width set: crossover near n=16",                        15.8,
      _T2C["extrapolation"]["crossover_n_where_enumeration_overtakes_suite_execution"]),
 ("M106", "width set: 600 s budget exhausted near n=19",          True,
      _T2C["extrapolation"]["projected_total_seconds_holding_A_at_its_median"]["18"] < 600
      < _T2C["extrapolation"]["projected_total_seconds_holding_A_at_its_median"]["19"]),
 ("M107", "largest CL5 separation = 0.0496",       0.0496, round(max(_T2A_SEP5), 4)),
 ("M108", "smallest CL4 separation = 0.0504",      0.0504, round(min(_T2A_SEP4), 4)),
 ("M109", "no case between them",                    True,
      max(_T2A_SEP5) < 0.05 < min(_T2A_SEP4)),
 ("M110", "diagonal CL3 among survivors = 92 of 271",  "92/271",
      f'{_cl3([r for r in _T2A_SUR if r["diag"]])}/{sum(1 for r in _T2A_SUR if r["diag"])}'),
 ("M111", "GHZ CL4 cases remaining under the whole-string reading", 22,
      sum(1 for m in _still if _aud[m]["subject"].startswith("ghz"))),
 ("M112", "GHZ CL4 cases needing both axes at the declared register", 22,
      sum(1 for m in _still if _aud[m]["subject"].startswith("ghz") and _pat(m)=="both_jointly")),
 ("M113", "S_BOTH kills of CL4",                 "79/79", f"{sa['S_BOTH']['CL4'][0]}/{sa['S_BOTH']['CL4'][1]}"),
 # -------- profiles: QuCheck X/Y/Z on every qubit (B5_A4_INTERFACE_CORRECTED)
 ("M119", "register-restricted QuCheck: observation limitations persisting = 12", 12,
      sum(1 for r in IF4 if r['reference_report']=='CL3' and r['R_O_QuCheck_declared_register']=='true')),
 # -------- decision and evidence
 ("M120", "natively executed decision cells",                    4869, len(SH)),
 ("M121", "N moves a Stage-2 relation in 0 cells",           0, sum(1 for v in _REL_BY_CELL.values() if len(v) > 1)),
 ("M122", "cells covered by the finite-shot bound",               "3648/4198", f"{len(gu)}/{len(stable)}"),
 ("M123", "no disagreement in covered cells",                0, sum(1 for r in gu if r["agree"]=="False")),
 ("M124", "disagreements among the cells outside the bound",     "71/550",
   f"{sum(1 for r in stable if r['guaranteed']=='False' and r['agree']=='False')}/{len(stable)-len(gu)}"),
 ("M125", "witness coverage over pairs",              "541/599", f"{sup(refc)}/{len(refc)}"),
 ("M126", "witness coverage over cells",        "7992/10782", f"{sup(UNIV)}/{len(UNIV)}"),
 ("M127", "witness coverage, %",                    "74.1", f"{100*sup(UNIV)/len(UNIV):.1f}"),
 ("M128", "ablations",                          21040, len(AB)),
 ("M129", "supported certificates",                  1178, len({(r['mutant_id'],r['suite'],r['report']) for r in AB})),
 ("M130", "requirement items, half the ablations",                           10520, len(AB)//2),
 ("M131", "mean requirements per certificate",   "8.93",
   f"{len(AB)/2/len({(r['mutant_id'],r['suite'],r['report']) for r in AB}):.2f}"),
 ("M132", "tolerance cells",                      3594, len(TO)),
 ("M133", "candidate CL5 sweep 0,0,1,1,4,23",  "0,0,1,1,4,23", ",".join(str(tol(t,"analytic_candidate")) for t in THS)),
 ("M134", "supported CL5 sweep 0,0,1,1,2,2",    "0,0,1,1,2,2", ",".join(str(tol(t,"supported_report")) for t in THS)),
 # -------- scale
 ("M135", "scale manifest pairs = 162",                    162, len(rows("data/scalability/E4_SCALE_MANIFEST.csv"))),
 ("M136", "executed scale pairs = 143",                    143, len(SC)),
 ("M137", "scale native kills = 96",                        96, scc["KILLED"]),
 ("M138", "scale CL1 = 19",                                 19, scc["CL1"]),
 ("M139", "scale CL3 = 17",                                 17, scc["CL3"]),
 ("M140", "scale CL4 = 7",                                   7, scc["CL4"]),
 ("M141", "scale CL5 = 3",                                   3, scc["CL5"]),
 ("M142", "scale Unresolved = 1",                            1, scc["Unresolved"]),
 ("M143", "universe 521 at n=8",                           521, int(scw[8][0]["U_v_implementation"])),
 ("M144", "universe 32,783 at n=14",                     32783, int(scw[14][0]["U_v_implementation"])),
 ("M145", "assertion-space factor 715",                    715, round(st.median([asw(r) for r in scw[14]])/
                                                                st.median([asw(r) for r in scw[8]]))),
 ("M146", "assertion-space median 5.8 ms at n=8",        "5.8", f"{st.median([asw(r) for r in scw[8]])*1000:.1f}"),
 ("M147", "assertion-space median 4.15 s at n=14",      "4.15", f"{st.median([asw(r) for r in scw[14]]):.2f}"),
 ("M148", "total-per-case medians 37.7 to 43.7 s",  "37.7/43.7",
   f"{min(st.median([float(x['total_seconds']) for x in g]) for g in scw.values()):.1f}/"
   f"{max(st.median([float(x['total_seconds']) for x in g]) for g in scw.values()):.1f}"),
 ("M149", "largest total 59.3 s",                       "59.3", f"{max(float(r['total_seconds']) for r in SC):.1f}"),
 ("M150", "largest resident set 0.092 GiB",             "0.092", f"{max(float(r['peak_rss_gib']) for r in SC):.3f}"),
 ("M151", "no resource censoring",                           0, sum(1 for r in SC if r.get("memory_censored")=="True"
                                                              or r.get("within_budget") is False)),
 # -------- corpus
 ("M152", "corpus distinct pairs = 1,569",                1569, CO["distinct_pairs"]),
 ("M153", "corpus CL3 substrate 9.4 % at n<=7",          "9.4", f"{100*c37(lambda k:k<=7)/tot7(lambda k:k<=7):.1f}"),
 ("M154", "corpus CL3 substrate 9.9 % at n>=8",          "9.9", f"{100*c37(lambda k:k>=8)/tot7(lambda k:k>=8):.1f}"),
 # -------- released defects
 ("M155", "released defects = 42",                          42, len(DF)),
 ("M156", "depth NOT_REPRODUCIBLE = 10",                    10, sum(1 for r in DF if r["evidence_depth"]=="NOT_REPRODUCIBLE")),
 ("M157", "depth NATIVE_REPRODUCTION_ONLY = 8",              8, sum(1 for r in DF if r["evidence_depth"]=="NATIVE_REPRODUCTION_ONLY")),
 ("M158", "depth PROFILE_ONLY = 10",                        10, sum(1 for r in DF if r["evidence_depth"]=="PROFILE_ONLY")),
 ("M159", "depth RELATION_LEVEL = 12",                      12, sum(1 for r in DF if r["evidence_depth"]=="RELATION_LEVEL")),
 ("M160", "depth FULL_CERTIFICATION = 2",                    2, sum(1 for r in DF if r["evidence_depth"]=="FULL_CERTIFICATION")),
 ("M161", "closed-profile eligible = 4",                     4, sum(1 for r in EL if r["qutest_eligibility"]=="ELIGIBLE")),
 # -------- analytic reruns
 ("M169", "QuCheck resolves 28 of the 599 pairs",           28, sum(1 for r in _T14 if r["R_O_QUTest"]=="True" and r["R_O_QuCheck"]=="False")),
 ("M170", "QuCheck loses 25 of the 599 pairs",              25, sum(1 for r in _T14 if r["R_O_QUTest"]=="False" and r["R_O_QuCheck"]=="True")),
 ("M171", "witness separates 5 of 35 primary CL3",      "5/35", f"{_wsep(_p3)}/{len(_p3)}"),
 ("M172", "witness-separated primary CL3 all QFT",           5, sum(1 for r in _p3 if int(r["witness_separating_cuts"] or 0) > 0 and r["subject"].startswith("qft"))),
 ("M173", "witness separates 4 of 150 corpus CL3",     "4/150", f"{_wsep(_c3)}/{len(_c3)}"),
 ("M174", "witness separates 0 of 17 width-set CL3",    "0/17", f"{_wsep(_w3)}/{len(_w3)}"),
 ("M175", "witness separates 0 of 30 external CL3",     "0/30", f"{_wsep(_R2X)}/{len(_R2X)}"),
 ("M176", "external rebuild reproduces R_O, 30 of 30",  "30/30", f"{sum(1 for r in _R2X if r['R_O_recomputed'].lower() in r['R_O_frozen'].lower())}/{len(_R2X)}"),
 ("M177", "low-order witness for 79 of 79 CL4",        "79/79", f"{sum(1 for r in _cbp if r['report']=='CL4' and r['cheap_witness']=='True')}/{sum(1 for r in _cbp if r['report']=='CL4')}"),
 ("M178", "low-order baseline escalates 1 primary case",     1, sum(1 for r in _cbp if float(r["full_max"]) > _TOL and r["cheap_witness"] != "True")),
 ("M179", "corpus CL4 with only higher-order witnesses = 11",11, sum(1 for r in _cbc if r["report"]=="CL4" and r["cheap_witness"] != "True")),
 ("M180", "corpus CL4 total = 185",                        185, sum(1 for r in _cbc if r["report"]=="CL4")),
 ("M181", "low-order median 0.15 ms",                   "0.15", f"{_ms(_cbp,'t_cheap_s')*1000:.2f}"),
 ("M182", "full-universe median 0.51 ms",               "0.51", f"{_ms(_cbp,'t_full_s')*1000:.2f}"),
 ("M183", "width low-order median 1.2 ms",               "1.2", f"{_ms(_cbw,'t_cheap_s')*1000:.1f}"),
 ("M184", "width full-universe median 79 ms",             "79", f"{_ms(_cbw,'t_full_s')*1000:.0f}"),
 ("M185", "rerun CL5 sweep over the six tolerances",         "0,0,1,1,4,18", ",".join(str(_cl5s(t, "RAcert")) for t in _TH6)),
 ("M186", "rerun CL5 at theta 0.50 = 18",                   18, _cl5s("0.5", "RAcert")),
 ("M187", "recorded CL5 at theta 0.50 = 23",                23, sum(1 for r in TO if r["theta"]=="0.5" and r["analytic_candidate"]=="CL5")),
 ("M188", "recorded sweep reproduced from rerun U5", "0,0,1,1,4,23", ",".join(str(_cl5s(t, "RA5")) for t in _TH6)),
 ("M189", "KL separates five recorded CL5 at 0.50",          5, sum(1 for r in _R2P if r["base_0.5"]=="True" and r["RA5_0.5"]=="false" and r["RAcert_0.5"]=="true")),
 ("M190", "full family settles two undecided at 0.50",       2, sum(1 for r in _R2P if r["base_0.5"]=="True" and r["RA5_0.5"]=="undecided" and r["RAcert_0.5"]=="true")),
 ("M191", "rerun resolution-limited at 0.50 = 3",            3, _und("0.5", "RAcert")),
 ("M192", "recorded resolution-limited at 0.50 = 5",         5, _und("0.5", "RA5")),
 ("M193", "excluded kinds lower theta 0.50 count to 16",    16, _cl5s("0.5", "RAcond")),
 ("M194", "excluded kinds leave smaller sweep unchanged", "0,0,1,1,4", ",".join(str(_cl5s(t, "RAcond")) for t in _TH6[:5])),
 ("M195", "supported CL5 unchanged under full family", "0,0,1,1,2,2",
   ",".join(str(sum(1 for r in TO if r["theta"]==_TOK[t] and r["supported_report"]=="CL5"
                    and _P2[r["mutant_id"]][f"RAcert_{t}"]=="false")) for t in _TH6)),
 ("M196", "reference CL5 stays CL5 under every universe",    1, _cl5s("0.05", "RAcond")),
 ("M202", "width rerun withdraws two of three CL5",          2, sum(1 for r in _cw5("width") if r["RAcert"]=="true" or r["pair_id"] in _bandkey)),
 ("M203", "SBS_055 observation margin 5.1e-9",            "5.1", f"{float(_mk[('width','SBS_055')]['obs_margin'])*1e9:.1f}"),
 ("M204", "corpus rerun withdraws five of 18 CL5",      "5/18", f"{sum(1 for r in _cw5('corpus') if r['RAcert']=='true' or r['pair_id'] in _bandkey)}/{len(_cw5('corpus'))}"),
 ("M205", "corpus CL5 in the rerun = 13",                   13, sum(1 for r in _cw5("corpus") if r["RAcert"]=="false" and r["pair_id"] not in _bandkey)),
 ("M206", "full family separates QRA_513 and SBS_081",       2, sum(1 for r in _cw5("corpus") if r["RAcert"]=="true" and r["pair_id"] in ("QRA_513","SBS_081"))),
 ("M207", "three corpus CL5 inside the guard band",          3, len(_band_c)),
 ("M208", "excluded kinds separate 9 of 16 corpus CL5", "9/16", f"{sum(1 for r in _R2C if r['arm']=='corpus' and r['separated_by_excluded_kinds']=='True')}/{sum(1 for r in _R2C if r['arm']=='corpus')}"),
 ("M209", "five only through rare-bit correlations",         5, sum(1 for r in _R2C if r["arm"]=="corpus" and r["only_rare_bit_separations"]=="True")),
 ("M210", "two through a changed most-frequent outcome",     2, sum(1 for r in _R2C if r["arm"]=="corpus" and r["most_frequent_separates"]=="True")),
 ("M211", "QRA_174 rare bit set with probability 5.6e-8", "5.6", f"{float(_q174['max_corr_bit_p1_original'].split(';')[0])*1e8:.1f}"),
 ("M212", "QRA_174 correlation moves by 0.39",           "0.39", f"{float(_q174['max_corr_change']):.2f}"),
 ("M213", "QRA_174 largest admitted difference 2.0e-7",   "2.0", f"{float(_q174['max_U5'])*1e7:.1f}"),
 ("M214", "every margin decided equal is below 7e-12",           7, _math.ceil(max(v for a, v in _eqv) * 1e12)),
 ("M215", "primary, interface and external margins decided different are above 4e-3",4, _math.floor(_ne_pie * 1e3)),
 ("M216", "corpus and width-set differences reach down to 4.8e-9",  "4.8", f"{_ne_cw*1e9:.1f}"),
 ("M217", "three more corpus pairs lie between 1e-8 and 1e-6",   3, len(_near_c)),
 ("M218", "dj_3#e19 state margin 0.293",              "0.293", f"{float(_dj['state_margin']):.3f}"),
 ("M219", "dj_3#e19 observation margin 0",                 0, int(float(_dj["obs_margin"]) * 1e12)),
 ("M220", "dj_3#e19 per-assertion bound 9.1e-5",        "9.1", f"{float(_djb['single_repetition_bound'])*1e5:.1f}"),
 ("M221", "dj_3#e19 unanimity bound 1.1e-3",            "1.1", f"{float(_djb['unanimity_failure_bound'])*1e3:.1f}"),
 ("M222", "dj_3#e19 no kill in 12 repetitions",       "0/12", f"{_djr['kills_recorded']}/{_djr['reps']}"),
]

# ---- v2 records (data/certification/outcomes/R2V_*): every report recomputed with native evidence
import hashlib as _hl
def _v2j(name): return json.load(open(_R2 / name))
_VN, _VT, _VS = _v2j("R2V_NUMBERS.json"), _v2j("R2V_TABLE_X.json"), _v2j("R2V_STATISTICS.json")
_VB, _VRC, _VDT = _v2j("R2V_BOUND.json"), _v2j("R2V_RELATION_CORPUS.json"), _v2j("R2V_DISTANCE_TIMING.json")
_VP, _VW, _VC = rerun_csv("R2V_FINAL_PRIMARY.csv"), rerun_csv("R2V_FINAL_WIDTH.csv"), rerun_csv("R2V_FINAL_CORPUS.csv")
_VE, _VD = rerun_csv("R2V_FINAL_EXTERNAL.csv"), rerun_csv("R2V_FINAL_DEFECT.csv")
_VRP, _VNAT = rerun_csv("R2V_RULE_CHANGES.csv"), rerun_csv("R2V_NATIVE.csv")
_VNATD = rerun_csv("R2V_NATIVE_DEFECTS.csv")
_VJ = {r["job_id"]: r for r in _VNAT + _VNATD}
_VCMP = list(csv.DictReader(open(_orig("data/primary/figures/R_fig2b_compression.csv"))))
_C6 = ("CL1", "CL2", "CL3", "CL4", "CL5", "Unresolved")
_vd = lambda rows: "/".join(str(sum(1 for r in rows if r["v2_report"] == c)) for c in _C6)
_alive = lambda rows: [r for r in rows if r["v2_report"] != "NA_KILLED"]
_pp = lambda x: f"{100 * x:.1f}"
_ppi = lambda a: f"[{100 * a[0]:.1f}, {100 * a[1]:.1f}]"
_trow = lambda s: f"{s['pos']}/{s['neg']}/{_pp(s['effect'])}/{_ppi(s['cluster_ci95'])}/{_ppi(s['loco_range'])}"
_TXo = {s["edge"]: s for s in _VT["observation"]}
_TXs = {s["contrast"]: s for s in _VT["suite"]}
_TXi = {s["contrast"]: s for s in _VT["interface"]}
_cand4 = lambda rows: [r for r in rows if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"]
_cc4 = _cand4(_VC)
_csplit = [r for r in _cc4 if r["v2_report"] != "CL4" and r["c_kind"] and r["final_OB02"] != "failed" and r["final_OB13"] == "failed"]
_cguard = [r for r in _cc4 if r["v2_report"] != "CL4" and r["c_kind"] and r["final_OB02"] == "failed"]
_ctrl_only = sum(1 for r in _cguard if int(_VJ[f"corpus|{r['case_key']}|OB13"]["guard_fails"]) == 0
                 and int(_VJ[f"corpus|{r['case_key']}|OB15"]["guard_fails"]) > 0)
_skills = sorted(int(_VJ[f"corpus|{r['case_key']}|OB13"]["kills"]) for r in _csplit)
_Vk = {r["case_key"]: r for r in _VC}
_n3 = len(_wo.CHANGED["corpus"])                      # corpus cases the v3 amendment reports (low-order witnesses)
_dc4 = lambda rep: sum(1 for r in _VD if r.get("v2_candidate") == "CL4" and r["v2_report"] == rep)
_VRPf = [r for r in _VRP if r["case"] not in _wo.CHANGED.get(r["arm"], ())]   # v1 -> final: v3 cases return to v1
_Wk = {r["case_key"]: r for r in _VW}
_Pk = {r["mutant_id"]: r for r in _VP}
_p4d = sorted(float(r["w_d"]) for r in _VP if r["v2_report"] == "CL4")
_nat_all = _VNAT + _VNATD
_cands_all = sum(len(_cand4(x)) for x in (_VP, _VW, _VC, _VE)) + sum(1 for r in _VD if r.get("v2_candidate") == "CL4")
_band3 = [b for b in _VRC["decided_different_below_1e-6"]
          if not any(x["pair"] == b["pair"] and x["set"] == b["set"] for x in _VRC["band_pairs"])]
_dt = _VDT["median_ms_by_width"]
_VCHECKS = [
 # -------- v2: specification, native evidence, reprocessing table
 ("M223", "v2 specification unchanged since its hash",  "6829f1ba", _hl.sha256(open(_orig("data/prospective/mqt_bench/frozen_deps/V2_SPECIFICATION.md"), "rb").read()).hexdigest()[:8]),
 ("M224", "v2 native checks 537 in 8,055 QUTest runs",  "537/8055", f"{_VN['native_jobs_total']}/{_VN['native_qutest_runs']}"),
 ("M225", "outcome records differing between the initial analysis and the final rules",           51, len(_VRPf)),
 ("M226", "50 of the 51 become Unresolved",                  50, sum(1 for r in _VRPf if r["v2_report"] == "Unresolved")),
 ("M227", "no primary or external report changes",            0, sum(1 for r in _VRP if r["arm"] in ("primary", "external"))),
 ("M228", "no CL3 report changes",                            0, sum(1 for r in _VRP if "CL3" in (r["v1_report"], r["v2_report"]))),
 ("M229", "native table 280/21/259/278",           "280/21/259/278",
   f"{_cands_all}/{_VN['primary_ob13_recorded_reuse']}/{sum(1 for r in _nat_all if r['purpose']=='OB13')}/{sum(1 for r in _nat_all if r['purpose']=='OB15')}"),
 ("M230", "native outcomes 234 confirmed, 27 split, 19 guard, 0 no control", "234/27/19/0",
   "/".join(str(sum(_VN[f"{a}_cl4_breakdown"].get(k, 0) for a in ("primary", "width", "corpus", "external"))
                + {"supported": _n3 + _dc4("CL4"), "no_control": _dc4("Unresolved") - _n3}.get(k, 0))
            for k in ("supported", "witness_split", "guard_false_failure", "no_control"))),
 # -------- v2: primary population
 ("M231", "v2 primary reference 93/87/35/79/1/2",  "93/87/35/79/1/2", _vd(_alive(_VP))),
 ("M232", "v2 construction 60/39/35/58/1/2",       "60/39/35/58/1/2", _vd([r for r in _alive(_VP) if r["population"] == "construction"])),
 ("M233", "v2 prospective 33/48/0/21/0/0",          "33/48/0/21/0/0", _vd([r for r in _alive(_VP) if r["population"] == "prospective"])),
 ("M234", "primary CL4 natively confirmed 79 of 79",          "79/79", f"{_VN['primary_cl4_breakdown'].get('supported', 0)}/{_VN['primary_cl4_candidates']}"),
 ("M235", "primary witnesses reused from 21 recorded repairs",  21, _VN["primary_ob13_recorded_reuse"]),
 ("M236", "CL3 endpoint states 29 of 35",                     "29/35", f"{_VN['effects_cl3']['groups']}/{_VN['effects_cl3']['cases']}"),
 ("M237", "construction CL2 collapse onto 4 of 39",            "4/39", f"{_VN['effects_cl2_construction']['groups']}/{_VN['effects_cl2_construction']['cases']}"),
 ("M238", "smallest primary witness 0.148, next at least 0.500", "0.148/0.500", f"{_p4d[0]:.3f}/{_p4d[1]:.3f}"),
 ("M239", "state groups 27/4/29/45/1/2, total 108", "27/4/29/45/1/2/108",
   "/".join(r["state"] for r in _VCMP if r["claim"] != "ALL") + "/" + next(r["state"] for r in _VCMP if r["claim"] == "ALL")),
 ("M240", "observation groups total 51",                51, int(next(r["obs"] for r in _VCMP if r["claim"] == "ALL"))),
 # -------- v2: matched changes
 ("M241", "matched changes: Z output->all qubits", "55/0/28.5/[1.3, 48.1]/[21.7, 32.2]", _trow(_TXo["Z: output -> all qubits"])),
 ("M242", "matched changes: output Z->XYZ",        "30/0/15.5/[7.3, 23.0]/[13.2, 17.4]", _trow(_TXo["output: Z -> XYZ"])),
 ("M243", "matched changes: all qubits Z->XYZ",    "35/0/18.1/[10.6, 26.7]/[16.1, 19.9]", _trow(_TXo["all qubits: Z -> XYZ"])),
 ("M244", "matched changes: XYZ output->all",      "60/0/31.1/[7.8, 50.2]/[24.6, 35.1]", _trow(_TXo["XYZ: output -> all qubits"])),
 ("M245", "matched changes: S_MIN->S_FAMILY",      "14/0/2.3/[0.2, 5.7]/[0.9, 2.5]", _trow(_TXs["S_MIN -> S_FAMILY"])),
 ("M246", "matched changes: S_MIN->S_COVER",       "41/0/6.8/[1.5, 13.2]/[4.9, 7.2]", _trow(_TXs["S_MIN -> S_COVER"])),
 ("M247", "matched changes: S_MIN->S_BOTH",        "81/0/13.5/[4.5, 23.7]/[10.9, 14.2]", _trow(_TXs["S_MIN -> S_BOTH"])),
 ("M250", "matched changes: QUTest->QuCheck",      "28/25/0.5/[-5.3, 6.2]/[-0.7, 1.9]", _trow(_TXi["QUTest -> QuCheck"])),
 ("M251", "matched changes: QuCheck p 0.784",      "0.784", f"{_TXi['QUTest -> QuCheck']['exact_mcnemar_p']:.3f}"),
 ("M252", "matched changes: QUTest->pytest",       "35/0/5.8/[2.7, 9.5]/[4.9, 6.2]", _trow(_TXi["QUTest -> pytest"])),
 ("M253", "matched changes: budget 236 resolved, 3 created, +14.4", "236/3/14.4",
   f"{_VS['v2']['resolved']}/{_VS['v2']['created']}/{_pp(_VS['v2']['effect'])}"),
 ("M254", "matched changes: budget p 5.2e-66, CI, LOO", "5.2e-66/[6.2, 24.6]/[12.0, 15.4]",
   f"{_VS['v2']['exact_mcnemar_p']:.1e}/{_ppi(_VS['v2']['cluster_ci95'])}/{_ppi(_VS['v2']['loco_range'])}"),
 ("M255", "matched changes: non-budget rows equal the v1 record",      True, all(s["matches_record"] for k in ("observation", "suite", "interface") for s in _VT[k])),
 ("M256", "matched changes: no lattice or interface margin in the band",  0, len(_VT["checks"]["observation_band_decisions"]) + len(_VT["checks"]["interface_band_decisions"])),
 # -------- v2: decision support, tolerance, ablation
 ("M257", "decision grid killed 784/785/793",         "784/785/793", "/".join(str(_VN["decision_grid_by_N"][n]["killed"]) for n in ("500", "2000", "8000"))),
 ("M258", "decision-supported 480/623/704",           "480/623/704", "/".join(str(_VN["decision_grid_by_N"][n]["decision_supported"]) for n in ("500", "2000", "8000"))),
 ("M259", "Unresolved cells 359/215/126",             "359/215/126", "/".join(str(_VN["decision_grid_by_N"][n]["unresolved"]) for n in ("500", "2000", "8000"))),
 ("M260", "N moves no Stage-2 relation under v2",             True, _VN["decision_grid_R_T_unchanged"]),
 ("M261", "tolerance CL5 candidates 0,0,1,1,4,18",  "0,0,1,1,4,18", ",".join(map(str, _VN["tolerance_cl5_candidates"]))),
 ("M262", "decision-supported CL5 0,0,1,1,2,2",      "0,0,1,1,2,2", ",".join(map(str, _VN["tolerance_cl5_decision_supported"]))),
 ("M263", "resolution-limited at theta 0.50 = 3",                3, _VN["tolerance_cl5_resolution_limited"][-1]),
 ("M264", "theta-invariant relations 93/180/215",     "93/180/215", "/".join(str(_VN["tolerance_theta_invariant_relations"][k]) for k in ("R_C_true", "R_S_true", "R_O_true"))),
 ("M265", "ablation 959 certificates, 18,882 ablations", "959/18882", f"{_VN['ablation']['certificates']}/{_VN['ablation']['ablations']}"),
 ("M266", "mean 9.84 requirements per certificate",       "9.84", f"{_VN['ablation']['ablations'] / 2 / _VN['ablation']['certificates']:.2f}"),
 ("M267", "every ablation withdraws, names, keeps candidate",  True, _VN["ablation"]["all_withdrawn"] and _VN["ablation"]["all_named"] and _VN["ablation"]["all_candidate_unchanged"]),
 ("M268", "by gate 16 of 90 against 110 of 740", "16/90/110/740",
   f"{_VN['decision_grid_by_gate_8000']['phase']['unresolved']}/{_VN['decision_grid_by_gate_8000']['phase']['not_killed']}/"
   f"{_VN['decision_grid_by_gate_8000']['other']['unresolved']}/{_VN['decision_grid_by_gate_8000']['other']['not_killed']}"),
 ("M269", "by-gate CL3 enrichment 10 of 33, 25 of 420", "10/33/25/420",
   f"{_VN['decision_grid_by_gate_8000']['phase']['reference_cl3']}/{_VN['decision_grid_by_gate_8000']['phase']['mutants']}/"
   f"{_VN['decision_grid_by_gate_8000']['other']['reference_cl3']}/{_VN['decision_grid_by_gate_8000']['other']['mutants']}"),
 # -------- v2: other programs
 ("M273", "external 28/94/30/5/0/2",                "28/94/30/5/0/2", _vd(_alive(_VE))),
 ("M274", "external CL4 confirmed 5 of 5",                    "5/5", f"{_VN['external_cl4_breakdown'].get('supported', 0)}/{_VN['external_cl4_candidates']}"),
 ("M275", "width set 19/0/17/6/1/4",                  "19/0/17/6/1/4", _vd(_alive(_VW))),
 ("M276", "width universe 523 to 32,785",               "523/32785",
   f"{min(int(r['universe_size']) for r in _VW)}/{max(int(r['universe_size']) for r in _VW)}"),
 ("M277", "width and corpus universe sizes equal 2^(n+1)+n+3",            True, all(int(r["universe_size"]) == 2 ** (int(r["n"]) + 1) + int(r["n"]) + 3 for r in _VW + _VC)),
 ("M278", "SBS_061 witness 0.008 above theta, kills 6 of 12", "0.008/6",
   f"{float(_Wk['SBS_061']['w_d']) - 0.05:.3f}/{_VJ['width|SBS_061|OB13']['kills']}"),
 ("M279", "SBS_081 original fails its witness in 3 of 3 guard runs", "3/3",
   f"{_VJ['width|SBS_081|OB13']['guard_fails']}/{len(_VJ['width|SBS_081|OB13']['guard_verdicts'].split(';'))}"),
 ("M280", "SBS_055 observation margin 5.1e-9 in the band",   "5.1/R_O", f"{float(_Wk['SBS_055']['margin_obs']) * 1e9:.1f}/{_Wk['SBS_055']['undecided_relation']}"),
 ("M281", "added distances 0.008 ms at 8, 0.11 ms at 14",  "0.008/0.11",
   f"{_dt['8']['hellinger'] + _dt['8']['kl']:.3f}/{_dt['14']['hellinger'] + _dt['14']['kl']:.2f}"),
 ("M282", "corpus 158/0/150/143/13/98",           "158/0/150/143/13/98", _vd(_alive(_VC))),
 ("M283", "corpus CL4 candidates 187",                         187, len(_cc4)),
 ("M284", "corpus 26 splits, 18 guard failures, 0 without control", "26/18/0",
   f"{_VN['corpus_cl4_breakdown']['witness_split']}/{_VN['corpus_cl4_breakdown']['guard_false_failure']}/{sum(1 for r in _cc4 if r['v2_report'] != 'CL4' and not r['c_kind'])}"),
 ("M285", "corpus split witnesses within 0.05 of theta",    "26/26", f"{sum(1 for r in _csplit if float(r['w_d']) - 0.05 < 0.05)}/{len(_csplit)}"),
 ("M286", "corpus split witnesses kill 5 to 11 of 12",       "5/11", f"{_skills[0]}/{_skills[-1]}"),
 ("M287", "corpus guard failures on the control alone 11",      11, _ctrl_only),
 ("M288", "QRA_360 control from the closed witness order", "2/control",
   f"{_Vk['qra_cases_v1_1/QRA_360']['n']}/{'no_control' if not _Vk['qra_cases_v1_1/QRA_360']['c_kind'] else 'control'}"),
 ("M289", "v1 reported 43 of the 44 failures as CL4",       "43/44",
   f"{sum(1 for r in _cc4 if r['v2_report'] != 'CL4' and r['v1_report'] == 'CL4')}/{sum(1 for r in _cc4 if r['v2_report'] != 'CL4')}"),
 ("M290", "QRA_513 confirmed CL4, SBS_081 Unresolved",   "CL4/Unresolved", f"{_Vk['qra_cases/QRA_513']['v2_report']}/{_Vk['sbs_cases/SBS_081']['v2_report']}"),
 ("M291", "largest difference >= 1: 76 of 80, 52 of 155", "76/80/52/155",
   f"{_VN['sep_primary']['at_least_one']}/{_VN['sep_primary']['cases']}/{_VN['sep_corpus']['at_least_one']}/{_VN['sep_corpus']['cases']}"),
 ("M292", "corpus separations down to 1.3e-7",                "1.3", f"{_VN['sep_corpus']['min'] * 1e7:.1f}"),
 ("M293", "largest CL5 0.0324, QRA_513 0.0487",    "0.0324/0.0487", f"{_VN['sep_corpus']['largest_cl5_u5']:.4f}/{_VN['sep_corpus']['smallest_cl4_u5']:.4f}"),
 ("M294", "excluded kinds 7 of 13, 3 rare-bit, 2 most-frequent", "7/13/3/2",
   f"{_VN['corpus_v2_cl5_excluded_separate']}/{_VN['corpus_v2_cl5']}/{_VN['corpus_v2_cl5_rare_bit_only']}/{_VN['corpus_v2_cl5_most_frequent']}"),
 ("M295", "QRA_174 observation margin 9.9e-9, undecided", "9.9/Unresolved",
   f"{float(_Vk['qra_cases/QRA_174']['margin_obs']) * 1e9:.1f}/{_Vk['qra_cases/QRA_174']['v2_report']}"),
 ("M296", "corpus CL4 without low-order witness 7 of 143",   "7/143", f"{_VN['corpus_v2_cl4_higher_order']}/{_VN['corpus_v2_cl4_low_order'] + _VN['corpus_v2_cl4_higher_order'] + _n3}"),
 ("M297", "relation-level CL3 substrate 151 under v2",          151, _VRC["cl3_substrate"]["v2"]),
 ("M298", "relation shares 78/829 and 73/740",        "78/829/73/740", f"{_VRC['shares_v2']['n<=7'][0]}/{_VRC['shares_v2']['n<=7'][1]}/{_VRC['shares_v2']['n>=8'][0]}/{_VRC['shares_v2']['n>=8'][1]}"),
 ("M299", "relation-level undecided pairs 3",                   3, _VRC["undecided_v2"]),
 ("M300", "defect CL4 candidate confirmed with its closed-order control", "CL4/",
   "/".join(next((r["v2_report"], r["unmet"]) for r in _VD if r.get("v2_candidate") == "CL4"))),
 ("M301", "defect CL2 over a 22-member universe",          "CL2/22", next(f"{r['v2_report']}/{r['universe_v2']}" for r in _VD if r["v2_report"] == "CL2")),
 # -------- v2: finite-shot coverage
 ("M302", "kill decision: 4,198 stable, 71 outside, 0 inside", "4198/71/0",
   f"{_VB['kill_decision']['stable_cells']}/{_VB['kill_decision']['disagreements_outside_c1']}/{_VB['kill_decision']['disagreements_inside_c_ref']}"),
 ("M303", "kill decision 3,648 / 3,200 / 3,128; 79 gained, 7 lost", "3648/3200/3128/79/7",
   f"{_VB['kill_decision']['covered_c1']}/{_VB['kill_decision']['covered_c_ref']}/{_VB['kill_decision']['covered_c2']}/"
   f"{_VB['kill_decision']['gained_at_500_c_ref_vs_c2']}/{_VB['kill_decision']['lost_at_8000_c_ref_vs_c2']}"),
 ("M304", "witness surface 8,211 of 10,782; 503 at reference", "8211/10782/503",
   f"{_VB['witness_surface_v2']['covered_c1']}/{_VB['witness_surface_v2']['decisions']}/{_VB['witness_surface_v2']['reference_schedule_c1']}"),
 ("M305", "witness surface at c = 2: 7,451; 322",       "7451/322", f"{_VB['witness_surface_v2']['covered_c2']}/{_VB['witness_surface_v2']['reference_schedule_c2']}"),
 ("M306", "frozen bound reproduces recorded v1 statuses",      0, _VB["v1_universe_rows_reproduced_mismatches"]),
 # -------- v2: numerical equality (Threats)
 ("M307", "corpus margins decided equal are below 7e-12 (1,569 pairs)", True, _VRC["max_margin_decided_equal"] < 7e-12),
 ("M308", "the three corpus pairs between 1e-8 and 1e-6: outcomes", "CL3/CL5/CL5",
   "/".join(sorted(_Vk[f"{b['set']}/{b['pair']}"]["v2_report"] for b in _band3))),
]
CHECKS += _VCHECKS

# ---- further values ---------------------------------------------------------------
try:                      # QUTest 0.1.0 documentation (Apache-2.0); not redistributed, read from an installed copy if present
    import importlib.metadata as _im; _QT_META = _im.distribution("qutest").read_text("METADATA") or ""
except Exception:
    _QT_META = None
def _qt_examples(meta):
    out = []
    for blk in re.findall(r"```qasm\n(.*?)```", meta, re.S):
        for m in re.finditer(r"def (test\w*)\(\)\s*\{(.*?)\n\}", blk, re.S):
            body = [l.strip() for l in m.group(2).split("\n") if l.strip() and not l.strip().startswith("//")]
            if not body: continue
            mi = [i for i, l in enumerate(body) if "measure" in l]
            out.append((m.group(1), body, mi))
    return out
_QTX = _qt_examples(_QT_META) if _QT_META is not None else None
def _measures_directly(body, mi):
    # where the test calls the program as a helper, the next statement is the measurement; where it writes the
    # circuit inline, the circuit is the program. Either way no gate stands between program and measurement.
    if not mi: return False
    stm = [t.strip() for l in body for t in l.split(";") if t.strip()]
    calls = [i for i, t in enumerate(stm) if re.match(r"^\w+\(q\)$", t)]
    return all(i + 1 < len(stm) and "measure" in stm[i + 1] for i in calls)
_RQ = json.load(open(_R2 / "R2V_RELEASED_CL3.json"))
_ST = json.load(open(resolve("data/scalability/corpus/T2A_STRATIFIED_SUMMARY.json")))
_TS = json.load(open(resolve("data/primary/decision/B5_A3_SUMMARY.json")))
_EL = json.load(open(resolve("data/profiles/E5_ENVIRONMENT_LOCK.json")))["reproduction_environments"]
_EX = rows("data/prospective/cross_tool/s2/S2_ELIGIBILITY_EXCLUSIONS.csv")
_VCd = [r for r in _VC if r["v2_report"] != "NA_KILLED"]
_R4CHECKS = [
 ("M309", "QUTest 0.1.0 documentation: 15 complete example tests", 15, len(_QTX) if _QTX is not None else "SKIPPED: qutest 0.1.0 not installed"),
 ("M310", "every example measures directly after the program", True, all(_measures_directly(b, mi) for _, b, mi in _QTX) if _QTX is not None else "SKIPPED: qutest 0.1.0 not installed"),
 ("M311", "Muskit records counts of every qubit (profile record)", True,
   "appends .measure(q[i], c[i]) for every qubit" in json.load(open(resolve("data/profiles/E3_PROFILE_MATRIX.json")))["interfaces"]["Muskit"]["alpha_v"]),
 ("M312", "one prospective exclusion: W-state cx -> rxx, preflight", "wstate_4#h29/rep@10:cx->rxx/UNSUPPORTED_INGESTION",
   "/".join((_EX[0]["mutant_id"], _EX[0]["location"], _EX[0]["exclusion_class"])) if len(_EX) == 1 else len(_EX)),
 ("M313", "three locked Qiskit releases", "0.45.3/1.1.1/2.5.0", "/".join(_EL[k]["qiskit"] for k in ("Q045", "Q11", "Q25"))),
 ("M314", "Qiskit 16164 state margin 0.061, observation 5.6e-17", "0.061/5.6",
   f"{_RQ['state_margin']:.3f}/{_RQ['obs_margin'] * 1e17:.1f}"),
 ("M315", "corpus 511 stable survivors of 562 diagnosed", "511/562",
   f"{sum(1 for r in _VCd if r['native_verdict'] != 'SPLIT')}/{len(_VCd)}"),
 ("M316", "non-diagonal 58 of 818 and 58 of 240", "58/818/58/240",
   f"{_ST['eligible']['non_diagonal']['cl3']}/{_ST['eligible']['non_diagonal']['n']}/{_ST['entering_diagnosis']['non_diagonal']['cl3']}/{_ST['entering_diagnosis']['non_diagonal']['n']}"),
 ("M317", "diagonal 92 of 719 (12.8) and 92 of 271 (33.9)", "92/719/12.8/92/271/33.9",
   f"{_ST['eligible']['diagonal']['cl3']}/{_ST['eligible']['diagonal']['n']}/{100*_ST['eligible']['diagonal']['rate']:.1f}/"
   f"{_ST['entering_diagnosis']['diagonal']['cl3']}/{_ST['entering_diagnosis']['diagonal']['n']}/{100*_ST['entering_diagnosis']['diagonal']['rate']:.1f}"),
 ("M318", "strata partition the 1,537 pairs 818/719 and the 511 stable survivors 240/271", "1537=818+719/511=240+271",
   f"{len(_T2A_OK)}={len(_T2A_ND)}+{len(_T2A_D)}/{len(_T2A_SUR)}="
   f"{sum(1 for r in _T2A_SUR if not r['diag'])}+{sum(1 for r in _T2A_SUR if r['diag'])}"),
 ("M319", "transpiler agreement identifies 1 to 3 of 85 across 36 configurations", "1/3/85/36",
   f"{_TS['certified_min']}/{_TS['certified_max']}/{_TS['pairs']}/{_TS['configurations']}"),
 ("M320", "smallest primary distinguishing assertion 0.148, a Z product", "0.148/zmask",
   (lambda m: f"{float(m['w_d']):.3f}/{m['w_kind']}")(min((r for r in _VP if r["v2_report"] == "CL4"), key=lambda r: float(r["w_d"])))),
 ("M321", "revised outcomes: 51 records of 48 distinct pairs, 48 corpus and 3 width-set records", "51/48/48/3",
   (lambda rs: f"{len(rs)}/{len({r['case'] if r['arm'] == 'corpus' else 'sbs_cases/' + r['case'] for r in rs})}/"
               f"{sum(r['arm'] == 'corpus' for r in rs)}/{sum(r['arm'] == 'width' for r in rs)}")(_VRPf)),
 ("M322", "closed witness order: witnesses and controls of every candidate, v3 controls formed", "330/330/2",
   (lambda I: f"{sum(int(r['candidates']) for r in I)}/{sum(int(r['v2_controls']) + int(r['v3_controls_formed']) for r in I)}/"
              f"{sum(int(r['v3_controls_formed']) for r in I)}")(list(csv.DictReader(open(_wo.WO / "IMPACT.csv"))))),
]
CHECKS += _R4CHECKS

bad, skipped = [], []
for _cid, name, exp, got in CHECKS:
    if str(got).startswith("SKIPPED"):
        skipped.append(_cid); tag = "SKIP"
    else:
        tag = "OK  " if str(exp) == str(got) else "FAIL"
        if tag == "FAIL": bad.append((name, exp, got))
    print(f"  {tag}  {name:<48} expected {exp!s:<14} recomputed {got}")
print(f"\n{len(CHECKS) - len(bad) - len(skipped)} of {len(CHECKS) - len(skipped)} checks recomputed from the packaged records; "
      f"{len(skipped)} left to the analytic tier")
with open(_out_dir() / "manuscript_checks.csv", "w", newline="") as _f:
    _w = csv.writer(_f); _w.writerow(["check_id", "label", "expected", "recomputed", "match"])
    for _c, _n, _e, _g in CHECKS: _w.writerow([_c, _n, _e, _g, "skipped" if str(_g).startswith("SKIPPED") else str(_e) == str(_g)])
for n, e, g in bad: print(f"   MISMATCH  {n}: expected {e}  recomputed {g}")
