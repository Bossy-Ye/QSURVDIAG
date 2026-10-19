#!/bin/sh
# Regenerate the inventory outside the package.  Usage: sh run_all.sh <package_root> <out_dir>
# Reads the package read-only, fetches the pinned QMutBench files to <out_dir>/qmutbench_dl and writes every output
# to <out_dir>; the archived outputs are data/inventory/out/ and data/inventory/POSITION_CROSSTAB.txt.
set -eu
ROOT="$1"; OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"
python3 -I -B "$HERE/corpus_files.py" "$ROOT" "$OUT/corpus_files.tsv"
sh "$HERE/fetch_corpus.sh" "$OUT/corpus_files.tsv" "$OUT/qmutbench_dl"
python3 -I -B "$HERE/inventory.py" "$ROOT" "$OUT/qmutbench_dl" "$OUT/corpus_files.tsv" "$OUT" > /dev/null
python3 -I -B "$HERE/rzz_count.py" "$OUT/corpus_files.tsv" "$OUT/qmutbench_dl" > "$OUT/rzz_count.txt"
python3 -I -B "$HERE/concentration.py" "$OUT/cases_all.csv" "$OUT/concentration.json" > /dev/null
python3 -I -B "$HERE/position_crosstab.py" "$OUT/cases_all.csv" > "$OUT/POSITION_CROSSTAB.txt"
echo "outputs in $OUT"
