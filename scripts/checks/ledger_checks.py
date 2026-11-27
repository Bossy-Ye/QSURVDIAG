"""Counts by population and record (checks L-* of expected/values.csv), recomputed from the archived records.
"""

import csv, json, re, sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import witness_order
from paths import CATALOGUE, archived, out_dir

OUTCOMES = "data/certification/outcomes/"
PRIMARY = OUTCOMES + "R2V_FINAL_PRIMARY.csv"
WIDTH = OUTCOMES + "R2V_FINAL_WIDTH.csv"
CORPUS = OUTCOMES + "R2V_FINAL_CORPUS.csv"
EXTERNAL = OUTCOMES + "R2V_FINAL_EXTERNAL.csv"
DEFECT = OUTCOMES + "R2V_FINAL_DEFECT.csv"
MARGINS = OUTCOMES + "R2_MARGINS_EXT.csv"
MATCHED = OUTCOMES + "R2V_TABLE_X.json"
MATCHED_DECISIONS = OUTCOMES + "R2V_TABLE_X_DECISIONS.csv"
GRID = OUTCOMES + "R2V_DECISION_GRID.csv"
ABLATION = OUTCOMES + "R2V_ABLATION.csv"
RULE_CHANGES = OUTCOMES + "R2V_RULE_CHANGES.csv"
NATIVE = OUTCOMES + "R2V_NATIVE.csv"
NATIVE_DEFECTS = OUTCOMES + "R2V_NATIVE_DEFECTS.csv"
RELATION_CORPUS = OUTCOMES + "R2V_RELATION_CORPUS.json"
IMPACT = "data/certification/witness_order/IMPACT.csv"
CLOSED_ORDER_RUNS = "data/certification/witness_order/NATIVE_RUNS.csv"
PROFILES = "data/primary/records/T1_4_INTERFACE_599.csv"
CONTRACT_MOVERS = "data/primary/records/T1_4_RQ2.json"
SUITE_RUNS = "data/primary/records/599_B5_A1G_POPULATION.csv"
SHOT_CELLS = "data/primary/records/599_B2_SHOT_FRESH.csv"
GHZ_REGISTER = "data/primary/records/599_B5_A1K_GHZ_CONTRACT_AUDIT.csv"
SUITE_GUARDS = "data/primary/suite_guards/B5_A1B_GUARD_EXACT.csv"
TRANSFER = "data/interventions/transfer/B5_A4B_REPAIR_TRANSFER.csv"
TRANSFER_REGISTER = "data/interventions/transfer/B5_A2_QUCHECK_REPAIR.csv"
QUCHECK_RUNS = "data/prospective/cross_tool/results/S3_QUCHECK_RESULTS.csv"
ALLOCATION = "data/external/cohort/EXTERNAL_ALLOCATION.csv"
DEFECTS = "data/external/defects/B3_REAL_DEFECTS_FRESH.csv"
ELIGIBILITY = "data/scalability/corpus/T2A_ELIGIBILITY.csv"
ENTAILMENT = "data/scalability/corpus/T3_1_ENTAILED_VS_CONTINGENT.json"
OTHER_MUTANTS = "data/prospective/mqt_bench/frozen_deps/S2_GENERATED_MUTANTS.csv"
DEVELOPMENT_MUTANTS = "data/prospective/mqt_bench/frozen_deps/MUTANT_POPULATION.csv"
MQT_MUTANTS = "data/prospective/mqt_bench/population/MUTANT_MANIFEST.csv"
MQT_CASES = "data/prospective/mqt_bench/records/analysis/PASS3C_CASES.csv"
MQT_REPAIR = "data/prospective/mqt_bench/records/stage_d/D1_REPAIR.csv"
MQT_OBSERVATION = "data/prospective/mqt_bench/records/stage_d/D2_OBSERVATION.csv"

REPORTED = ("CL1", "CL2", "CL3", "CL4", "CL5")
POPULATIONS = (PRIMARY, WIDTH, CORPUS, EXTERNAL, DEFECT)
ledger = []


