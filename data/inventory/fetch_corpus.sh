#!/bin/sh
# Download the pinned QMutBench files listed by corpus_files.py into a dedicated directory.
# Usage: sh fetch_corpus.sh <corpus_files.tsv> <download_dir>
# Files are stored as <download_dir>/<sha256-from-manifest>.qasm; verification is done by
# inventory.py (it recomputes SHA-256 and refuses mismatches).
set -eu
TSV="$1"; DL="$2"
mkdir -p "$DL"
tail -n +2 "$TSV" | awk -F'\t' '{print $6"\t"$8; print $7"\t"$9}' | sort -u > "$DL/.urls"
while IFS="$(printf '\t')" read -r url sha; do
  [ -s "$DL/$sha.qasm" ] || printf '%s\n%s\n' "$url" "$DL/$sha.qasm"
done < "$DL/.urls" | xargs -r -n 2 -P 16 sh -c 'curl -sS --retry 3 -m 60 -o "$1" "$0"'
echo "files: $(ls "$DL" | wc -l)"
