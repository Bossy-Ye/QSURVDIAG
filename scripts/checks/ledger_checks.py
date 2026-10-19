import sys as _sys; _sys.dont_write_bytecode = True   # keep the package free of interpreter caches
"""Recompute the ledger values (engine ledger_checks in expected/expected_results.csv) from the archived records.

Writes ledger_checks.csv to QSD_OUT: id, area, quantity, unit, recomputed_value, source, method.
scripts/reproduce.py compares recomputed_value with expected/expected_results.csv.
"""
import csv, collections, json, os, re, sys

import builtins as _bi
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "lib"))
from paths import orig as _orig, out_dir as _out_dir
import witness_order as _wo
def open(p, mode="r", *a, **k):
    """Archived inputs are named by package path and checked against the manifest."""
    if "r" in mode and not any(c in mode for c in "wax+") and str(p).startswith("data/"):
        p = _orig(p)
    return _bi.open(p, mode, *a, **k)
OUT = str(_out_dir()) + "/"
rows = []


def rd(p):
    return _wo.final(p, list(csv.DictReader(open(p))))


def add(i, area, qty, unit, ms, rc, src, method, note="", status=None):
    """expected/expected_results.csv"""
    rows.append(dict(id=i, area=area, quantity=qty, unit=unit, recomputed_value=rc, source=src, method=method))


C = collections.Counter

