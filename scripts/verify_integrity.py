"""Check the package against its provenance tables: checksums.sha256, source_manifest.csv, redactions.csv,
derived_files.csv, license_map.csv and renames.csv, and the paths named in README.md and docs/protocols.md.

A redacted or derived file is checked against the release hash of its record and is not counted as identical
to its source."""

import argparse, csv, fnmatch, functools, hashlib, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "provenance"
CHECKSUMS = "provenance/checksums.sha256"
MQT_FREEZE = ROOT / "data/prospective/mqt_bench/freeze"
TSA = ("-CAfile", MQT_FREEZE / "tsa/freetsa_cacert.pem", "-untrusted", MQT_FREEZE / "tsa/freetsa_tsa.crt")
# Freezes C and D time-stamp the plans under their names in the study. The package holds them at these paths.
PLANS = {
    "X1_OBSERVATION_CHANGE.md": "data/observation_change/PLAN.md",
    "X2_DEVELOPER_SUITES.md": "data/developer_suites/PLAN.md",
    "X4_POSITION.md": "data/position/PLAN.md",
    "X1_POSITION_EXTENSION.md": "data/observation_change/POSITION_EXTENSION.md",
}
# Not part of the package: the output folder, version control, files that .gitattributes keeps out of the
# release archive, and files that an interpreter or a file manager leaves behind.
OUTSIDE = ("output", ".git", ".github", ".gitignore", ".gitattributes")
LITTER = ("__pycache__", ".DS_Store")
# Names that README.md and docs/protocols.md mention and the package does not hold: study files that
# docs/protocols.md lists as not released, files that archived runners write, plan names without a file of
# their own, a working folder and a corpus case key.
NOT_IN_PACKAGE = (
    "E13_CERTIFICATES.json",
    "E13_CERTIFICATES_PREAMENDMENT.json",
    "E13_SUBJECTS.json",
    "claim_decision.py",
    "ASSERTION_INSTANCE_CLOSURE_AUDIT.md",
    "CROSS_TOOL_MAPPING.yaml",
    "PHASE5A_1_AMENDMENT.md",
    "PILOT_CANDIDATE_REPORT.md",
    "select_units.py",
    "select_units_v11.py",
    "PASS3A2_SCIENTIFIC_DECISION.md",
    "programs.json",
    "mutant_gates.json",
    "X2_INPUTS.jsonl",
    "X2_RUNTIME_CHECK.json",
    "revision2/",
    "qra_cases_v1_1/QRA_360",
)

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--tsr", action="store_true", help="also verify the RFC 3161 receipts (needs OpenSSL)")
args = ap.parse_args()


@functools.lru_cache(maxsize=None)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differs(rel, digest):
    return not (ROOT / rel).is_file() or sha(ROOT / rel) != digest


def table(name):
    with open(PROVENANCE / name) as f:
        return list(csv.DictReader(f))


def hash_list(path):
    lines = path.read_text().splitlines()
    return [line.split("  ", 1) for line in lines if line.strip() and not line.startswith("#")]


def exceptions(name):
    return {r["package_path"]: r for r in table(name)} if (PROVENANCE / name).is_file() else {}


bad = []
checksums = hash_list(ROOT / CHECKSUMS)
listed = {rel for _, rel in checksums}
for digest, rel in checksums:
    if not (ROOT / rel).is_file():
        bad.append(f"missing: {rel}")
    elif sha(ROOT / rel) != digest:
        bad.append(f"changed: {rel}")
present = {
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob("*")
    if p.is_file() and p.relative_to(ROOT).parts[0] not in OUTSIDE and not set(p.parts) & set(LITTER)
}
unlisted = sorted(present - listed - {CHECKSUMS})

redactions, derivations = exceptions("redactions.csv"), exceptions("derived_files.csv")
archived, redacted, derived = set(), set(), set()
for r in table("source_manifest.csv"):
    rel = r["package_path"]
    archived.add(rel)
    for records, found, record, file in (
        (redactions, redacted, "redaction record", "redacted file differs from its redaction record"),
        (derivations, derived, "derived-file record", "derived file differs from its record"),
    ):
        if rel in records:
            if records[rel]["original_sha256"] != r["sha256"]:
                bad.append(f"{record} disagrees with the source hash: {rel}")
            elif differs(rel, records[rel]["release_sha256"]):
                bad.append(f"{file}: {rel}")
            else:
                found.add(rel)
            break
    else:
        if differs(rel, r["sha256"]):
            bad.append(f"archived file differs from its source hash: {rel}")

licenses = table("license_map.csv")
licensed = {r["package_path"] for r in licenses}
bad += [f"license-map row without a role: {r['package_path']}" for r in licenses if not (r.get("role") or "").strip()]
bad += [f"no license-map row: {k}" for k in sorted(present - licensed - {CHECKSUMS})]
bad += [f"license-map row without a file: {k}" for k in sorted(licensed - present)]
bad += [f"redaction record without a source-manifest row: {k}" for k in redactions if k not in archived]
bad += [f"derived-file record without a source-manifest row: {k}" for k in derivations if k not in archived]

