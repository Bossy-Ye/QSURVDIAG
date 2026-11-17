"""Verify the package against provenance/checksums.sha256, the archived content against source_manifest.csv, the
renamed files against provenance/RENAMES.csv, and that provenance/LICENSE_MAP.csv gives a license and a role for every
file.

Usage:  python3 scripts/verify_integrity.py [--tsr]
With --tsr (needs OpenSSL), also verifies the RFC 3161 receipts of Freezes A to D: the MQT Bench freeze (A, B), the
designs of the separating-setting, developer-suite and later-position experiments (C) and the extension of separating
settings to the later positions (D).

Archived files that this release redacts are listed in provenance/REDACTIONS.csv, and the archived file whose
third-party quotations it replaces is listed in provenance/DERIVED_FILES.csv. They are reported separately: their
release hash is checked against that record, and they are never counted as matching their original source hash or
the timestamped freeze manifest.
"""

import csv, fnmatch, hashlib, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Top-level names that serve the repository only; the release archive leaves them out (.gitattributes, export-ignore).
REPOSITORY_ONLY = (".github", ".gitignore", ".gitattributes")
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
    if not line.strip() or line.startswith("#"):
        continue
    h, rel = line.split("  ", 1)
    listed.add(rel)
    p = ROOT / rel
    if not p.is_file():
        bad.append(f"missing: {rel}")
    elif sha(p) != h:
        bad.append(f"changed: {rel}")
present = {
    str(p.relative_to(ROOT))
    for p in ROOT.rglob("*")
    if p.is_file()
    and p.relative_to(ROOT).parts[0] not in ("output", ".git", *REPOSITORY_ONLY)
    and "__pycache__" not in p.parts
}
extra = sorted(present - listed - {"provenance/checksums.sha256"})
archived, redacted, derived = set(), [], []
for r in csv.DictReader(open(ROOT / "provenance/source_manifest.csv")):
    p = ROOT / r["package_path"]
    archived.add(r["package_path"])
    x = RED.get(r["package_path"])
    if x is not None:
        if x["original_sha256"] != r["sha256"]:
            bad.append(f"redaction record disagrees with the source hash: {r['package_path']}")
        elif not p.is_file() or sha(p) != x["release_sha256"]:
            bad.append(f"redacted file differs from its redaction record: {r['package_path']}")
        elif r["package_path"] not in redacted:
            redacted.append(r["package_path"])
        continue
    x = DER.get(r["package_path"])
    if x is not None:
        if x["original_sha256"] != r["sha256"]:
            bad.append(f"derived-file record disagrees with the source hash: {r['package_path']}")
        elif not p.is_file() or sha(p) != x["release_sha256"]:
            bad.append(f"derived file differs from its record: {r['package_path']}")
        elif r["package_path"] not in derived:
            derived.append(r["package_path"])
        continue
    if not p.is_file() or sha(p) != r["sha256"]:
        bad.append(f"archived file differs from its source hash: {r['package_path']}")
LIC = list(csv.DictReader(open(ROOT / "provenance/LICENSE_MAP.csv")))
lic = {r["package_path"] for r in LIC}
bad += [f"license-map row without a role: {r['package_path']}" for r in LIC if not (r.get("role") or "").strip()]
bad += [f"no license-map row: {k}" for k in sorted(present - lic - {"provenance/checksums.sha256"})]
bad += [f"license-map row without a file: {k}" for k in sorted(lic - present)]
bad += [f"redaction record without a source-manifest row: {k}" for k in RED if k not in archived]
bad += [f"derived-file record without a source-manifest row: {k}" for k in DER if k not in archived]
# provenance/RENAMES.csv: every file whose name changed since version 1.3.0. The change is "none" exactly when the
# earlier and present hashes are equal; a file added after version 1.3.0 states so before the kind of change.
renamed = {"unchanged": 0, "edited": 0}
for r in csv.DictReader(open(ROOT / "provenance/RENAMES.csv")):
    p = ROOT / r["package_path"]
    kind = r["change"].split("added after version 1.3.0; ", 1)[-1]
    if not p.is_file():
        bad.append(f"renamed file missing: {r['package_path']}")
    elif sha(p) != r["sha256"]:
        bad.append(f"renamed file differs from its RENAMES.csv hash: {r['package_path']}")
    elif not kind or (kind == "none") != (r["earlier_sha256"] == r["sha256"]):
        bad.append(f"RENAMES.csv change does not agree with the two hashes: {r['package_path']}")
    else:
        renamed["unchanged" if kind == "none" else "edited"] += 1