def rows(path):
    with open(archived(path)) as f:
        return witness_order.final(path, list(csv.DictReader(f)))


def load(path):
    with open(archived(path)) as f:
        return json.load(f)


def add(cid, unit, value, source, method):
    area, quantity = CATALOGUE["L-" + cid]["label"].split(": ", 1)
    ledger.append(
        {
            "id": cid,
            "area": area,
            "quantity": quantity,
            "unit": unit,
            "recomputed_value": value,
            "source": source,
            "method": method,
        }
    )


def counts(rs, column="v2_report"):
    return Counter(r[column] for r in rs)


def spread(rs, keys=REPORTED + ("Unresolved",)):
    c = counts(rs)
    return "/".join(str(c[k]) for k in keys)


def stable(rs):
    return [r for r in rs if r["native_verdict"] in ("KILLED", "SURVIVED")]


def predicted(rs):
    return sum(1 for r in stable(rs) if (r["R_T"] == "true") == (r["native_verdict"] == "KILLED"))


def sites(rs, program="subject"):
    return len({(r[program], int(r["anchor_index"])) for r in rs})


def first_gate(rs):
    return sum(int(r["anchor_index"]) == 0 for r in rs)


def qutest_runs(rs):
    return sum(len(r["verdicts"].split(";")) + len(r["guard_verdicts"].split(";")) for r in rs)


primary = rows(PRIMARY)
outcome = counts(primary)
population = counts(primary, "population")
diagnosed = [r for r in primary if r["v2_report"] != "NA_KILLED"]
diagnosed_in = counts(diagnosed, "population")
development = [r for r in primary if r["population"] == "construction"]
subjects = lambda rs, report: {r["subject"] for r in rs if r["v2_report"] == report}
add("P01", "mutant (program pair)", len(primary), PRIMARY, "row count")
add("P02", "mutant", f"{population['construction']}/{population['prospective']}", PRIMARY, "population column")
add("P03", "mutant", outcome["NA_KILLED"], PRIMARY, "v2_report==NA_KILLED")
add(
    "P04",
    "mutant",
    f"{len(diagnosed)} ({diagnosed_in['construction']}+{diagnosed_in['prospective']})",
    PRIMARY,
    "v2_report!=NA_KILLED",
)
add("P05", "mutant", spread(primary), PRIMARY, "v2_report counts")
add("P06", "mutant", sum(outcome[k] for k in REPORTED), PRIMARY, "CL1..CL5")
add("P07", "mutant", counts(primary, "native_verdict")["SPLIT"], PRIMARY, "native_verdict==SPLIT")
add("P08", "mutant", f"{predicted(primary)} of {len(stable(primary))}", PRIMARY, "R_T==true iff KILLED")
add(
    "P09",
    "mutant",
    counts(r for r in primary if r["population"] == "prospective")["CL3"],
    PRIMARY,
    "prospective CL3 count",
)
add(
    "P10",
    "program",
    f"{len(subjects(development, 'CL3'))} of {len({r['subject'] for r in development})}",
    PRIMARY,
    "distinct subjects",
)
add("P11", "program", len(subjects(development, "CL4")), PRIMARY, "distinct subjects")
add(
    "P12",
    "mutant",
    sum(1 for r in primary if r["v2_report"] == "CL4" and r["subject"].startswith("ghz")),
    PRIMARY,
    "subject prefix ghz",
)

unitary_margin = {r["pair"]: float(r["unitary_margin"]) for r in rows(MARGINS) if r["arm"] == "primary"}
reported = [r for r in primary if r["v2_report"] in REPORTED]
add(
    "C01",
    "mutant",
    f"{outcome['CL1']} vs {sum(1 for r in reported if unitary_margin[r['mutant_id']] < 1e-10)}",
    f"{PRIMARY}; {MARGINS}",
    "unitary_margin < 1e-10 among issued",
)
add(
    "C02",
    "mutant",
    sum(1 for r in reported if r["v2_report"] == "CL1" and unitary_margin[r["mutant_id"]] >= 1e-10),
    "same",
    "CL1 under declared with unitary margin >= 1e-10",
)
add("C03", "mutant", sum(1 for r in diagnosed if r["R_S"] == "true"), PRIMARY, "R_S==true")

