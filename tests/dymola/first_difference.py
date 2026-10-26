"""Where do the Linux and Windows Dymola results of one run first differ? (diagnostic of the self-comparison)

Reads the two dsres.mat files of a run, maps every stored variable by NAME (the two translations may store a
different set of columns), and reports
  - the stored points and the stored time instants of each file, and the instants only one of them has;
  - the first stored point (within the first --points points) at which any variable differs, which variables
    differ there (with both values), and, for the first --show variables to differ, their first differing time;
  - for every point index where the two files store a different number of points at one instant, the values.

Usage: python -I -B first_difference.py --linux <dsres.mat> --windows <dsres.mat> [--points 200000] [--show 25]
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsres import DsRes  # noqa: E402


def instants(t):
    new = np.ones(len(t), dtype=bool)
    new[1:] = (t[1:] - t[:-1]) > 1e-9
    f = np.flatnonzero(new)
    cnt = np.diff(np.append(f, len(t)))
    return t[f], cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--linux', required=True)
    ap.add_argument('--windows', required=True)
    ap.add_argument('--points', type=int, default=200000)
    ap.add_argument('--show', type=int, default=25)
    a = ap.parse_args()
    L, W = DsRes(a.linux), DsRes(a.windows)
    tl, tw = L.time(), W.time()
    print('stored points: linux %d, windows %d; data_2 columns: linux %d, windows %d; variables: %d / %d'
          % (L.npoints, W.npoints, L.data_2.shape[1], W.data_2.shape[1], len(L.names), len(W.names)))
    il, cl = instants(tl)
    iw, cw = instants(tw)
    print('distinct instants: linux %d, windows %d' % (len(il), len(iw)))
    if len(il) == len(iw) and np.all(np.abs(il - iw) < 1e-9):
        k = np.flatnonzero(cl != cw)
        print('same instants; instants with a different number of stored points: %d' % k.size)
        for j in k[:10]:
            print('  t = %r: linux %d points, windows %d points' % (float(il[j]), cl[j], cw[j]))
    names = [n for n in L.names if L.has(n) and W.has(n) and L.info[n][0] == 2 and W.info[n][0] == 2]
    n = min(L.npoints, W.npoints, a.points)
    if L.npoints != W.npoints:
        k = np.flatnonzero(np.abs(tl[:n] - tw[:n]) > 0)
        if k.size:
            n = int(k[0])
            print('time vectors differ from point %d (t = %r) on; points compared: %d' % (n, float(tl[n]), n))
    first = {}
    for nm in names:
        d = L.values(nm)[:n] != W.values(nm)[:n]
        idx = np.flatnonzero(d)
        if idx.size:
            first[nm] = int(idx[0])
    print('variables stored in data_2 by both: %d; differing within the first %d points: %d' % (len(names), n,
                                                                                               len(first)))
    if not first:
        return 0
    i0 = min(first.values())
    print('first differing point: index %d, t = %r' % (i0, float(tl[i0])))
    at = sorted(nm for nm, i in first.items() if i == i0)
    print('variables that differ there (%d):' % len(at))
    for nm in at[:a.show]:
        print('  %-60s linux %.17g windows %.17g diff %.3g' % (nm, L.values(nm)[i0], W.values(nm)[i0],
                                                                L.values(nm)[i0] - W.values(nm)[i0]))
    order = sorted(first.items(), key=lambda kv: kv[1])
    print('first difference per variable, earliest %d:' % a.show)
    for nm, i in order[:a.show]:
        print('  %-60s t = %.10g (point %d)' % (nm, tl[i], i))
    return 0


if __name__ == '__main__':
    sys.exit(main())