# Paths named in README.md and docs/protocols.md. A name in single backticks is a path when it holds a "/" or ends in a
# file extension; it must equal a package file or folder, end one, or match one as a pattern. Exceptions: the earlier
# paths of provenance/RENAMES.csv, the plan names that the Freeze C and D manifests timestamp, the study files that
# docs/protocols.md (section 9) names as not released, and NOT_IN_PACKAGE.
NOT_RELEASED = (
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
)
NOT_IN_PACKAGE = (
    "programs.json",  # runner inputs that data/position/select_mutants.py writes (docs/protocols.md, section 7)
    "mutant_gates.json",
    "X2_INPUTS.jsonl",  # plan names without a file of their own (docs/protocols.md, section 10)
    "X2_RUNTIME_CHECK.json",
    "revision2/",  # a working folder of the study (docs/protocols.md, section 9)
    "qra_cases_v1_1/QRA_360",  # a corpus case key (docs/protocols.md, section 11)
)
earlier = [r["earlier_path"] for r in csv.DictReader(open(ROOT / "provenance/RENAMES.csv"))]
frozen = [
    l.split("  ", 1)[1]
    for f in ("FREEZE_C.sha256", "FREEZE_D.sha256")
    for l in (ROOT / "provenance" / f).read_text().splitlines()
    if l.strip()
]
folders = {str(q) + "/" for k in present for q in Path(k).parents if str(q) != "."}
named = 0
for doc in ("README.md", "docs/protocols.md"):
    text = re.sub(r"```.*?```", "", (ROOT / doc).read_text(), flags=re.S)
    for t in re.findall(r"`([^`\n]+)`", text):
        if " " in t or not ("/" in t or re.search(r"[\w*-]\.[A-Za-z0-9*]{1,8}$", t)):
            continue
        named += 1
        hit = lambda names: any(fnmatch.fnmatchcase(k, t) or fnmatch.fnmatchcase(k, "*/" + t) for k in names)
        if not (hit(present) or hit(folders) or hit(earlier) or t in frozen or t in NOT_RELEASED + NOT_IN_PACKAGE):
            bad.append(f"{doc} names a path that is not in the package: {t}")
if (ROOT / "expected/verify_summary.txt").read_text() not in (ROOT / "README.md").read_text():
    bad.append("README.md does not show expected/verify_summary.txt verbatim")
print(
    f"checksums: {len(listed)} files listed (every file except provenance/checksums.sha256 itself), {len(bad)} problems, {len(extra)} unlisted files"
)
print(
    f"archived files: {len(archived) - len(redacted) - len(derived)} identical to their source hash, {len(redacted)} redacted"
    + (
        " (original SHA-256 and the hash of each removed text in provenance/REDACTIONS.csv)"
        if redacted
        else ""
    )
)
print(f"license map: {len(lic)} files")
print(f"renamed files: {renamed['unchanged']} unchanged, {renamed['edited']} edited (provenance/RENAMES.csv)")
print(f"paths named in README.md and docs/protocols.md: {named}")
if DER:
    print(
        f"derived files: {len(derived)} with third-party quotations replaced (original SHA-256 and the hash of each omitted text in provenance/DERIVED_FILES.csv)"
    )
for b in bad[:20]:
    print("  ", b)
for x in extra[:20]:
    print("   unlisted:", x)