profile = {r["mutant_id"]: r for r in rows(PROFILES)}
ol = [r["mutant_id"] for r in primary if r["v2_report"] == "CL3"]
so = [r["mutant_id"] for r in primary if r["v2_report"] == "CL4"]
add(
    "I01",
    "mutant",
    f"{sum(1 for m in ol if profile[m]['R_O_QuCheck'] == 'False')}/"
    f"{sum(1 for m in so if profile[m]['R_O_QuCheck'] == 'True')}",
    PROFILES,
    "R_O_QuCheck over v2 CL3 / CL4",
)
add(
    "I02",
    "mutant",
    f"{sum(1 for m in ol if profile[m]['R_O_QUTest'] == 'True')}/"
    f"{sum(1 for m in ol if profile[m]['R_O_pytest'] == 'True')}",
    PROFILES,
    "R_O_QUTest / R_O_pytest on CL3 (Muskit shares QUTest's joint-Z observation)",
)
suite_runs = rows(SUITE_RUNS)
killed = lambda suite, ids: sum(
    1 for r in suite_runs if r["suite"] == suite and r["mutant_id"] in ids and r["outcome"] == "KILLED"
)
SUITES = ("S_FAMILY", "S_COVER", "S_BOTH")
add(
    "S01",
    "mutant",
    "/".join(str(killed(s, set(so))) for s in SUITES),
    SUITE_RUNS,
    "native suite outcomes over v2 CL4",
)
add("S02", "mutant", sum(killed(s, set(ol)) for s in SUITES), "same", "sum over three suites")
matched = load(MATCHED)
z_refinement = next(e for e in matched["observation"] if e["edge"] == "Z: output -> all qubits")
add(
    "O01",
    "mutant (193 stable construction)",
    f"{z_refinement['cl3_from']} -> {z_refinement['cl3_to']}",
    MATCHED,
    "derived record",
)
decisions = rows(MATCHED_DECISIONS)
add(
    "O02",
    "mutant",
    "/".join(
        str(sum(1 for r in decisions if r[f"R_O_v2_{c}"] == "true" and r["R_S_v2"] == "false"))
        for c in ("Z_output", "Z_all", "XYZ_output", "XYZ_all")
    ),
    MATCHED_DECISIONS,
    "R_O true and R_S false per observation column",
)
add(
    "O03",
    "mutant",
    sum(1 for r in decisions if r["R_O_v2_Z_all"] == "true" and r["R_O_v2_Z_output"] == "false"),
    MATCHED_DECISIONS,
    "R_O true at finer, false at coarser",
)

grid = rows(GRID)
add("D01", "pair x (theta,N)", f"{len(grid):,}", GRID, "row count")
add("D02", "cell", f"{len(stable(grid)):,}", "same", "KILLED+SURVIVED")
disagree = [r for r in stable(rows(SHOT_CELLS)) if r["agree"] == "False"]
add(
    "D03",
    "cell",
    f"{len(disagree)} / {sum(1 for r in disagree if r['guaranteed'] == 'True')}",
    SHOT_CELLS,
    "agree==False; guaranteed==True",
)
unresolved = Counter(r["N"] for r in grid if r["v2_status"].startswith("unresolved"))
add(
    "D04",
    "cell",
    f"{unresolved['500']}/{unresolved['2000']}/{unresolved['8000']} (falls)",
    GRID,
    "unresolved_* by N",
)
budget = matched["budget"]["v2"]
add("D05", "cell", f"{budget['resolved']} / {budget['created']}", MATCHED, "derived record")
ablation = rows(ABLATION)
add(
    "D06",
    "ablation",
    f"{sum(all(r[k] == 'True' for k in ('withdrawn', 'named', 'candidate_unchanged')) for r in ablation)}"
    f" of {len(ablation)}",
    ABLATION,
    "all three flags True",
)

