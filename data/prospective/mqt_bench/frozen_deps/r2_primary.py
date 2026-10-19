"""Revision 2, step 3: analytic rerun over the frozen primary population (599 pairs).

Reads only frozen inputs (the packaged e1_lib / e1_relations definitions and the frozen
599 ledgers) and writes only under revision2/. Three universes are evaluated:

  U5    the frozen enumeration: marginal, Pauli-Z product, basis-state probability,
        entropy, and one distribution assertion (total variation). Must reproduce the
        frozen ledgers exactly; this is the validation.
  Ucert the certifying set of the frozen Phase-0 protocol with the distribution family
        instantiated at every analytic metric QUTest 0.1.0 ships: total variation,
        Hellinger and KL (formulas copied from qutest/assertions/distribution.py).
        The chi-squared metric is a significance test on N shots and has no analytic
        tolerance form; it is reported structurally, not enumerated.
  Ucond Ucert plus the kinds the frozen protocol classed as conditional and that read
        counts: Pearson correlation for every qubit pair (QUTest's constant-bit
        convention) and most-frequent (an argmax check, robust separation only).

For every CL3 pair it also evaluates the tool's entanglement witness over every cut.
"""
import csv, json, os, sys, time, itertools
import numpy as np
sys.path.insert(0, "/Users/mac/Desktop/ZX-STUDY/paper-artifact/github/code/qsurvdiag")
import e1_lib as L, e1_relations as REL
from qsurvdiag_confirmatory import exists_above, T, F, U
def tri(v): return "true" if v is T else ("false" if v is F else "undecided")

R = "/Users/mac/Desktop/ZX-STUDY/paper-artifact/github/results/recovered/"
OUT = os.path.dirname(os.path.abspath(__file__))
THETAS = [0.01, 0.025, 0.05, 0.10, 0.25, 0.50]

def hellinger(p, q):
    return float(np.sqrt(0.5 * np.sum((np.sqrt(p) - np.sqrt(q)) ** 2)))

def kl(p, q):
    eps = 1e-12
    ps, qs = np.clip(p, eps, None), np.clip(q, eps, None)
    return float(np.sum(ps * np.log(ps / qs)))

def bit_moments(p, n):
    idx = np.arange(len(p))
    bits = [((idx >> q) & 1).astype(float) for q in range(n)]
    mean = [float((p * b).sum()) for b in bits]
    return bits, mean

def pearson_all(p, n):
    bits, mean = bit_moments(p, n)
    out = {}
    for i, j in itertools.combinations(range(n), 2):
        vi, vj = mean[i] * (1 - mean[i]), mean[j] * (1 - mean[j])
        if vi <= 1e-15 or vj <= 1e-15:
            if vi <= 1e-15 and vj <= 1e-15:
                out[(i, j)] = 1.0 if abs(mean[i] - mean[j]) <= 1e-15 else 0.0
            else:
                out[(i, j)] = 0.0
            continue
        cov = float((p * bits[i] * bits[j]).sum()) - mean[i] * mean[j]
        out[(i, j)] = cov / np.sqrt(vi * vj)
    return out

def most_frequent_sep(pa, pb, tie=1e-12):
    """1.0 if the original has a unique argmax b* and b* is not a maximizer of the
    mutant; 0.0 if both have the same unique argmax; None if a tie makes the
    assertion's reference or verdict depend on sampling."""
    ma = pa.max(); top = np.flatnonzero(pa >= ma - tie)
    if len(top) != 1: return None
    b = top[0]; mb = pb.max()
    if pb[b] >= mb - tie:
        return 0.0 if len(np.flatnonzero(pb >= mb - tie)) == 1 else None
    return 1.0

