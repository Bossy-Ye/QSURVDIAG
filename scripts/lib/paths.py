"""Archived files are addressed by package path and checked against provenance/source_manifest.csv."""
import csv, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
with open(ROOT / "provenance" / "source_manifest.csv", newline="") as _f:
    _LISTED = {_r["package_path"] for _r in csv.DictReader(_f)}


def orig(path):
    """Absolute path of an archived file, given its package path."""
    key = str(path)
    while key.startswith("./"):
        key = key[2:]
    if key in _LISTED:
        return ROOT / key
    raise FileNotFoundError(f"{key} is not an archived file (see provenance/source_manifest.csv)")


class Dir:
    """Package directory whose archived files are resolved through the manifest: Dir('data/certification/outcomes') / name."""
    def __init__(self, prefix):
        self.prefix = str(prefix).rstrip("/")

    def __truediv__(self, name):
        return orig(f"{self.prefix}/{name}")


def out_dir(sub=""):
    """Output directory for regenerated values: $QSD_OUT, else <package>/output. Never inside data/."""
    d = Path(os.environ.get("QSD_OUT", ROOT / "output")) / sub
    d.mkdir(parents=True, exist_ok=True)
    return d