transfer = Counter((r["subject"], r["outcome"], r["qutest_witness_expressible"]) for r in rows(TRANSFER))
add(
    "R01",
    "case",
    f"{transfer[('toffoli_barenco_5', 'WITNESS_EXISTS', 'True')]}/"
    f"{transfer[('simon_4', 'WITNESS_EXISTS', 'False')]}/"
    f"{transfer[('simon_4', 'NO_WITNESS_ABOVE_THETA', 'False')]}",
    TRANSFER,
    "outcome x expressible",
)
qucheck = {r["mutant_id"]: r for r in rows(QUCHECK_RUNS)}
so_other = [r["mutant_id"] for r in primary if r["population"] == "prospective" and r["v2_report"] == "CL4"]
add(
    "R02",
    "case",
    f"{sum(qucheck[m]['verdict_primary'] == 'DETECTED' for m in so_other)} of {len(so_other)}",
    QUCHECK_RUNS,
    "verdict_primary over the 21 prospective SO",
)
transfer_register = rows(TRANSFER_REGISTER)
add(
    "R03",
    "case",
    f"{sum(r['outcome'] == 'WITNESS_EXISTS' for r in transfer_register)} of "
    f"{sum(not r['outcome'].startswith('NOT_EVALUABLE') for r in transfer_register)}",
    TRANSFER_REGISTER,
    "outcome",
)

final = {p: rows(p) for p in POPULATIONS}
candidates = {
    p: [r for r in rs if r.get("v2_candidate") == "CL4" and r.get("OB03") == "satisfied"]
    for p, rs in final.items()
}
confirmed = {p: sum(1 for r in rs if r["v2_report"] == "CL4") for p, rs in candidates.items()}
add(
    "N01",
    "case",
    "/".join(str(len(candidates[p])) for p in POPULATIONS),
    OUTCOMES + "R2V_FINAL_*.csv",
    "v2_candidate==CL4 and OB03 satisfied (stable survival)",
)
add("N02", "case", "/".join(str(confirmed[p]) for p in POPULATIONS), "same", "v2_report==CL4")
total = sum(map(len, candidates.values()))
add("N03", "case", f"{total} / {total - sum(confirmed.values())}", "same", "candidates minus confirmed")
revised = [r for r in rows(RULE_CHANGES) if r["case"] not in witness_order.CHANGED.get(r["arm"], ())]
add(
    "N04",
    "pair",
    f"{len(revised)} / {sum(r['v2_report'] == 'Unresolved' for r in revised)} / "
    f"{sum(r['v2_report'] == 'CL4' for r in revised)}",
    f"{RULE_CHANGES}; {IMPACT}",
    "row counts, less the v3 cases that return to their v1 outcome",
)
native = rows(NATIVE) + rows(NATIVE_DEFECTS)
add("N05", "check", len(native), f"{NATIVE}; {NATIVE_DEFECTS}", "row count")
add("N06", "run", f"{qutest_runs(native):,}", NATIVE, "len(verdicts)+len(guard_verdicts)")
closed_order = list(witness_order.NATIVE.values())
add(
    "N07",
    "check",
    f"{len(closed_order)} / {qutest_runs(closed_order)} / "
    f"{sum(r['purpose'] == 'OB15' and r['status'] == 'satisfied' for r in closed_order)}",
    CLOSED_ORDER_RUNS,
    "row count; len(verdicts)+len(guard_verdicts); OB15 status",
)

external = final[EXTERNAL]
killed_external = counts(external)["NA_KILLED"]
add(
    "E01",
    "mutant",
    f"{len(external)}/{killed_external}/{len(external) - killed_external}",
    EXTERNAL,
    "counts",
)
add("E02", "mutant", spread(external), "same", "v2_report")
add("E03", "mutant", predicted(external), "same", "R_T vs native")
allocation = {r["mutant_id"]: r for r in rows(ALLOCATION)}
add(
    "E04",
    "mutant / site",
    f"{first_gate(allocation.values())} / {sites(allocation.values())}",
    ALLOCATION,
    "anchor_index==0",
)
ol_external = [allocation[r["case"]] for r in external if r["v2_report"] == "CL3"]
add(
    "E05",
    "mutant / program",
    f"{first_gate(ol_external)} / {len({r['subject'] for r in ol_external})}",
    f"{ALLOCATION}; {EXTERNAL}",
    "join",
)

