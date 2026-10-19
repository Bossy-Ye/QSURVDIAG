"""Analytic relations R_C, R_S, R_O, R_A^theta, R_T^theta from exact states.

Section III definitions, computed exactly (no shots):
  R_S : psi_P(x) ~= psi_M(x) up to a single global phase
  R_O : alpha(psi_P) == alpha(psi_M), the joint computational-Z distribution
  R_A : exists a in U_v(P) with d_a > theta   (enumerated over the closed universe)
  R_T : exists a in Suite with d_a > theta
R_C is the recorded contract relation; it is a property of the declaration.
"""
import json, numpy as np
from qsurvdiag_confirmatory import T, F, U, exists_above
from functools import lru_cache
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from e1_lib import orig, nq, outreg, MUT, suite_terms, SSPEC
THETA = 0.05
TOL = 1e-9

def _sv(gates, n):
    qc = QuantumCircuit(n)
    for g in gates:
        a = g.get("angles", [])
        (getattr(qc, g["gate"])(*a, *[int(x) for x in g["q"]]) if a
         else getattr(qc, g["gate"])(*[int(x) for x in g["q"]]))
    return Statevector.from_int(0, dims=(2,) * n).evolve(qc).data

def probs(sv):
    return np.abs(sv) ** 2

def state_equal(a, b, tol=TOL):
    """Equality up to a single global phase."""
    ov = np.vdot(a, b)
    return bool(abs(abs(ov) - 1.0) < tol)

def obs_equal(pa, pb, tol=TOL):
    return bool(np.max(np.abs(pa - pb)) < tol)

def marginal_p1(p, n, q):
    idx = np.arange(len(p))
    return float(p[(idx >> q) & 1 == 1].sum())

def zprod(p, n, qs):
    idx = np.arange(len(p))
    s = np.ones(len(p))
    for q in qs:
        s = s * np.where((idx >> q) & 1 == 1, -1.0, 1.0)
    return float((p * s).sum())

def universe_diffs(pa, pb, n):
    """d_a for every instance of the closed count-substrate universe:
       marginal (n) + observable Z-strings (2^n - 1) + probability (2^n)
       + entropy (1) + distribution (1)  =  2^(n+1) + n + 1."""
    d = []
    for q in range(n):
        d.append(abs(marginal_p1(pa, n, q) - marginal_p1(pb, n, q)))
    for m in range(1, 2 ** n):
        qs = [q for q in range(n) if (m >> q) & 1]
        d.append(abs(zprod(pa, n, qs) - zprod(pb, n, qs)))
    d.extend(np.abs(pa - pb).tolist())
    ea = float(-(pa[pa > 0] * np.log2(pa[pa > 0])).sum())
    eb = float(-(pb[pb > 0] * np.log2(pb[pb > 0])).sum())
    d.append(abs(ea - eb))
    d.append(float(0.5 * np.abs(pa - pb).sum()))
    return d

def suite_diffs(pa, pb, n, terms):
    out = []
    for t in terms:
        if len(t) == 1:
            out.append(abs(marginal_p1(pa, n, t[0]) - marginal_p1(pb, n, t[0])))
        else:
            out.append(abs(zprod(pa, n, list(t)) - zprod(pb, n, list(t))))
    return out

def sspec_diffs(pa, pb, n, sub):
    """d_a for the S_SPEC assertions: marginals at their specification value, or a
    distribution total-variation against the specification reference."""
    out = []
    for a in SSPEC[sub]:
        tok = a.split()
        if tok[2] == "marginal":
            q = int(tok[3].split("[")[1].split("]")[0])
            ref = float(tok[6])
            out.append(abs(marginal_p1(pb, n, q) - ref) - abs(marginal_p1(pa, n, q) - ref))
        elif tok[2] == "distribution" and "ref" in a:
            refd = json.loads(a.split("ref", 1)[1].strip())
            r = np.zeros(2 ** n)
            for k, v in refd.items():
                r[int(k, 2)] = v
            out.append(float(0.5 * np.abs(pb - r).sum()) - float(0.5 * np.abs(pa - r).sum()))
    return [abs(x) for x in out]

@lru_cache(maxsize=None)
def _orig_cache(sub):
    n = nq[sub]; sv = _sv(orig[sub], n); return sv, probs(sv), n

def relations(mutant_id, suite, contract_equivalent):
    m = MUT[mutant_id]; sub = m["subject"]
    sva, pa, n = _orig_cache(sub)
    svb = _sv(m["gates"], n); pb = probs(svb)
    R_S = state_equal(sva, svb)
    R_O = obs_equal(pa, pb)
    # CORRECTION 9 (conformance category 9), applied here as at every other site
    # that compares an analytic difference against theta.  The superseded lines were
    #     R_A = bool(max(universe_diffs(...)) > THETA)
    #     R_T = bool(sd and max(sd) > THETA)
    # which return a boolean at margins the simulator, not the mathematics, decides.
    # universe_diffs already spans U_v(P) entire, so correction 8 needs nothing here.
    ud = universe_diffs(pa, pb, n)
    R_A = exists_above(ud, THETA)
    if suite == "S_SPEC":
        sd = sspec_diffs(pa, pb, n, sub)
    else:
        sd = suite_diffs(pa, pb, n, suite_terms(sub)[suite])
    R_T = exists_above(sd, THETA) if sd else F
    return {"R_C": T if contract_equivalent else F, "R_S": T if R_S else F,
            "R_O": T if R_O else F,
            "R_A": R_A, "R_T": R_T,
            "max_suite_d_a": float(max(sd)) if sd else 0.0,
            "max_universe_d_a": float(max(ud))}
