"""Package paths. archived() accepts only files listed in provenance/source_manifest.csv."""

import csv, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
with open(ROOT / "provenance/source_manifest.csv", newline="") as f:
    MANIFEST = {r["package_path"] for r in csv.DictReader(f)}
with open(ROOT / "expected/values.csv", newline="") as f:
    CATALOGUE = {r["check_id"]: r for r in csv.DictReader(f)}


def archived(path):
    if str(path) not in MANIFEST:
        raise FileNotFoundError(f"{path} is not listed in provenance/source_manifest.csv")
    return ROOT / path


def output(path):
    """Directory given as --out: created if absent, never inside data/."""
    out = Path(path).resolve()
    if ROOT / "data" in (out, *out.parents):
        sys.exit("refusing to write inside data/")
    out.mkdir(parents=True, exist_ok=True)
    return out


def out_dir(sub=""):
    """Subdirectory of $QSD_OUT, the output directory that an entry script hands to the modules it runs."""
    return output(Path(os.environ.get("QSD_OUT", ROOT / "output")) / sub)
