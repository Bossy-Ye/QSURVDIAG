"""Pass 56E: is the variability caused by the unseeded transpile in qutest.runner.run_test? Read-only; prints only."""
import csv, json, sys, collections
Q = "/Users/mac/Desktop/ZX-STUDY/qsurvcert_pilot"; sys.path.insert(0, f"{Q}/cross_tool_stage/qutest")
from qutest_adapter import make_test
from qutest.parser.qasm_parser import parse_test_source
from qutest.backends import resolve_backend
from qiskit import qasm3, transpile
PM = {r["program"]: r for r in csv.DictReader(open(f"{Q}/final_empirical_study/PROGRAM_MANIFEST.csv"))}
B = resolve_backend("ideal", 42)
for prog in ("dj_4", "bv_4", "bv_5", "dj_3"):
    p = PM[prog]; tc = parse_test_source(make_test(json.loads(p["base_gates"]), int(p["n"]), []))[0]; c = qasm3.loads(tc.qasm_source)
    un = collections.Counter(tuple(sorted({i.operation.name for i in transpile(c, backend=B).data} - {"measure"})) for _ in range(30))
    se = collections.Counter(tuple(sorted({i.operation.name for i in transpile(c, backend=B, seed_transpiler=7).data} - {"measure"})) for _ in range(30))
    print(prog, "unseeded:", dict(un), "| seeded:", dict(se), "| default opt level:", "2")
