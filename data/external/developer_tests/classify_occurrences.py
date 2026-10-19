"""E1a: occurrence-level classification of the assertions in the developer tests profiled for E1.

Read-only. Reproduces the 51 assertion occurrences of the frozen assertion-family packet from the
cached pinned sources (same file list and family rule as work/assert_families.py), attaches the two
reviewers' family labels, and classifies every occurrence by what it reads. Writes
occurrence_classification.csv next to this file and verifies every count the manuscript prints.
No mutant is generated, no test is executed, and no frozen E1 file is written.
"""
import csv, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "work", "cache")
JOBS = {
    "qiboteam/qibo": ("7c422b3a3d", ["tests/test_models_qft.py", "tests/test_models_hep.py",
                                      "tests/test_models_iqae.py", "tests/test_models_qcnn.py"]),
    "unitaryfoundation/mitiq": ("1a892a9783", ["mitiq/benchmarks/tests/test_qpe_circuits.py",
                                                "mitiq/benchmarks/tests/test_w_state_circuits.py"]),
    "quantumlib/Qualtran": ("d5faa99db8", ["qualtran/bloqs/qft/qft_text_book_test.py",
                                            "qualtran/bloqs/qft/approximate_qft_test.py",
                                            "qualtran/bloqs/qft/qft_phase_gradient_test.py"]),
}

def family(a):  # identical to the frozen work/assert_families.py rule
    s = re.sub(r"\s+", " ", a.strip())
    s = re.sub(r"[\"'][^\"']*[\"']", "STR", s)
    s = re.sub(r"\b\d+(\.\d+)?(e-?\d+)?\b", "N", s)
    calls = re.findall(r"([A-Za-z_][\w.]*)\s*\(", s)
    return " | ".join(sorted(set(calls))[:5]) or "(bare comparison)"

# Occurrence classes. Every behavioural occurrence is pinned to (file basename, line) with the
# quantity it reads, established by reading the surrounding test and, where needed, the unit.
STATE, UNITARY, BASIS, STRUCT = "full state vector", "full unitary", "computational-basis quantity", "structure, resources or setup"
BEHAVIOURAL = {
    ("test_models_qcnn.py", 37): (STATE, "real part of the final state vector"),
    ("test_models_qcnn.py", 38): (STATE, "imaginary part of the final state vector"),
    ("test_models_qcnn.py", 95): (STATE, "real part of the final state vector"),
    ("test_models_qcnn.py", 96): (STATE, "imaginary part of the final state vector"),
    ("test_models_hep.py", 114): (BASIS, "qPDF.predict: (1-<Z_q>)/(1+<Z_q>), <Z_q> from the exact state (hep.py _model)"),
    ("test_models_iqae.py", 69): (BASIS, "IQAE amplitude estimate from sampled measurement shots"),
    ("test_models_iqae.py", 70): (BASIS, "IQAE amplitude estimate from sampled measurement shots"),
    ("test_w_state_circuits.py", 56): (STATE, "final state vector"),
    ("test_w_state_circuits.py", 82): (STATE, "final state vector"),
    ("test_w_state_circuits.py", 111): (STATE, "final state vector"),
    ("test_qpe_circuits.py", 190): (BASIS, "one measured bitstring from cirq.Simulator.run"),
    ("test_qpe_circuits.py", 207): (BASIS, "one measured bitstring from cirq.Simulator.run"),
    ("approximate_qft_test.py", 71): (UNITARY, "cirq.unitary of the bloq"),
    ("approximate_qft_test.py", 72): (UNITARY, "cirq.unitary of the adjoint bloq"),
    ("approximate_qft_test.py", 83): (UNITARY, "cirq.unitary of the bloq"),
    ("qft_phase_gradient_test.py", 56): (UNITARY, "cirq.unitary of the bloq"),
    ("qft_phase_gradient_test.py", 57): (UNITARY, "cirq.unitary of the inverse bloq"),
    ("qft_text_book_test.py", 31): (UNITARY, "tensor_contract of the bloq"),
    ("qft_text_book_test.py", 32): (UNITARY, "tensor_contract of the adjoint bloq"),
    ("qft_text_book_test.py", 44): (UNITARY, "tensor_contract of the bloq"),
    ("qft_text_book_test.py", 45): (UNITARY, "tensor_contract of the adjoint bloq"),
}

