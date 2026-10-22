"""Assemble the run tree of the packaged v2 implementation (as scripts/reproduce_analytic.py does), for X4."""
import csv, shutil, sys
from pathlib import Path
PKG = Path(sys.argv[1]); RT = Path(sys.argv[2])
if RT.exists(): shutil.rmtree(RT)
byhash = {}
for m in csv.DictReader(open(PKG / "provenance/source_manifest.csv")): byhash.setdefault(m["sha256"], PKG / m["package_path"])
for x in csv.DictReader(open(PKG / "scripts/analytic/r2v_inputs.csv")):
    d = RT / x["path"]; d.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(byhash[x["sha256"]], d)
shutil.copy2(PKG / "scripts/analytic/r2v_lib.py", RT / "artifact/outcomes/r2v_lib.py")
print("files", sum(1 for _ in RT.rglob("*") if _.is_file()))