width = final[WIDTH]
width_outcome = counts(width)
width_diagnosed = len(width) - width_outcome["NA_KILLED"]
add(
    "W01",
    "pair",
    f"{len(width)}/{width_diagnosed}/{width_diagnosed - width_outcome['Unresolved']}/"
    f"{width_outcome['Unresolved']}",
    WIDTH,
    "counts",
)

corpus = final[CORPUS]
corpus_outcome = counts(corpus)
add(
    "K01",
    "pair",
    f"{len(corpus):,}/{corpus_outcome['NA_KILLED']}/{len(corpus) - corpus_outcome['NA_KILLED']}",
    CORPUS,
    "counts",
)
add("K02", "pair", spread(corpus, ("CL1", "CL3", "CL4", "CL5", "Unresolved")), "same", "v2_report")
corpus_unresolved = [r for r in corpus if r["v2_report"] == "Unresolved"]
add(
    "K03",
    "pair",
    f"{sum(1 for r in corpus_unresolved if r['native_verdict'] == 'SPLIT')}/"
    f"{sum(1 for r in corpus_unresolved if r['unmet'].startswith('relation R_') and 'inconsistent' not in r['unmet'])}/"
    f"{sum(1 for r in corpus_unresolved if r['v2_candidate'] == 'CL4' and r['native_verdict'] != 'SPLIT')}",
    CORPUS,
    "native_verdict / unmet / candidate",
)
add(
    "K04",
    "pair",
    f"{corpus_outcome['CL3']}/{len(corpus):,} = {100 * corpus_outcome['CL3'] / len(corpus):.1f}%",
    "same",
    "ratio",
)

defect = final[DEFECT]
add(
    "F01",
    "defect",
    f"{len(defect)}/" + spread(defect, ("NA_KILLED", "CL2", "CL4", "Unresolved")),
    DEFECT,
    "rows",
)
add(
    "P13",
    "mutant",
    sum(r["moved"] == "True" and r["declared_report"] == "CL4" for r in rows(GHZ_REGISTER)),
    GHZ_REGISTER,
    "moved CL4 -> NA_KILLED",
)
diagonal = {f"{r['case_set']}/{r['pair_id']}": r["diagonal_stratum"] for r in rows(ELIGIBILITY)}
corpus_survivors = [r for r in corpus if r["native_verdict"] == "SURVIVED"]
ol_share = lambda rs: f"{sum(r['v2_report'] == 'CL3' for r in rs)}/{len(rs)}"
add(
    "K05",
    "pair",
    " ; ".join(
        ol_share([r for r in corpus_survivors if diagonal[r["case"]] == d]) for d in ("False", "True")
    ),
    f"{CORPUS}; {ELIGIBILITY}",
    "diagonal_stratum join",
)
entailment = load(ENTAILMENT)
add(
    "K06",
    "pair",
    f"{entailment['entailed']['cl3']} / {entailment['not_entailed']['cl3']}",
    ENTAILMENT,
    "derived record",
)
shares = load(RELATION_CORPUS)["shares_v2"]
add(
    "K07",
    "pair",
    " / ".join(f"{100 * shares[k][0] / shares[k][1]:.1f}%" for k in ("n<=7", "n>=8")),
    RELATION_CORPUS,
    "derived record",
)
defects = rows(DEFECTS)
depth = counts(defects, "evidence_depth")
add(
    "F02",
    "defect",
    f"{len(defects)} / {sum(r['reproduction'] == 'REPRODUCED' for r in defects)}",
    DEFECTS,
    "rows",
)
DEPTHS = (
    "NOT_REPRODUCIBLE",
    "NATIVE_REPRODUCTION_ONLY",
    "PROFILE_ONLY",
    "RELATION_LEVEL",
    "FULL_CERTIFICATION",
)
add(
    "F03",
    "defect",
    "/".join(str(depth[k]) for k in DEPTHS),
    "same",
    "evidence_depth",
)
add("C04", "mutant", load(CONTRACT_MOVERS)["movers"], CONTRACT_MOVERS, "derived record")