# renames.csv: the change is "none" exactly when the earlier and the present hash are equal.
renames = table("renames.csv")
renamed = {"unchanged": 0, "edited": 0}
for r in renames:
    rel = r["package_path"]
    change = r["change"].split("added after version 1.3.0; ", 1)[-1]
    if not (ROOT / rel).is_file():
        bad.append(f"renamed file missing: {rel}")
    elif sha(ROOT / rel) != r["sha256"]:
        bad.append(f"renamed file differs from its renames.csv hash: {rel}")
    elif not change or (change == "none") != (r["earlier_sha256"] == r["sha256"]):
        bad.append(f"renames.csv change does not agree with the two hashes: {rel}")
    else:
        renamed["unchanged" if change == "none" else "edited"] += 1

# A name in single backticks is a path when it holds a "/" or ends in a file extension. It must equal a
# package file or folder, end one, or match one as a pattern, unless it is an earlier path of renames.csv, a
# time-stamped plan name or listed in NOT_IN_PACKAGE.
freezes = {k: hash_list(PROVENANCE / f"FREEZE_{k}.sha256") for k in "CD"}
stamped = {name for manifest in freezes.values() for _, name in manifest}
folders = {q.as_posix() + "/" for k in present for q in Path(k).parents if q.as_posix() != "."}
known = [present, folders, [r["earlier_path"] for r in renames]]
named = 0
for doc in ("README.md", "docs/protocols.md"):
    prose = re.sub(r"```.*?```", "", (ROOT / doc).read_text(), flags=re.S)
    for name in re.findall(r"`([^`\n]+)`", prose):
        if " " in name or not ("/" in name or re.search(r"[\w*-]\.[A-Za-z0-9*]{1,8}$", name)):
            continue
        named += 1
        if name in stamped or name in NOT_IN_PACKAGE:
            continue
        matches = lambda k: fnmatch.fnmatchcase(k, name) or fnmatch.fnmatchcase(k, "*/" + name)
        if not any(matches(k) for ks in known for k in ks):
            bad.append(f"{doc} names a path that is not in the package: {name}")
if (ROOT / "expected/verify_summary.txt").read_text() not in (ROOT / "README.md").read_text():
    bad.append("README.md does not show expected/verify_summary.txt verbatim")

print(
    f"checksums: {len(listed)} files listed (every file except provenance/checksums.sha256 itself), "
    f"{len(bad)} problems, {len(unlisted)} unlisted files"
)
note = " (original SHA-256 and the hash of each removed text in provenance/redactions.csv)"
print(
    f"archived files: {len(archived) - len(redacted) - len(derived)} identical to their source hash, "
    f"{len(redacted)} redacted" + (note if redacted else "")
)
print(f"license map: {len(licensed)} files")
print(f"renamed files: {renamed['unchanged']} unchanged, {renamed['edited']} edited (provenance/renames.csv)")
print(f"paths named in README.md and docs/protocols.md: {named}")
if derivations:
    print(
        f"derived files: {len(derived)} with third-party quotations replaced "
        "(original SHA-256 and the hash of each omitted text in provenance/derived_files.csv)"
    )
for problem in bad[:20]:
    print("  ", problem)
for rel in unlisted[:20]:
    print("   unlisted:", rel)


def receipt(freeze, *arguments, cwd=None):
    command = ["openssl", "ts", "-verify", *map(str, arguments), *map(str, TSA)]
    r = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    answer = r.stdout + r.stderr
    verdict = [line for line in answer.splitlines() if line.startswith("Verification")]
    print(f"RFC 3161 Freeze {freeze}: {verdict[0] if verdict else answer.strip()[-200:]}")
    if verdict != ["Verification: OK"]:
        bad.append(f"RFC 3161 receipt of Freeze {freeze} does not verify")


if args.tsr:
    for k in "AB":
        receipt(k, "-in", f"FREEZE_{k}.tsr", "-queryfile", f"FREEZE_{k}.tsq", cwd=MQT_FREEZE)
    note = " (original SHA-256 in provenance/redactions.csv equals the timestamped hash)"
    for k in "AB":
        manifest = hash_list(MQT_FREEZE / f"FREEZE_{k}.sha256")
        matching, as_redacted, other = 0, 0, 0
        for digest, rel in manifest:
            rel = "data/prospective/mqt_bench/" + rel.removeprefix("./")
            record = redactions.get(rel, {})
            if not differs(rel, digest):
                matching += 1
            elif record.get("original_sha256") == digest and not differs(rel, record["release_sha256"]):
                as_redacted += 1
            else:
                other += 1
        print(
            f"MQT Bench Freeze {k} manifest: {len(manifest)} entries, {matching} matching, {as_redacted} "
            f"redacted"
            + (note if as_redacted else "")
            + f", {other} other"
        )
        if other:
            bad.append(f"MQT Bench Freeze {k} manifest: {other} entries match neither the file nor a redaction record")
    for k in "CD":
        receipt(k, "-in", PROVENANCE / f"FREEZE_{k}.tsr", "-data", PROVENANCE / f"FREEZE_{k}.sha256")
        manifest = freezes[k]
        matching = sum(name in PLANS and not differs(PLANS[name], digest) for digest, name in manifest)
        print(
            f"Freeze {k} manifest: {len(manifest)} {'entry' if len(manifest) == 1 else 'entries'}, "
            f"{matching} matching "
            + ", ".join(PLANS.get(name, name) for _, name in manifest)
        )
        if matching != len(manifest):
            bad.append(f"Freeze {k} manifest does not match the {'plan' if len(manifest) == 1 else 'plans'}")
sys.exit(1 if bad or unlisted else 0)
