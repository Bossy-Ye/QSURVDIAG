"""Wrapped-test demonstration for the running example dj_3#e19 (outside the RQ4 census).

A QUTest 0.1.0 test file defines the program under test as a helper function and a test
function that calls it, applies a Hadamard to q2 and asserts the q2 marginal. QUTest's
parser inlines the helper (parser/qasm_parser.py:88). The same file shape runs against the
original and against the mutant, 12 repetitions each at seeds 42-53, N = 2000. The count
test of the declared profile (S_MIN) is run alongside for contrast.
"""
import csv, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2v_lib as V
from e1_lib import MUT, orig, nq
import e1_relations as REL

def gate_line(g, qname="q"):
    a = ("(" + ",".join(f"{x}" for x in g.get("angles", [])) + ")") if g.get("angles") else ""
    return f"{g['gate']}{a} " + ", ".join(f"{qname}[{i}]" for i in g["q"]) + ";"

def wrapped_test(prog_gates, n, ref, seed):
    body = "\n".join("    " + gate_line(g) for g in V.to_text(prog_gates))
    return "\n".join([
        "OPENQASM 3;", 'include "stdgates.inc";', "",
        f"def program(qubit[{n}] q) {{", body, "}", "",
        "def test_phase_visible() {",
        f"    //% shots {V.N_SHOTS}", f"    //% seed {seed}", "    //% backend ideal",
        f"    qubit[{n}] q;", f"    bit[{n}] m;",
        "    program(q);", "    h q[2];", "    m = measure q;",
        f"    //% expect marginal m[2] p1 ~= {ref} atol={V.QA.ATOL}", "}", ""])

def main():
    mid = "dj_3#e19"; m = MUT[mid]; sub = m["subject"]; n = nq[sub]
    H = [{"gate": "h", "q": [2]}]
    pp_h = np.abs(REL._sv(orig[sub] + H, n)) ** 2; pm_h = np.abs(REL._sv(m["gates"] + H, n)) ** 2
    ref = round(V.marg(pp_h, n, 2), 4)
    rows = []
    for who, gates in (("original", orig[sub]), ("mutant", m["gates"])):
        v = [V.QA.run_qutest(wrapped_test(gates, n, ref, s))[0] for s in V.MUT_SEEDS]
        rows.append({"test": "wrapped (H on q2)", "program": who, "kills": sum(x == "KILLED" for x in v),
                     "unsupported": sum(x == "UNSUPPORTED" for x in v), "reps": len(v)})
    # the declared-profile count test on the same pair: S_MIN, analytic references
    pp = np.abs(REL._sv(orig[sub], n)) ** 2
    smin = [V.QA.marginal_assertion(q, round(V.marg(pp, n, q), 4)) for q in (0, 1)]
    for who, gates in (("original", orig[sub]), ("mutant", m["gates"])):
        v = [V.QA.run_qutest(V.QA.make_test(V.to_text(gates), n, smin, V.N_SHOTS, s))[0] for s in V.MUT_SEEDS]
        rows.append({"test": "S_MIN (declared profile)", "program": who, "kills": sum(x == "KILLED" for x in v),
                     "unsupported": sum(x == "UNSUPPORTED" for x in v), "reps": len(v)})
    with open(os.path.join(V.HERE, "R2V_WRAPPED_DEMO.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(os.path.join(V.HERE, "R2V_WRAPPED_DEMO_test.qasm"), "w") as f:
        f.write(wrapped_test(m["gates"], n, ref, 42))
    print("reference P(q2=1) after H, original:", ref, " mutant:", round(V.marg(pm_h, n, 2), 4))
    for r in rows: print(r)

if __name__ == "__main__":
    main()
