"""QUTest adapter contract tests (native; no QuCheck). Non-result-bearing (originals + legality only).
RUN: .venv-qutest-audit/bin/python -m pytest cross_tool_stage/qutest/test_qutest_adapter.py -q
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qutest_adapter as QA
from qutest_adapter import QUTestAdapter, marginal_assertion, nonZ_observable_assertion, make_test


def test_adapter_has_no_qucheck_identifiers():
    tree = ast.parse(open(os.path.join(HERE, "qutest_adapter.py")).read())
    idents = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name): idents.append(node.id.lower())
        elif isinstance(node, ast.Attribute): idents.append(node.attr.lower())
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)): idents.append(node.name.lower())
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            assert node.value != 400, "leaks QuCheck 400"
    for name in idents:
        for tok in ("fisher", "holm", "nstar", "n_star", "qucheck"):
            assert tok not in name, f"QuCheck identifier leaked: {name}"


def test_native_decision_rule_is_tolerance_not_fisher_holm():
    r = QUTestAdapter().native_decision_rule()
    assert r["statistic"].startswith("tolerance")
    assert "fisher_exact" in r["NOT"] and "holm" in r["NOT"] and "qucheck_400" in r["NOT"]


def test_inner_shots_2000_is_experimental_configuration():
    p = QUTestAdapter().provenance()["inner_shots"]
    assert p["value"] == 2000 and p["status"] == "experimental_configuration"
    assert QA.INNER_SHOTS == 2000 and QA.INNER_SHOTS != 400


def test_candidate_legality_zbasis_only():
    ad = QUTestAdapter()
    assert ad.check_candidate_legality(marginal_assertion(1, 0.5))          # Z marginal legal
    assert not ad.check_candidate_legality(nonZ_observable_assertion("X0"))  # non-Z observable illegal


def test_make_test_is_valid_qasm3_and_runs():
    # bell |Phi+> ; assert m[0] p1 ~= 0.5 -> passes (legality/syntax smoke, original only)
    gates = [{"gate": "h", "q": [0]}, {"gate": "cx", "q": [0, 1]}]
    ad = QUTestAdapter()
    status, _ = ad.run_suite(gates, 2, [marginal_assertion(0, 0.5)])
    assert status in ("SURVIVED", "KILLED", "UNSUPPORTED")                   # CLI ran and returned a native decision
    assert status == "SURVIVED"                                             # 0.5 within atol on |Phi+>


def test_non_z_rejected_unsupported():
    gates = [{"gate": "h", "q": [0]}]
    status, _ = QUTestAdapter().run_suite(gates, 1, [nonZ_observable_assertion("X0")])
    assert status == "UNSUPPORTED"                                          # Z-basis contract boundary


def test_adding_assertion_is_not_auto_repair():
    # the adapter only returns a native decision; it never labels anything a "repair".
    src = open(os.path.join(HERE, "qutest_adapter.py")).read().lower()
    assert "repair" not in src                                             # repair is a CORE diagnosis, not an adapter output


def test_resource_vector_is_vector_with_inner_shots():
    rv = QUTestAdapter().resource_vector(3)
    assert rv["assertions"] == 3 and rv["inner_shots"] == 2000 and "circuit_executions" in rv
