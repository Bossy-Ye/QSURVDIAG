"""Separating setting (X1 rule) of the QED-C constructed pair (P, P_Z) at widths 2-8, from ideal states."""
import itertools, sys
from math import pi
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/lib"))
import numpy as np
import counts as C

K, TT, H_FIELD, J = 5, 0.2, 1.0, 1.0            # data/qedc: precalculated reference k = 5, t = 0.2
TAU = TT / K


def tfim_gates(n, zz_angle, terminal_z=None):     # data/qedc/case_run.py
    g = [{"gate": "h", "q": [0]}] + [{"gate": "cx", "q": [k - 1, k]} for k in range(1, n)]
    for _ in range(K):
        g += [{"gate": "rx", "q": [i], "angles": [2 * TAU * H_FIELD]} for i in range(n)]
        for j in range(2):
            for i in range(j % 2, n - 1, 2):
                g += [{"gate": "cx", "q": [i, i + 1]}, {"gate": "rz", "q": [i + 1], "angles": [zz_angle]}, {"gate": "cx", "q": [i, i + 1]}]
    if terminal_z is not None: g.append({"gate": "z", "q": [terminal_z]})
    return g


def settings(n):
    for k in range(1, n + 1):
        for qs in itertools.combinations(range(n), k):
            for bs in itertools.product("XY", repeat=k):
                s = ["Z"] * n
                for q, b in zip(qs, bs): s[q] = b
                yield "".join(s), k


if __name__ == "__main__":
  for n in range(2, 9):
    po, pm = C.sv(tfim_gates(n, 2 * TAU * J), n), C.sv(tfim_gates(n, 2 * TAU * J, 0), n)
    assert C.first_witness(np.abs(po) ** 2, np.abs(pm) ** 2, n) is None
    for s, k in settings(n):
        w = C.first_witness(np.abs(C.rotate(po, n, s)) ** 2, np.abs(C.rotate(pm, n, s)) ** 2, n)
        if w is not None:
            print(n, s, k, w[0], w[1], round(w[2], 4)); break
