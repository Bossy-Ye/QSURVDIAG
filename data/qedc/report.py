"""Reporting path with the original-validity precondition enforced in code.

Reads CASE_RESULTS.json and NATIVE_RUNS.csv (the frozen run) and REANALYSIS_RUNS.csv (the same seeded
histograms evaluated under T, the stored-E-referenced method-2 rule, and T', the admitted P-referenced Hellinger
instance of U(P)). For every pair and width it reports, per evaluation stage, the original's validity and the
counterpart's verdicts, and admits a diagnosis only when the executed baseline is an admitted instance (T') and the
original passes it (false failures at most 1 of 12, the OB02 rule). The runner's raw certify() output is retained.
Usage: python -I report.py <package root> <run tree> <precalculated_data.json> <qedc dir>
"""
import csv, json, sys, collections
from pathlib import Path
PKG, TREE, REFP, D = (Path(a).resolve() for a in sys.argv[1:5])
src = open(PKG / "data/qedc/case_run.py").read().split("# ------------------------------------------------------------------ native runner")[0]
sys.argv = ["x", str(PKG), str(TREE), str(REFP), str(D)]
g = {"__name__": "report"}; exec(src, g)
np, T, F, U = g["np"], g["T"], g["F"], g["U"]
from qsurvdiag_confirmatory import candidate, certify, empirical   # noqa: E402

R = g["R"]
case = {(c["pair"], c["n"]): c for c in json.load(open(D / "CASE_RESULTS.json"))["cases"]}
runs = collections.defaultdict(list)
for r in csv.DictReader(open(D / "NATIVE_RUNS.csv")): runs[(r["pair"], int(r["n"]), r["run"])].append(r["verdict"])
re_ = collections.defaultdict(list); hval = collections.defaultdict(list)
for r in csv.DictReader(open(D / "REANALYSIS_RUNS.csv")):
    re_[(r["pair"], int(r["n"]), r["run"], r["predicate"])].append(r["verdict"]); hval[(r["pair"], int(r["n"]), r["run"], r["predicate"])].append(float(r["hellinger"]))
K = lambda v: sum(x == "KILLED" for x in v)

def valid(fails): return fails / R <= 0.10                               # OB02: original false-failure rate <= 0.10

def admit(label, n):
    c = case[(label, n)]
    a, b = ("P", "M") if label == "natural" else ("P", "C")
    pa = np.abs(g["state"](g["PROG"][a](n), n)) ** 2; pb = np.abs(g["state"](g["PROG"][b](n), n)) ** 2
    ordered, alld = g["ordered_universe"](pa, pb, n)
    d_hel = next(x["d"] for x in ordered if x["kind"] == "hellinger")
    rel = {k: {"true": T, "false": F, "undecided": U}[v] for k, v in c["relations"].items()}
    if rel["R_O"] is F:                                                   # R_T over the admitted executed suite {T'}
        rel["R_T"] = T if g["compare_threshold"](d_hel, g["THETA"]) is T else F
    tp_o, tp_m = K(re_[(label, n, "A_orig_cert", "Tprime")]), K(re_[(label, n, "A_mut_cert", "Tprime")])
    ev = {"OB01": "satisfied", "OB04": "satisfied", "OB05": "satisfied", "OB06": "satisfied",
          "OB07": "satisfied" if rel["R_O"] is not U else "unknown", "OB08": "satisfied", "OB09": "satisfied",
          "OB10": "satisfied" if len(alld) == 2 ** (n + 1) + n + 3 else "failed", "OB14": "satisfied",
          "OB17": "satisfied", "OB18": "satisfied", "OB19": "satisfied", "OB02": "satisfied" if valid(tp_o) else "failed"}
    cand, _, _ = candidate(rel)
    if cand == "CL5": ev["OB16"] = "satisfied" if g["compare_threshold"](c["max_admitted_d"], g["THETA"]) is F else "failed"
    if cand == "CL4":
        w = c["witness"]; ev.update({"OB11": "satisfied", "OB12": "satisfied", "OB16": "satisfied" if g["compare_threshold"](w["d"], g["THETA"]) is T else "failed"})
        wg, wm, cg, cm = (runs.get((label, n, t)) for t in ("W_orig_guard", "W_mut_cert", "Ctl_orig_guard", "Ctl_mut_cert"))
        if (wg and K(wg)) or (cg and K(cg)): ev["OB02"] = "failed"
        ev["OB13"] = "unknown" if (wg and K(wg)) else ("satisfied" if K(wm) == R else "failed")
        ev["OB15"] = "unknown" if (cm is None or (cg and K(cg))) else ("failed" if K(cm) == R else "satisfied")
    rep = certify(rel, ev, empirical_verdict=empirical(tp_m, R))
    precondition = valid(tp_o)
    reported = rep["report"] if precondition else "not evaluable (original-validity check failed)"
    xs = lambda t: f"{K(runs[(label, n, t)])}/{len(runs[(label, n, t)])}" if (label, n, t) in runs else "-"
    x_ok = (label, n, "X_mut_val") in runs and K(runs[(label, n, "X_mut_val")]) == R and K(runs[(label, n, "X_orig_val")]) <= 1
    return {"pair": label, "n": n, "candidate": cand, "U(P)_hellinger_d": d_hel,
            "T_E_original_fails_cert": K(runs[(label, n, "A_orig_cert")]), "T_E_counterpart_kills_cert": K(runs[(label, n, "A_mut_cert")]),
            "Tprime_original_fails_cert": tp_o, "Tprime_counterpart_kills_cert": tp_m,
            "Tprime_original_fails_val": K(re_[(label, n, "A_orig_val", "Tprime")]), "Tprime_counterpart_kills_val": K(re_[(label, n, "A_mut_val", "Tprime")]),
            "Tprime_original_hellinger_mean": float(np.mean(hval[(label, n, "A_orig_cert", "Tprime")])),
            "T_E_original_hellinger_mean": float(np.mean(hval[(label, n, "A_orig_cert", "T")])),
            "baseline_valid": precondition, "certify_raw": rep["report"], "certify_unmet": ";".join(rep.get("failed", []) + rep.get("unknown", [])),
            "reported": reported, "runner_raw_report_under_T": c["report"],
            "B_combined_original_fails_val": xs("B_orig_val"), "B_combined_counterpart_kills_val": xs("B_mut_val"),
            "X_original_guard": xs("X_orig_guard"), "X_counterpart_cert": xs("X_mut_cert"),
            "X_original_val": xs("X_orig_val"), "X_counterpart_val": xs("X_mut_val"), "X_supported": x_ok}

rows = [admit(lab, n) for lab in ("natural", "constructed") for n in g["WIDTHS"]]
# rule checks on one invalid and one valid saved cell
inv = next(r for r in rows if r["pair"] == "constructed" and r["n"] == 6); val = next(r for r in rows if r["pair"] == "constructed" and r["n"] == 3)
assert inv["baseline_valid"] is False and inv["reported"].startswith("not evaluable"), inv
assert val["baseline_valid"] is True and val["reported"] == val["certify_raw"], val
with open(D / "REPORT.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
for r in rows: print({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
