"""Record-level checks of the decision-diagram equivalence check, the developer-test inspection, the 42 released
defects, the worked-example run, the QuCheck count and two environment freezes. No circuit is executed."""
import csv, hashlib, json, re, sys
sys.dont_write_bytecode = True
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import orig, out_dir, ROOT
import witness_order as wo

OUT = []
def chk(cid, label, value, level): OUT.append({"check_id": cid, "label": label, "recomputed": value, "evidence_level": level})
rd = lambda p: wo.final(p, list(csv.DictReader(open(orig(p), newline=""))))
fsha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

# N01-N03 decision-diagram equivalence check: one pinned run over the 295 issued primary outcomes
L = rd("data/certification/equivalence/T2B_QCEC_LEDGER_599.csv")
REG = json.load(open(orig("data/certification/equivalence/T2B_QCEC_REGISTRY_599.json")))
V = Counter(r["qcec_verdict"] for r in L)
decided = len(L) - V["no_information"]
allin = V["equivalent"] + V["equivalent_up_to_global_phase"]
chk("N01", "decision-diagram check: cases / decided / no information / all-input equivalences",
    f"{len(L)}/{decided}/{V['no_information']}/{allin}", "per-case records")
T14 = rd("data/primary/records/T1_4_INTERFACE_599.csv")
issued = {r["mutant_id"] for r in T14 if r["report"] not in ("NA_KILLED", "Unresolved")}
ids = [r["mutant_id"] for r in L]
hexok = all(re.fullmatch(r"[0-9a-f]{16}", r[k] or "") for r in L for k in ("origin_qasm_sha256", "mutant_qasm_sha256"))
chk("N02", "decision-diagram ledger: unique ids / equal to the issued primary outcomes / 16-hex input-hash prefix present for every case",
    f"{len(set(ids))}/{set(ids) == issued}/{hexok}", "per-case records")
chk("N03", "decision-diagram check: pinned versions mqt-qcec / mqt-core, single run",
    f"{REG['versions'].get('mqt-qcec')}/{REG['versions'].get('mqt-core')}/{REG.get('pinned')}", "frozen run record")

# N04-N05 developer-practice check: occurrence-level classification with pinned sources
O = rd("data/external/developer_tests/occurrence_classification.csv")
C = Counter(r["occurrence_class"] for r in O)
chk("N04", "developer tests: occurrences / structure, resources or set-up / full state or unitary / computational basis",
    f"{len(O)}/{C['structure, resources or setup']}/{C['full state vector'] + C['full unitary']}/{C['computational-basis quantity']}",
    "per-occurrence records")
pins = {(r["repository"], r["commit"]) for r in O}
located = all(r["file"] and r["line"].isdigit() for r in O)
chk("N05", "developer tests: repositories / pinned commits / every occurrence located by file and line",
    f"{len({p[0] for p in pins})}/{len(pins)}/{located}", "per-occurrence records")

# N06 released defects: the depth record's 42 numbers map one to one onto identified Bugs4Q defects
D = rd("data/external/defects/B3_REAL_DEFECTS_FRESH.csv")
MAN = rd("data/external/defects/E5_DEFECT_MANIFEST.csv")
mids = {r["defect_id"].replace("qiskit_", "") for r in MAN}
ident = all(r["repository"] and r["issue_or_thread"] and r["buggy_sha256"] for r in MAN)
chk("N06", "released defects: manifest rows / depth-record ids matched / every row identified by repository, issue and hash",
    f"{len(MAN)}/{sum(r['defect_id'] in mids for r in D)}/{ident}", "per-defect records")

# N07-N08 Listing 1: the recorded run and its test file
W = rd("data/certification/outcomes/R2V_WRAPPED_DEMO.csv")
g = {(r["test"].split(" ")[0], r["program"]): r for r in W}
chk("N07", "Listing 1 run: basis-change test kills original / mutant / repetitions; baseline suite kills original / mutant",
    f"{g[('wrapped','original')]['kills']}/{g[('wrapped','mutant')]['kills']}/{g[('wrapped','mutant')]['reps']}/"
    f"{g[('S_MIN','original')]['kills']}/{g[('S_MIN','mutant')]['kills']}", "per-run record")
qasm = open(orig("data/certification/outcomes/R2V_WRAPPED_DEMO_test.qasm")).read()
lib = open(orig("data/prospective/mqt_bench/frozen_deps/r2v_lib.py")).read()
seeds = "42-53" if re.search(r"MUT_SEEDS\s*=\s*\[42 \+ r for r in range\(R\)\]", lib) and re.search(r"N_SHOTS,\s*R,\s*GUARD_REPS\s*=\s*2000,\s*12,", lib) else "differs"
shown = "//% seed 42" in qasm and "h q[2];" in qasm and "rz(1.570796326795) q[2];" in qasm
chk("N08", "Listing 1: repetition seeds (r2v_lib) / file shows seed 42, the Hadamard on q2 and the mutation",
    f"{seeds}/{shown}", "archived code and test file")

# N09 QuCheck: observation limitations under QUTest that stay observation-limited under the declared QuCheck profile
ol = [r for r in T14 if r["report"] == "CL3"]
chk("N09", "QUTest observation limitations / still observation-limited under the declared QuCheck profile",
    f"{len(ol)}/{sum(r['R_O_QuCheck'] == 'True' for r in ol)}", "per-case records")

# N10 environment freezes recorded by hash in E5_ENVIRONMENT_LOCK.json
LOCK = json.load(open(orig("data/profiles/E5_ENVIRONMENT_LOCK.json")))["reproduction_environments"]
ok = sum(fsha(ROOT / f"environment/records/{k}_pip_freeze.txt") == LOCK[k]["pip_freeze_sha256"] for k in ("Q045", "Q11", "Q25"))
chk("N10", "released-defect environments: pip freezes equal to their locked hashes (Q045, Q11, Q25)", f"{ok}/3", "file hashes")

with open(out_dir() / "records_checks.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["check_id", "label", "recomputed", "evidence_level"]); w.writeheader(); w.writerows(OUT)
for r in OUT: print(f"{r['check_id']}  {r['recomputed']:<22} {r['label']}")