def cut_entropies(sv, n):
    """Von Neumann entropy of every cut B (non-empty, proper, up to complement),
    as QUTest's witness computes it: eigenvalues <= 1e-12 dropped, log base 2."""
    psi = sv.reshape([2] * n)[::-1] if False else sv  # ordering handled by axes below
    t = sv.reshape([2] * n)  # axis k <-> qubit n-1-k (little-endian index)
    res = {}
    for r in range(1, n // 2 + 1):
        for B in itertools.combinations(range(n), r):
            if r == n - r and 0 not in B: continue  # complement already visited
            axes_B = [n - 1 - q for q in B]
            axes_R = [a for a in range(n) if a not in axes_B]
            m = np.transpose(t, axes_B + axes_R).reshape(2 ** r, -1)
            s = np.linalg.svd(m, compute_uv=False) ** 2
            s = s[s > 1e-12]
            res[B] = float(-np.sum(s * np.log2(s))) if len(s) else 0.0
    return res

def witness_separation(sva, svb, n):
    ea, eb = cut_entropies(sva, n), cut_entropies(svb, n)
    sep = [B for B in ea if (ea[B] > 1e-6) != (eb[B] > 1e-6)]
    margins = [min(abs(ea[B] - 1e-6), abs(eb[B] - 1e-6)) for B in sep]
    return len(ea), sep, (min(margins) if margins else None), \
        (max(abs(ea[B] - eb[B]) for B in sep) if sep else 0.0)

def main():
    ref = {r["mutant_id"]: r for r in csv.DictReader(open(R + "599_B1_REFERENCE_RERUN_FRESH.csv"))}
    tol = {}
    for r in csv.DictReader(open(R + "599_B2_TOLERANCE_FRESH.csv")):
        tol[(r["mutant_id"], float(r["theta"]))] = r
    rows, t0 = [], time.time()
    for mid, fr in ref.items():
        m = L.MUT[mid]; sub = m["subject"]
        sva, pa, n = REL._orig_cache(sub)
        svb = REL._sv(m["gates"], n); pb = REL.probs(svb)
        ud5 = REL.universe_diffs(pa, pb, n)
        extra = [hellinger(pb, pa), kl(pb, pa)]
        ca, cb = pearson_all(pa, n), pearson_all(pb, n)
        corr = [abs(ca[k] - cb[k]) for k in ca]
        mf = most_frequent_sep(pa, pb)
        row = {"mutant_id": mid, "subject": sub, "n": n, "report": fr["diagnostic_outcome"],
               "frozen_max_U5": (float(fr["max_universe_d_a"]) if fr["max_universe_d_a"] else None), "max_U5": max(ud5),
               "hellinger": extra[0], "kl": extra[1],
               "max_corr": max(corr) if corr else 0.0, "most_frequent_sep": mf}
        for th in THETAS:
            a5 = exists_above(ud5, th)
            ac = exists_above(ud5 + extra, th)
            ad = exists_above(ud5 + extra + corr + ([mf] if mf is not None else []), th)
            ft = tol.get((mid, th))
            row[f"RA5_{th}"] = tri(a5); row[f"RAcert_{th}"] = tri(ac); row[f"RAcond_{th}"] = tri(ad)
            if ft is not None:
                row[f"frozen_RA_{th}"] = ft["R_A"]
                row[f"cl5cand_frozen_{th}"] = ft["analytic_candidate"] == "CL5"
                base = ft["R_C"] == "false" and ft["R_S"] == "false" and ft["R_O"] == "false"
                row[f"base_{th}"] = base
        if fr["diagnostic_outcome"] == "CL3":
            k, sep, mg, gap = witness_separation(sva, svb, n)
            row.update({"witness_cuts": k, "witness_separating_cuts": len(sep),
                        "witness_min_margin": mg, "witness_max_entropy_gap": gap})
        rows.append(row)
    keys = sorted({k for r in rows for k in r})
    with open(os.path.join(OUT, "R2_PRIMARY_PAIRS.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("pairs", len(rows), "seconds", round(time.time() - t0, 1))

if __name__ == "__main__":
    main()
