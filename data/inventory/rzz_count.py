"""Count the R_zz gate statements in the QMutBench originals and mutants behind the corpus pairs.

Usage: python3 -I rzz_count.py <corpus_files.tsv> <download_dir>

Reads the table written by corpus_files.py and the files fetched by fetch_corpus.sh, refuses any
file whose SHA-256 differs from the case manifests, and prints the number of rzz statements over
the originals and the mutants of all pairs (each pair counted once, so an original shared by
several pairs is counted once per pair), the number in distinct files, and the number of pairs
whose original or mutant contains one.  No file is written.
"""
import csv
import hashlib
import os
import re
import sys

RZZ = re.compile(r"^\s*rzz\s*\(", re.M)


def count(dl, sha, cache):
    if sha not in cache:
        b = open(os.path.join(dl, sha + ".qasm"), "rb").read()
        if hashlib.sha256(b).hexdigest() != sha:
            sys.exit("SHA-256 mismatch: " + sha)
        cache[sha] = len(RZZ.findall(b.decode()))
    return cache[sha]


def main(tsv, dl):
    rows = list(csv.DictReader(open(tsv, newline=""), delimiter="\t"))
    cache = {}
    orig = sum(count(dl, r["orig_sha256"], cache) for r in rows)
    mut = sum(count(dl, r["mut_sha256"], cache) for r in rows)
    pairs = sum(1 for r in rows if count(dl, r["orig_sha256"], cache) or count(dl, r["mut_sha256"], cache))
    print("pairs", len(rows))
    print("rzz in originals", orig)
    print("rzz in mutants", mut)
    print("rzz in originals and mutants", orig + mut)
    print("rzz in distinct files", sum(cache.values()), "over", len(cache), "files")
    print("pairs with an rzz gate", pairs)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