def main():
    frozen = list(csv.DictReader(open(os.path.join(ROOT, "human_review_admissibility", "decision_form.csv"))))
    fid = {r["family_signature"]: (r["family_id"], int(r["occurrences"])) for r in frozen}
    lab = {}
    for who in ("reviewer_A", "reviewer_B"):
        for r in csv.DictReader(open(os.path.join(ROOT, "human_review_submissions", who, "assertion_families.csv"))):
            lab.setdefault(r["family_id"], []).append(r["admissibility"])
    rows = []
    for repo, (sha, files) in JOBS.items():
        o, n = repo.split("/")
        for f in files:
            src = open(os.path.join(CACHE, f"{o}__{n}__{sha[:8]}__{f.replace('/', '__')}"), encoding="utf-8").read()
            for m in re.finditer(r"^[^\n]*(?:\bassert\b|self\.assert\w+|np\.testing\.assert\w+)[^\n]*", src, re.M):
                a = m.group(0)
                if a.strip().startswith("#"):
                    continue
                line = src[:m.start()].count("\n") + 1
                key = family(a)
                cls, reads = BEHAVIOURAL.get((os.path.basename(f), line), (STRUCT, ""))
                rows.append(dict(repository=repo, commit=sha, file=f, line=line, family_id=fid[key][0],
                                 family_label=" / ".join(sorted(set(lab[fid[key][0]]))),
                                 occurrence_class=cls, reads=reads, code=a.strip()))
    checks = []
    def check(name, ok):
        checks.append((name, bool(ok)))
    cnt = Counter(r["family_id"] for r in rows)
    check("51 occurrences", len(rows) == 51)
    check("12 families, counts equal to the frozen form", len(cnt) == 12 and all(cnt[i] == c for i, c in fid.values()))
    check("every pinned behavioural line found", len({(os.path.basename(r["file"]), r["line"]) for r in rows} & set(BEHAVIOURAL)) == len(BEHAVIOURAL))
    check("both reviewers agree on all 12 family labels", all(len(set(v)) == 1 and len(v) == 2 for v in lab.values()) and len(lab) == 12)
    fam_lab = Counter(v[0] for v in lab.values())
    check("family labels 6 behavioural, 5 structural, 1 unclear",
          fam_lab == Counter({"behaviourally_admissible": 6, "structural_implementation_only": 5, "unclear": 1}))
    tot = Counter(r["occurrence_class"] for r in rows)
    check("occurrences: 30 structure/resources/setup, 16 state or unitary, 5 basis",
          tot[STRUCT] == 30 and tot[STATE] + tot[UNITARY] == 16 and tot[BASIS] == 5)
    per = {repo: Counter(r["occurrence_class"] for r in rows if r["repository"] == repo) for repo in JOBS}
    check("qibo 16 = 9 structural, 4 state, 3 basis", per["qiboteam/qibo"] == Counter({STRUCT: 9, STATE: 4, BASIS: 3}))
    check("mitiq 13 = 8 structural, 3 state, 2 basis", per["unitaryfoundation/mitiq"] == Counter({STRUCT: 8, STATE: 3, BASIS: 2}))
    check("Qualtran 22 = 13 structural, 9 unitary", per["quantumlib/Qualtran"] == Counter({STRUCT: 13, UNITARY: 9}))
    census = list(csv.DictReader(open(os.path.join(ROOT, "repository_candidates.csv"))))
    check("25 repositories verified against the API", len(census) == 25)
    status = Counter(r["eligibility_status"] for r in census)
    check("8 read at source level (25 minus 17 reserve)", len(census) - status["reserve_metadata_verified"] == 8)
    check("3 pilot candidates", status["pilot_candidate"] == 3)
    log = open(os.path.join(ROOT, "search_log.md"), encoding="utf-8").read()
    check("search log: 46 distinct repositories", "| distinct repositories after de-duplication | 46 |" in log)
    check("search log: 21 screened out at listing level", "| screened out at listing level (X2/X5, toy repositories) | 21 |" in log)
    check("search log: no third-party QUTest use", "No repository outside the tool's own was found using QUTEST" in log)
    check("search log: one third-party QuCheck use", "only one third-party repository" in log)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "occurrence_classification.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["repository"], r["file"], r["line"])))
    for name, ok in checks:
        print("PASS" if ok else "FAIL", name)
    print(f"{sum(ok for _, ok in checks)}/{len(checks)} checks pass; wrote {os.path.relpath(out, ROOT)}")
    return 0 if all(ok for _, ok in checks) else 1

if __name__ == "__main__":
    sys.exit(main())
