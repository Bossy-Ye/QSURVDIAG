"""List the QMutBench original and mutant files behind every corpus pair (R2V_FINAL_CORPUS.csv).

Usage: python3 -I corpus_files.py <package_root> <out_tsv>

Writes one row per corpus case: case_key, case_set, case_id, original_id, mutant_file,
orig_url, mut_url, orig_sha256, mut_sha256, family, manifest.  Hashes are the raw SHA-256 values
recorded in data/scalability/corpus/case_manifests/.  No file of the package is modified.
"""
import csv
import os
import sys

COMMIT = "01f5e7700c051fe715fc368b307deaa7e6869ba8"
RAW = "https://raw.githubusercontent.com/EnautMendi/QMutBench/" + COMMIT + "/data/"

MANIFEST_OF_SET = {
    "qra_cases": "QUCHECK_REPLICATION_600_MANIFEST.csv",
    "qra_cases_v1_1": "QUCHECK_REPLICATION_600_MANIFEST_V1_1.csv",
    "holdout_cases": "REAL_STUDY_500_CASE_MANIFEST.csv",
    "sbs_cases": "SCALABILITY_STRESS_MANIFEST.csv",
    "preflight_cases": "REAL_TRANSFER_40_CASE_MANIFEST.csv",
}


def main(root, out):
    man_dir = os.path.join(root, "data/scalability/corpus/case_manifests")
    manifests = {}
    for cs, fn in MANIFEST_OF_SET.items():
        rows = list(csv.DictReader(open(os.path.join(man_dir, fn), newline="")))
        key = "case_id" if "case_id" in rows[0] else "study_case_id"
        manifests[cs] = {r[key]: r for r in rows}
    corpus = list(csv.DictReader(open(os.path.join(root, "data/certification/outcomes/R2V_FINAL_CORPUS.csv"), newline="")))
    rows = []
    for c in corpus:
        cs, cid = c["case"].split("/")
        m = manifests[cs][cid]
        orig = m["source_original_id"]
        mut = m["source_mutant_id"]
        if cs == "holdout_cases":
            mut_path = m["raw_path"]
            assert mut_path.endswith("/" + mut), (cid, mut_path, mut)
        else:
            mut_path = "Mutated_programs/Mutants_%s/%s" % (orig, mut)
        fam = m.get("algorithm_family") or m.get("qmutbench_algorithm") or ""
        if cs == "preflight_cases":
            fam = m["qmutbench_algorithm"]
            mut_sha, orig_sha = m["raw_mutant_sha256"], m["raw_origin_sha256"]
        else:
            mut_sha, orig_sha = m["raw_sha256"], m["raw_origin_sha256"]
        rows.append({
            "case_key": c["case_key"], "case_set": cs, "case_id": cid, "original_id": orig,
            "mutant_file": mut, "orig_url": RAW + "Origin_programs/%s.qasm" % orig,
            "mut_url": RAW + mut_path, "orig_sha256": orig_sha, "mut_sha256": mut_sha,
            "family": fam, "manifest": MANIFEST_OF_SET[cs],
        })
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print("cases", len(rows), "distinct originals", len({r["original_id"] for r in rows}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