if "--tsr" in sys.argv:
    fz = ROOT / "data/prospective/mqt_bench/freeze"
    for k in ("A", "B"):
        r = subprocess.run(
            [
                "openssl",
                "ts",
                "-verify",
                "-in",
                f"FREEZE_{k}.tsr",
                "-queryfile",
                f"FREEZE_{k}.tsq",
                "-CAfile",
                "tsa/freetsa_cacert.pem",
                "-untrusted",
                "tsa/freetsa_tsa.crt",
            ],
            cwd=fz,
            capture_output=True,
            text=True,
        )
        verdict = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Verification")]
        print(f"RFC 3161 Freeze {k}: {verdict[0] if verdict else (r.stdout + r.stderr).strip()[-200:]}")
        if verdict != ["Verification: OK"]:
            bad.append(f"RFC 3161 receipt of Freeze {k} does not verify")
    for k in ("A", "B"):
        lines = [
            l.split("  ", 1)
            for l in (fz / f"FREEZE_{k}.sha256").read_text().splitlines()
            if l.strip() and not l.startswith("#")
        ]
        match, red, miss = 0, [], []
        for h, rel in lines:
            p = fz.parent / rel
            pkg = "data/prospective/mqt_bench/" + (rel[2:] if rel.startswith("./") else rel)
            if p.is_file() and sha(p) == h:
                match += 1
            elif (
                pkg in RED
                and RED[pkg]["original_sha256"] == h
                and p.is_file()
                and sha(p) == RED[pkg]["release_sha256"]
            ):
                red.append(pkg)
            else:
                miss.append(rel)
        print(
            f"MQT Bench Freeze {k} manifest: {len(lines)} entries, {match} matching, {len(red)} redacted"
            + (" (original SHA-256 in provenance/REDACTIONS.csv equals the timestamped hash)" if red else "")
            + f", {len(miss)} other"
        )
        if miss:
            bad.append(
                f"MQT Bench Freeze {k} manifest: {len(miss)} entries match neither the file nor a redaction record"
            )
    pv = ROOT / "provenance"
    fz = ROOT / "data/prospective/mqt_bench/freeze"
    r = subprocess.run(
        [
            "openssl",
            "ts",
            "-verify",
            "-in",
            str(pv / "FREEZE_C.tsr"),
            "-data",
            str(pv / "FREEZE_C.sha256"),
            "-CAfile",
            str(fz / "tsa/freetsa_cacert.pem"),
            "-untrusted",
            str(fz / "tsa/freetsa_tsa.crt"),
        ],
        capture_output=True,
        text=True,
    )
    verdict = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Verification")]
    print(f"RFC 3161 Freeze C: {verdict[0] if verdict else (r.stdout + r.stderr).strip()[-200:]}")
    if verdict != ["Verification: OK"]:
        bad.append("RFC 3161 receipt of Freeze C does not verify")
    PLAN = {
        "X1_OBSERVATION_CHANGE.md": "data/observation_change/PLAN.md",
        "X2_DEVELOPER_SUITES.md": "data/developer_suites/PLAN.md",
        "X4_POSITION.md": "data/position/PLAN.md",
    }
    lines = [l.split("  ", 1) for l in (pv / "FREEZE_C.sha256").read_text().splitlines() if l.strip()]
    match = sum(sha(ROOT / PLAN[n]) == h for h, n in lines)
    print(
        f"Freeze C manifest: {len(lines)} entries, {match} matching " + ", ".join(PLAN[n] for _, n in lines)
    )
    if match != len(lines):
        bad.append("Freeze C manifest does not match the plans")
    r = subprocess.run(
        [
            "openssl",
            "ts",
            "-verify",
            "-in",
            str(pv / "FREEZE_D.tsr"),
            "-data",
            str(pv / "FREEZE_D.sha256"),
            "-CAfile",
            str(fz / "tsa/freetsa_cacert.pem"),
            "-untrusted",
            str(fz / "tsa/freetsa_tsa.crt"),
        ],
        capture_output=True,
        text=True,
    )
    verdict = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Verification")]
    print(f"RFC 3161 Freeze D: {verdict[0] if verdict else (r.stdout + r.stderr).strip()[-200:]}")
    if verdict != ["Verification: OK"]:
        bad.append("RFC 3161 receipt of Freeze D does not verify")
    ((h, n),) = [l.split("  ", 1) for l in (pv / "FREEZE_D.sha256").read_text().splitlines() if l.strip()]
    ok = n == "X1_POSITION_EXTENSION.md" and sha(ROOT / "data/observation_change/POSITION_EXTENSION.md") == h
    print(f"Freeze D manifest: 1 entry, {int(ok)} matching data/observation_change/POSITION_EXTENSION.md")
    if not ok:
        bad.append("Freeze D manifest does not match the plan")
sys.exit(1 if bad or extra else 0)