# ------------------------------------------------------------------ primary
P = rd("data/certification/outcomes/R2V_FINAL_PRIMARY.csv")
pc = C(r["v2_report"] for r in P)
pop = C(r["population"] for r in P)
add("P01", "primary", "executable primary pairs", "mutant (program pair)", 599, len(P), "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "row count")
add("P02", "primary", "construction / prospective split", "mutant", "450/149", f"{pop['construction']}/{pop['prospective']}", "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "population column")
add("P03", "primary", "killed at baseline", "mutant", 302, pc["NA_KILLED"], "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "v2_report==NA_KILLED")
diag = [r for r in P if r["v2_report"] != "NA_KILLED"]
dpop = C(r["population"] for r in diag)
add("P04", "primary", "entering diagnosis (construction+prospective)", "mutant", "297 (195+102)", f"{len(diag)} ({dpop['construction']}+{dpop['prospective']})", "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "v2_report!=NA_KILLED")
add("P05", "primary", "CE/EIE/OL/SO/BTD/Unresolved", "mutant",
    "93/87/35/79/1/2", "/".join(str(pc[k]) for k in ("CL1", "CL2", "CL3", "CL4", "CL5", "Unresolved")), "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "v2_report counts")
add("P06", "primary", "issued outcomes", "mutant", 295, sum(pc[k] for k in ("CL1", "CL2", "CL3", "CL4", "CL5")), "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "CL1..CL5")
nv = C(r["native_verdict"] for r in P)
add("P07", "primary", "split native verdicts", "mutant", 2, nv["SPLIT"], "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "native_verdict==SPLIT")
stable = [r for r in P if r["native_verdict"] in ("KILLED", "SURVIVED")]
agree = sum(1 for r in stable if (r["R_T"] == "true") == (r["native_verdict"] == "KILLED"))
add("P08", "primary", "analytic prediction agrees with native verdict (stable pairs)", "mutant", "597 of 597", f"{agree} of {len(stable)}", "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "R_T==true iff KILLED")
cp = C(r["v2_report"] for r in P if r["population"] == "prospective")
add("P09", "primary", "prospective set has no observation limitation", "mutant", 0, cp["CL3"], "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "prospective CL3 count")
cs = len({r["subject"] for r in P if r["population"] == "construction" and r["v2_report"] == "CL3"})
add("P10", "primary", "construction subjects with an observation limitation", "program", "10 of 15", f"{cs} of {len({r['subject'] for r in P if r['population']=='construction'})}", "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "distinct subjects")
ss = len({r["subject"] for r in P if r["population"] == "construction" and r["v2_report"] == "CL4"})
add("P11", "primary", "construction subjects with a suite omission", "program", 7, ss, "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "distinct subjects")
ghz = sum(1 for r in P if r["v2_report"] == "CL4" and r["subject"].startswith("ghz"))
add("P12", "primary", "suite omissions that are GHZ mutants", "mutant", 54, ghz, "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "subject prefix ghz")

# ------------------------------------------------------------------ contract (RQ2)
X = {r["pair"]: r for r in rd("data/certification/outcomes/R2_MARGINS_EXT.csv") if r["arm"] == "primary"}
LO = 1e-10
issued = [r for r in P if r["v2_report"] in ("CL1", "CL2", "CL3", "CL4", "CL5")]
uni_ce = sum(1 for r in issued if float(X[r["mutant_id"]]["unitary_margin"]) < LO)
add("C01", "contract", "contract-equivalent under declared vs unitary contract", "mutant", "93 vs 4", f"{pc['CL1']} vs {uni_ce}", "data/certification/outcomes/R2V_FINAL_PRIMARY.csv; data/certification/outcomes/R2_MARGINS_EXT.csv", "unitary_margin < 1e-10 among issued")
dep = sum(1 for r in issued if r["v2_report"] == "CL1" and float(X[r["mutant_id"]]["unitary_margin"]) >= LO)
add("C02", "contract", "contract-dependent survivors (same executed-input state, different unitary)", "mutant", 89, dep, "same", "CL1 under declared with unitary margin >= 1e-10")
rs = sum(1 for r in diag if r["R_S"] == "true")
add("C03", "contract", "R_S true among diagnosed (CE+EIE)", "mutant", 180, rs, "data/certification/outcomes/R2V_FINAL_PRIMARY.csv", "R_S==true")

# ------------------------------------------------------------------ interface / suites / observation (RQ3)
IF = {r["mutant_id"]: r for r in rd("data/primary/records/T1_4_INTERFACE_599.csv")}
cl3 = [r["mutant_id"] for r in P if r["v2_report"] == "CL3"]
cl4 = [r["mutant_id"] for r in P if r["v2_report"] == "CL4"]
gain = sum(1 for m in cl3 if IF[m]["R_O_QuCheck"] == "False")
lose = sum(1 for m in cl4 if IF[m]["R_O_QuCheck"] == "True")
add("I01", "interface", "QuCheck gains / loses vs QUTest", "mutant", "28/25", f"{gain}/{lose}", "data/primary/records/T1_4_INTERFACE_599.csv", "R_O_QuCheck over v2 CL3 / CL4")
add("I02", "interface", "Muskit keeps all OL; pytest admits none", "mutant", "35/0",
    f"{sum(1 for m in cl3 if IF[m]['R_O_QUTest']=='True')}/{sum(1 for m in cl3 if IF[m]['R_O_pytest']=='True')}", "data/primary/records/T1_4_INTERFACE_599.csv", "R_O_QUTest / R_O_pytest on CL3 (Muskit shares QUTest's joint-Z observation)")
A1G = rd("data/primary/records/599_B5_A1G_POPULATION.csv")
k = lambda su, S_: sum(1 for r in A1G if r["suite"] == su and r["mutant_id"] in S_ and r["outcome"] == "KILLED")
add("S01", "suite", "SO killed by correlator / all-qubit / combined suites", "mutant", "12/41/79",
    f"{k('S_FAMILY', set(cl4))}/{k('S_COVER', set(cl4))}/{k('S_BOTH', set(cl4))}", "data/primary/records/599_B5_A1G_POPULATION.csv", "native suite outcomes over v2 CL4")
add("S02", "suite", "OL killed by any systematic suite", "mutant", 0,
    k('S_FAMILY', set(cl3)) + k('S_COVER', set(cl3)) + k('S_BOTH', set(cl3)), "same", "sum over three suites")
TX = json.load(open("data/certification/outcomes/R2V_TABLE_X.json"))
obs = {e["edge"]: e for e in TX["observation"]}
add("O01", "observation", "OL under Z-output -> Z-all", "mutant (193 stable construction)", "90 -> 35",
    f"{obs['Z: output -> all qubits']['cl3_from']} -> {obs['Z: output -> all qubits']['cl3_to']}", "data/certification/outcomes/R2V_TABLE_X.json", "derived record", status="VERIFIED_DERIVED")
TXD = rd("data/certification/outcomes/R2V_TABLE_X_DECISIONS.csv")
con = [r for r in TXD if r.get("part") in ("construction", "observation") or True]
def olcount(col):
    return sum(1 for r in TXD if r[col] == "true" and r["R_S_v2"] == "false")
add("O02", "observation", "OL count Z-output / Z-all / XYZ-output / XYZ-all (rows of R2V_TABLE_X_DECISIONS)", "mutant",
    "90/35/60/0", "/".join(str(olcount(c)) for c in ("R_O_v2_Z_output", "R_O_v2_Z_all", "R_O_v2_XYZ_output", "R_O_v2_XYZ_all")),
    "data/certification/outcomes/R2V_TABLE_X_DECISIONS.csv", "R_O true and R_S false per observation column", f"rows={len(TXD)}")
entered = sum(1 for r in TXD if r["R_O_v2_Z_all"] == "true" and r["R_O_v2_Z_output"] == "false")
add("O03", "observation", "pairs entering OL along a refinement (Z-output -> Z-all)", "mutant", 0, entered, "data/certification/outcomes/R2V_TABLE_X_DECISIONS.csv", "R_O true at finer, false at coarser")

# ------------------------------------------------------------------ decision grid (RQ3 budget)
GR = rd("data/certification/outcomes/R2V_DECISION_GRID.csv")
add("D01", "decision", "decision cells", "pair x (theta,N)", "4,869", f"{len(GR):,}", "data/certification/outcomes/R2V_DECISION_GRID.csv", "row count")
st = [r for r in GR if r["native_verdict"] in ("KILLED", "SURVIVED")]
add("D02", "decision", "executed cells with a stable native verdict", "cell", "4,198", f"{len(st):,}", "same", "KILLED+SURVIVED")
SH = rd("data/primary/records/599_B2_SHOT_FRESH.csv")
sh_st = [r for r in SH if r["native_verdict"] in ("KILLED", "SURVIVED")]
dis = [r for r in sh_st if r["agree"] == "False"]
dis_g = [r for r in dis if r["guaranteed"] == "True"]
add("D03", "decision", "stable cells disagreeing with the ideal prediction / of which covered by the bound", "cell", "71 / 0",
    f"{len(dis)} / {len(dis_g)}", "data/primary/records/599_B2_SHOT_FRESH.csv", "agree==False; guaranteed==True", f"stable cells in this file={len(sh_st)}")
byN = collections.defaultdict(C)
for r in GR:
    byN[r["N"]][r["v2_status"]] += 1
ur = {n: sum(v for kk, v in byN[n].items() if kk.startswith("unresolved")) for n in byN}
add("D04", "decision", "Unresolved cells fall as N grows (500/2000/8000)", "cell", "359/215/126 (falls)", f"{ur['500']}/{ur['2000']}/{ur['8000']} (falls)", "data/certification/outcomes/R2V_DECISION_GRID.csv", "unresolved_* by N")
TB = TX["budget"]["v2"]
add("D05", "decision", "N 500->8000 resolved / created", "cell", "236 / 3", f"{TB['resolved']} / {TB['created']}", "data/certification/outcomes/R2V_TABLE_X.json", "derived record", status="VERIFIED_DERIVED")
AB = rd("data/certification/outcomes/R2V_ABLATION.csv")
add("D06", "decision", "ablations withdraw outcome, name item, keep candidate", "ablation", "18882 of 18882",
    f"{sum(r['withdrawn']=='True' and r['named']=='True' and r['candidate_unchanged']=='True' for r in AB)} of {len(AB)}", "data/certification/outcomes/R2V_ABLATION.csv", "all three flags True")

# ------------------------------------------------------------------ RQ4 transfer
TR = rd("data/interventions/transfer/B5_A4B_REPAIR_TRANSFER.csv")
t = C((r["subject"], r["outcome"], r["qutest_witness_expressible"]) for r in TR)
add("H07", "rq4", "QuCheck transfer same / another / none (analytic)", "case", "8/7/6",
    f"{t[('toffoli_barenco_5','WITNESS_EXISTS','True')]}/{t[('simon_4','WITNESS_EXISTS','False')]}/{t[('simon_4','NO_WITNESS_ABOVE_THETA','False')]}",
    "data/interventions/transfer/B5_A4B_REPAIR_TRANSFER.csv", "outcome x expressible", "all 8 Toffoli; 7 and 6 Simon")
SQ = {r["mutant_id"]: r for r in rd("data/prospective/cross_tool/s3/S3_QUCHECK_RESULTS.csv")}
ids21 = [r["mutant_id"] for r in P if r["population"] == "prospective" and r["v2_report"] == "CL4"]
add("H08", "rq4", "finite-shot QuCheck equality check (output register, 30 July) detected", "case", "5 of 21",
    f"{sum(SQ[i]['verdict_primary']=='DETECTED' for i in ids21)} of {len(ids21)}", "data/prospective/cross_tool/s3/S3_QUCHECK_RESULTS.csv", "verdict_primary over the 21 prospective SO")
A2 = rd("data/interventions/transfer/B5_A2_QUCHECK_REPAIR.csv")
add("H09", "rq4", "analytic transfer over output register only (2 Sept): witness exists", "case", "5 of 21",
    f"{sum(r['outcome']=='WITNESS_EXISTS' for r in A2)} of {sum(not r['outcome'].startswith('NOT_EVALUABLE') for r in A2)}", "data/interventions/transfer/B5_A2_QUCHECK_REPAIR.csv", "outcome")

# ------------------------------------------------------------------ native evidence and v1 -> final (v2 records with the v3 amendment)
FIN = {a: rd(f"data/certification/outcomes/R2V_FINAL_{a}.csv") for a in ("PRIMARY", "WIDTH", "CORPUS", "EXTERNAL")}
FIN["DEFECT"] = rd("data/certification/outcomes/R2V_FINAL_DEFECT.csv")
cand = {a: [r for r in v if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"] for a, v in FIN.items()}
conf = {a: sum(1 for r in v if r["v2_report"] == "CL4") for a, v in cand.items()}
add("N01", "certification", "SO candidates primary/width/corpus/external/defect", "case", "79/8/187/5/1",
    "/".join(str(len(cand[a])) for a in ("PRIMARY", "WIDTH", "CORPUS", "EXTERNAL", "DEFECT")), "data/certification/outcomes/R2V_FINAL_*.csv", "v2_candidate==CL4 and OB03 satisfied (stable survival)")
add("N02", "certification", "confirmed (issued CL4)", "case", "79/6/143/5/1",
    "/".join(str(conf[a]) for a in ("PRIMARY", "WIDTH", "CORPUS", "EXTERNAL", "DEFECT")), "same", "v2_report==CL4")
tc = sum(len(v) for v in cand.values()); tf = sum(conf.values())
add("N03", "certification", "total candidates / withdrawn", "case", "280 / 46", f"{tc} / {tc - tf}", "same", "candidates minus confirmed")
RP = [r for r in rd("data/certification/outcomes/R2V_RULE_CHANGES.csv") if r["case"] not in _wo.CHANGED.get(r["arm"], ())]
add("N04", "certification", "pair outcomes differing v1->final / to Unresolved / to CL4", "pair", "51 / 50 / 1",
    f"{len(RP)} / {sum(r['v2_report']=='Unresolved' for r in RP)} / {sum(r['v2_report']=='CL4' for r in RP)}", "data/certification/outcomes/R2V_RULE_CHANGES.csv; data/certification/witness_order/IMPACT.csv", "row counts, less the v3 cases that return to their v1 outcome")
NAT = rd("data/certification/outcomes/R2V_NATIVE.csv") + rd("data/certification/outcomes/R2V_NATIVE_DEFECTS.csv")
add("N05", "certification", "native confirmation + control checks", "check", 537, len(NAT), "data/certification/outcomes/R2V_NATIVE.csv; data/certification/outcomes/R2V_NATIVE_DEFECTS.csv", "row count")
runs = sum(len(r["verdicts"].split(";")) + len(r["guard_verdicts"].split(";")) for r in NAT)
add("N06", "certification", "QUTest runs in native evidence", "run", "8,055", f"{runs:,}", "data/certification/outcomes/R2V_NATIVE.csv", "len(verdicts)+len(guard_verdicts)")
N3 = list(_wo.NATIVE.values())
add("N07", "certification", "v3 native checks / QUTest runs / controls satisfied", "check", "4 / 60 / 2",
    f"{len(N3)} / {sum(len(r['verdicts'].split(';')) + len(r['guard_verdicts'].split(';')) for r in N3)} / {sum(r['purpose'] == 'OB15' and r['status'] == 'satisfied' for r in N3)}",
    "data/certification/witness_order/NATIVE_RUNS.csv", "row count; len(verdicts)+len(guard_verdicts); OB15 status")

# ------------------------------------------------------------------ external
E = FIN["EXTERNAL"]; ec = C(r["v2_report"] for r in E)
add("E01", "external", "mutants / killed / diagnosed", "mutant", "270/111/159", f"{len(E)}/{ec['NA_KILLED']}/{len(E)-ec['NA_KILLED']}", "data/certification/outcomes/R2V_FINAL_EXTERNAL.csv", "counts")
add("E02", "external", "CE/EIE/OL/SO/BTD/Unresolved", "mutant", "28/94/30/5/0/2", "/".join(str(ec[k]) for k in ("CL1", "CL2", "CL3", "CL4", "CL5", "Unresolved")), "same", "v2_report")
est = [r for r in E if r["native_verdict"] in ("KILLED", "SURVIVED")]
add("E03", "external", "analytic and executed verdict agree (stable)", "mutant", 268,
    sum(1 for r in est if (r["R_T"] == "true") == (r["native_verdict"] == "KILLED")), "same", "R_T vs native", f"stable={len(est)}")
AL = {r["mutant_id"]: r for r in rd("data/external/cohort/EXTERNAL_ALLOCATION.csv")}
add("E04", "external", "first-gate mutants / distinct (program, site)", "mutant / site", "244 / 16",
    f"{sum(int(r['anchor_index'])==0 for r in AL.values())} / {len({(r['subject'],int(r['anchor_index'])) for r in AL.values()})}", "data/external/cohort/EXTERNAL_ALLOCATION.csv", "anchor_index==0")
add("E05", "external", "OL at the first gate / programs with OL", "mutant / program", "30 / 9",
    f"{sum(1 for r in E if r['v2_report']=='CL3' and int(AL[r['case']]['anchor_index'])==0)} / {len({AL[r['case']]['subject'] for r in E if r['v2_report']=='CL3'})}", "data/external/cohort/EXTERNAL_ALLOCATION.csv; data/certification/outcomes/R2V_FINAL_EXTERNAL.csv", "join")

# ------------------------------------------------------------------ width set
Wd = FIN["WIDTH"]; wc = C(r["v2_report"] for r in Wd)
add("W01", "width", "executed / diagnosed / issued / Unresolved", "pair", "143/47/43/4",
    f"{len(Wd)}/{len(Wd)-wc['NA_KILLED']}/{len(Wd)-wc['NA_KILLED']-wc['Unresolved']}/{wc['Unresolved']}", "data/certification/outcomes/R2V_FINAL_WIDTH.csv", "counts", "listed 162 not in this file")

# ------------------------------------------------------------------ corpus
Co = FIN["CORPUS"]; cc = C(r["v2_report"] for r in Co)
add("K01", "corpus", "pairs <=14 qubits / killed / diagnosed", "pair", "1,537/975/562", f"{len(Co):,}/{cc['NA_KILLED']}/{len(Co)-cc['NA_KILLED']}", "data/certification/outcomes/R2V_FINAL_CORPUS.csv", "counts")
add("K02", "corpus", "CE/OL/SO/BTD/Unresolved", "pair", "158/150/143/13/98", "/".join(str(cc[k]) for k in ("CL1", "CL3", "CL4", "CL5", "Unresolved")), "same", "v2_report")
un = [r for r in Co if r["v2_report"] == "Unresolved"]
spl = sum(1 for r in un if r["native_verdict"] == "SPLIT")
add("K03", "corpus", "Unresolved: split / undecided margin / failed SO candidates", "pair", "51/3/44",
    f"{spl}/{sum(1 for r in un if r['unmet'].startswith('relation R_') and 'inconsistent' not in r['unmet'])}/{sum(1 for r in un if r['v2_candidate']=='CL4' and r['native_verdict']!='SPLIT')}",
    "data/certification/outcomes/R2V_FINAL_CORPUS.csv", "native_verdict / unmet / candidate", "split also includes candidate splits; see note in ledger discussion")
add("K04", "corpus", "certified OL share", "pair", "150/1,537 = 9.8%", f"{cc['CL3']}/{len(Co):,} = {100*cc['CL3']/len(Co):.1f}%", "same", "ratio")

# ------------------------------------------------------------------ defects
D = FIN["DEFECT"]
add("F01", "defects", "eligible for the QUTest profile / killed / CE-EIE / SO / Unresolved", "defect", "4/2/1/1/0",
    f"{len(D)}/{sum(r['v2_report']=='NA_KILLED' for r in D)}/{sum(r['v2_report']=='CL2' for r in D)}/{sum(r['v2_report']=='CL4' for r in D)}/{sum(r['v2_report']=='Unresolved' for r in D)}", "data/certification/outcomes/R2V_FINAL_DEFECT.csv", "rows")

GA = rd("data/primary/records/599_B5_A1K_GHZ_CONTRACT_AUDIT.csv")
add("P13", "primary", "GHZ SO killed under full-string register (79 -> 47)", "mutant", 32, sum(r["moved"] == "True" and r["declared_report"] == "CL4" for r in GA), "data/primary/records/599_B5_A1K_GHZ_CONTRACT_AUDIT.csv", "moved CL4 -> NA_KILLED")
EL = {r["case_set"] + "/" + r["pair_id"]: r for r in rd("data/scalability/corpus/T2A_ELIGIBILITY.csv")}
sv = [r for r in Co if r["native_verdict"] == "SURVIVED"]
nd = [r for r in sv if EL[r["case"]]["diagonal_stratum"] == "False"]; dg = [r for r in sv if EL[r["case"]]["diagonal_stratum"] == "True"]
add("K05", "corpus", "OL among stable survivors: non-diagonal / diagonal stratum", "pair", "58/240 ; 92/271",
    f"{sum(r['v2_report']=='CL3' for r in nd)}/{len(nd)} ; {sum(r['v2_report']=='CL3' for r in dg)}/{len(dg)}", "data/certification/outcomes/R2V_FINAL_CORPUS.csv; data/scalability/corpus/T2A_ELIGIBILITY.csv", "diagonal_stratum join")
EN = json.load(open("data/scalability/corpus/T3_1_ENTAILED_VS_CONTINGENT.json"))
add("K06", "corpus", "OL meeting the diagonal sufficient condition / not", "pair", "54 / 96", f"{EN['entailed']['cl3']} / {EN['not_entailed']['cl3']}", "data/scalability/corpus/T3_1_ENTAILED_VS_CONTINGENT.json", "derived record", status="VERIFIED_DERIVED")
RC = json.load(open("data/certification/outcomes/R2V_RELATION_CORPUS.json"))
sh = RC["shares_v2"]
add("K07", "corpus", "relation-level OL share n<=7 / n>=8", "pair", "9.4% / 9.9%", f"{100*sh['n<=7'][0]/sh['n<=7'][1]:.1f}% / {100*sh['n>=8'][0]/sh['n>=8'][1]:.1f}%", "data/certification/outcomes/R2V_RELATION_CORPUS.json", "derived record", status="VERIFIED_DERIVED")
DF = rd("data/external/defects/B3_REAL_DEFECTS_FRESH.csv"); dd = C(r["evidence_depth"] for r in DF)
add("F02", "defects", "defects / reproduced in a locked release", "defect", "42 / 32", f"{len(DF)} / {sum(r['reproduction']=='REPRODUCED' for r in DF)}", "data/external/defects/B3_REAL_DEFECTS_FRESH.csv", "rows")
add("F03", "defects", "evidence depth: not repr. / tool / profile / relation / issued", "defect", "10/8/10/12/2",
    f"{dd['NOT_REPRODUCIBLE']}/{dd['NATIVE_REPRODUCTION_ONLY']}/{dd['PROFILE_ONLY']}/{dd['RELATION_LEVEL']}/{dd['FULL_CERTIFICATION']}", "same", "evidence_depth")
RQ2 = json.load(open("data/primary/records/T1_4_RQ2.json"))
add("C04", "contract", "movers between declared and unitary contract (cross-check)", "mutant", 89, RQ2["movers"], "data/primary/records/T1_4_RQ2.json", "derived record", status="VERIFIED_DERIVED")

# ------------------------------------------------------------------ sites
S2 = rd("data/prospective/mqt_bench/frozen_deps/S2_GENERATED_MUTANTS.csv")
add("Z01", "sites", "S2 prospective first-gate / mutants / distinct sites", "mutant / site", "140/150/9",
    f"{sum(int(r['anchor_index'])==0 for r in S2)}/{len(S2)}/{len({(r['subject'],int(r['anchor_index'])) for r in S2})}", "data/prospective/mqt_bench/frozen_deps/S2_GENERATED_MUTANTS.csv", "anchor_index")
CON = rd("data/prospective/mqt_bench/frozen_deps/MUTANT_POPULATION.csv")
add("Z02", "sites", "construction distinct (program, site)", "site", 214,
    len({(r['program'], int(re.search(r'@(\d+)', r['location']).group(1))) for r in CON}), "data/prospective/mqt_bench/frozen_deps/MUTANT_POPULATION.csv", "location index")
MM = rd("data/prospective/mqt_bench/population/MUTANT_MANIFEST.csv")
add("Z03", "sites", "MQT first-gate / distinct sites", "mutant / site", "68/22",
    f"{sum(int(r['anchor_index'])==0 for r in MM)}/{len({(r['subject'],int(r['anchor_index'])) for r in MM})}", "data/prospective/mqt_bench/population/MUTANT_MANIFEST.csv", "anchor_index")

# ------------------------------------------------------------------ MQT prospective
MC = rd("data/prospective/mqt_bench/records/analysis/PASS3C_CASES.csv")
mc = C(r["v2_report"] for r in MC)
add("M01", "mqt", "mutants / killed / diagnosed", "mutant", "120/64/56", f"{len(MC)}/{mc['NA_KILLED']}/{len(MC)-mc['NA_KILLED']}", "data/prospective/mqt_bench/records/analysis/PASS3C_CASES.csv", "counts")
add("M02", "mqt", "CE/EIE/OL/SO/BTD/Unresolved", "mutant", "14/10/7/22/0/3", "/".join(str(mc[k]) for k in ("CL1", "CL2", "CL3", "CL4", "CL5", "Unresolved")), "same", "v2_report")
mcand = [r for r in MC if r["v2_candidate"] == "CL4"]
add("M03", "mqt", "SO candidates / certified / withheld", "mutant", "23/22/1", f"{len(mcand)}/{sum(r['v2_report']=='CL4' for r in mcand)}/{sum(r['v2_report']!='CL4' for r in mcand)}", "same", "candidate CL4")
cert = [r for r in mcand if r["v2_report"] == "CL4"]
add("M04", "mqt", "certified repairs killing 12/12 at fresh seeds", "mutant", 22, sum(r["d1_mutant_kills_of_12"] == "12" for r in cert), "data/prospective/mqt_bench/records/stage_d/D1_REPAIR.csv; data/prospective/mqt_bench/records/analysis/PASS3C_CASES.csv", "d1 kills")
add("M05", "mqt", "distinct repaired suites among certified", "repaired suite", 4, len({(r['subject'], r['witness_key']) for r in cert}), "same", "(subject, witness)")
add("M06", "mqt", "original false failures across D1 (sum)", "run", 1, sum(int(r["d1_original_false_failures_of_12"]) for r in mcand), "same", "sum over candidates")
wh = [r for r in mcand if r["v2_report"] != "CL4"][0]
add("M07", "mqt", "withheld: confirmation / control / validation kills", "run", "9/4/11", f"{wh['ob13_kills_of_12']}/{wh['ob15_kills_of_12']}/{wh['d1_mutant_kills_of_12']}", "same", "withheld row")
add("M08", "mqt", "OL rerun consistent", "mutant", "7/7", f"{sum(r['d2_outcome']=='consistent' for r in MC)}/{mc['CL3']}", "data/prospective/mqt_bench/records/stage_d/D2_OBSERVATION.csv; data/prospective/mqt_bench/records/analysis/PASS3C_CASES.csv", "d2_outcome")
add("M09", "mqt", "bound covers SO kill / guard", "mutant", "19/0", f"{sum(r['bound_b13']=='True' for r in mcand)}/{sum(r['bound_guard']=='True' for r in mcand)}", "same", "b13 / bgw")


# ------------------------------------------------------------------ guards
GE = rd("data/primary/suite_guards/B5_A1B_GUARD_EXACT.csv")
add("G01", "guards", "suite cells failing the guard: sampled ref (any fail / >1 of 12) ; exact ref (any fail / >1 of 12)", "subject x suite cell", "10/7 ; 9/0",
    f"{sum(int(r['sampled_ref_false_fails'])>0 for r in GE)}/{sum(int(r['sampled_ref_false_fails'])>1 for r in GE)} ; {sum(int(r['exact_ref_false_fails'])>0 for r in GE)}/{sum(int(r['exact_ref_false_fails'])>1 for r in GE)}",
    "data/primary/suite_guards/B5_A1B_GUARD_EXACT.csv", "false-fail counts")

# ------------------------------------------------------------------ write
with open(OUT + "ledger_checks.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    print(f"{r['id']:4s} {r['recomputed_value']!s:28s} {r['quantity']}")