other_mutants = rows(OTHER_MUTANTS)
add(
    "Z01",
    "mutant / site",
    f"{first_gate(other_mutants)}/{len(other_mutants)}/{sites(other_mutants)}",
    OTHER_MUTANTS,
    "anchor_index",
)
position = lambda r: int(re.search(r"@(\d+)", r["location"]).group(1))
add(
    "Z02",
    "site",
    len({(r["program"], position(r)) for r in rows(DEVELOPMENT_MUTANTS)}),
    DEVELOPMENT_MUTANTS,
    "location index",
)
mqt_mutants = rows(MQT_MUTANTS)
add("Z03", "mutant / site", f"{first_gate(mqt_mutants)}/{sites(mqt_mutants)}", MQT_MUTANTS, "anchor_index")

mqt = rows(MQT_CASES)
mqt_outcome = counts(mqt)
add("M01", "mutant", f"{len(mqt)}/{mqt_outcome['NA_KILLED']}/{len(mqt) - mqt_outcome['NA_KILLED']}", MQT_CASES, "counts")
add("M02", "mutant", spread(mqt), "same", "v2_report")
mqt_candidates = [r for r in mqt if r["v2_candidate"] == "CL4"]
mqt_reported = [r for r in mqt_candidates if r["v2_report"] == "CL4"]
mqt_withheld = next(r for r in mqt_candidates if r["v2_report"] != "CL4")
add(
    "M03",
    "mutant",
    f"{len(mqt_candidates)}/{len(mqt_reported)}/{len(mqt_candidates) - len(mqt_reported)}",
    "same",
    "candidate CL4",
)
add(
    "M04",
    "mutant",
    sum(r["d1_mutant_kills_of_12"] == "12" for r in mqt_reported),
    f"{MQT_REPAIR}; {MQT_CASES}",
    "d1 kills",
)
add(
    "M05",
    "repaired suite",
    len({(r["subject"], r["witness_key"]) for r in mqt_reported}),
    "same",
    "(subject, witness)",
)
add(
    "M06",
    "run",
    sum(int(r["d1_original_false_failures_of_12"]) for r in mqt_candidates),
    "same",
    "sum over candidates",
)
add(
    "M07",
    "run",
    "/".join(mqt_withheld[k] for k in ("ob13_kills_of_12", "ob15_kills_of_12", "d1_mutant_kills_of_12")),
    "same",
    "withheld row",
)
add(
    "M08",
    "mutant",
    f"{sum(r['d2_outcome'] == 'consistent' for r in mqt)}/{mqt_outcome['CL3']}",
    f"{MQT_OBSERVATION}; {MQT_CASES}",
    "d2_outcome",
)
add(
    "M09",
    "mutant",
    f"{sum(r['bound_b13'] == 'True' for r in mqt_candidates)}/"
    f"{sum(r['bound_guard'] == 'True' for r in mqt_candidates)}",
    "same",
    "b13 / bgw",
)

guards = rows(SUITE_GUARDS)
fails = lambda column, more_than: sum(int(r[column]) > more_than for r in guards)
add(
    "G01",
    "subject x suite cell",
    f"{fails('sampled_ref_false_fails', 0)}/{fails('sampled_ref_false_fails', 1)} ; "
    f"{fails('exact_ref_false_fails', 0)}/{fails('exact_ref_false_fails', 1)}",
    SUITE_GUARDS,
    "false-fail counts",
)

with open(out_dir() / "ledger_checks.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ledger[0]))
    w.writeheader()
    w.writerows(ledger)
for r in ledger:
    print(f"{r['id']:4s} {r['recomputed_value']!s:28s} {r['quantity']}")
