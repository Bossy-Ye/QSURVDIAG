"""Verify the package against provenance/checksums.sha256 and the archived content against source_manifest.csv.

Usage:  python3 scripts/verify_integrity.py
Optional (needs OpenSSL): also verifies the RFC 3161 receipts of the MQT Bench freeze with --tsr.

Archived files that this release redacts are listed in provenance/REDACTIONS.csv, and the archived file whose
third-party quotations it replaces is listed in provenance/DERIVED_FILES.csv. They are reported separately: their
release hash is checked against that record, and they are never counted as matching their original source hash or
the timestamped freeze manifest.
"""
import csv, hashlib, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
RED = {}
if (ROOT / "provenance/REDACTIONS.csv").is_file():
    RED = {r["package_path"]: r for r in csv.DictReader(open(ROOT / "provenance/REDACTIONS.csv"))}
DER = {}
if (ROOT / "provenance/DERIVED_FILES.csv").is_file():
    DER = {r["package_path"]: r for r in csv.DictReader(open(ROOT / "provenance/DERIVED_FILES.csv"))}
bad = []
listed = set()
for line in (ROOT / "provenance/checksums.sha256").read_text().splitlines():
    if not line.strip() or line.startswith("#"): continue
    h, rel = line.split("  ", 1); listed.add(rel); p = ROOT / rel
    if not p.is_file(): bad.append(f"missing: {rel}")
    elif sha(p) != h: bad.append(f"changed: {rel}")
present = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and p.relative_to(ROOT).parts[0] not in ("output", ".git") and "__pycache__" not in p.parts}
extra = sorted(present - listed - {"provenance/checksums.sha256"})
archived, redacted, derived = set(), [], []
for r in csv.DictReader(open(ROOT / "provenance/source_manifest.csv")):
    p = ROOT / r["package_path"]; archived.add(r["package_path"]); x = RED.get(r["package_path"])
    if x is not None:
        if x["original_sha256"] != r["sha256"]: bad.append(f"redaction record disagrees with the source hash: {r['package_path']}")
        elif not p.is_file() or sha(p) != x["release_sha256"]: bad.append(f"redacted file differs from its redaction record: {r['package_path']}")
        elif r["package_path"] not in redacted: redacted.append(r["package_path"])
        continue
    x = DER.get(r["package_path"])
    if x is not None:
        if x["original_sha256"] != r["sha256"]: bad.append(f"derived-file record disagrees with the source hash: {r['package_path']}")
        elif not p.is_file() or sha(p) != x["release_sha256"]: bad.append(f"derived file differs from its record: {r['package_path']}")
        elif r["package_path"] not in derived: derived.append(r["package_path"])
        continue
    if not p.is_file() or sha(p) != r["sha256"]: bad.append(f"archived file differs from its source hash: {r['package_path']}")
bad += [f"redaction record without a source-manifest row: {k}" for k in RED if k not in archived]
bad += [f"derived-file record without a source-manifest row: {k}" for k in DER if k not in archived]
print(f"checksums: {len(listed)} files listed (every file except provenance/checksums.sha256 itself), {len(bad)} problems, {len(extra)} unlisted files")
print(f"archived files: {len(archived) - len(redacted) - len(derived)} identical to their source hash, {len(redacted)} redacted"
      + (" (original SHA-256 and the hash of each removed text in provenance/REDACTIONS.csv)" if redacted else ""))
if DER: print(f"derived files: {len(derived)} with third-party quotations replaced (original SHA-256 and the hash of each omitted text in provenance/DERIVED_FILES.csv)")
for b in bad[:20]: print("  ", b)
for x in extra[:20]: print("   unlisted:", x)
if "--tsr" in sys.argv:
    fz = ROOT / "data/prospective/mqt_bench/freeze"
    for k in ("A", "B"):
        r = subprocess.run(["openssl", "ts", "-verify", "-in", f"FREEZE_{k}.tsr", "-queryfile", f"FREEZE_{k}.tsq",
                            "-CAfile", "tsa/freetsa_cacert.pem", "-untrusted", "tsa/freetsa_tsa.crt"], cwd=fz, capture_output=True, text=True)
        verdict = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Verification")]
        print(f"RFC 3161 Freeze {k}: {verdict[0] if verdict else (r.stdout + r.stderr).strip()[-200:]}")
    for k in ("A", "B"):
        lines = [l.split("  ", 1) for l in (fz / f"FREEZE_{k}.sha256").read_text().splitlines() if l.strip() and not l.startswith("#")]
        match, red, miss = 0, [], []
        for h, rel in lines:
            p = fz.parent / rel; pkg = "data/prospective/mqt_bench/" + (rel[2:] if rel.startswith("./") else rel)
            if p.is_file() and sha(p) == h: match += 1
            elif pkg in RED and RED[pkg]["original_sha256"] == h and p.is_file() and sha(p) == RED[pkg]["release_sha256"]: red.append(pkg)
            else: miss.append(rel)
        print(f"MQT Bench Freeze {k} manifest: {len(lines)} entries, {match} matching, {len(red)} redacted"
              + (" (original SHA-256 in provenance/REDACTIONS.csv equals the timestamped hash)" if red else "") + f", {len(miss)} other")
sys.exit(1 if bad or extra else 0)
