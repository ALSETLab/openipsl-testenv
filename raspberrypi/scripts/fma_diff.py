"""fma_diff.py: worst difference per signal between two OpenModelica CSV records of the same runs (contract grid).

Usage: python3 -I fma_diff.py <record A> <record B> <run> [<run> ...]
Relative to the signal's max |value| in A; prints the first instant where |A - B| exceeds 1e-6 of that scale.
Written 2026-11-01 for the Raspberry Pi FMA control (record vs record_fma_gnu11).
"""
import csv
import os
import sys

import numpy as np


def load(path):
    with open(path, newline='') as f:
        r = csv.reader(f)
        head = next(r)
        data = np.array([[float(x) for x in row] for row in r])
    return head, data


def main():
    a_dir, b_dir, runs = sys.argv[1], sys.argv[2], sys.argv[3:]
    for run in runs:
        ha, A = load(os.path.join(a_dir, run + '.csv'))
        hb, B = load(os.path.join(b_dir, run + '.csv'))
        if ha != hb or A.shape != B.shape:
            print('%s: headers or grid differ (%s vs %s)' % (run, A.shape, B.shape))
            continue
        t = A[:, 0]
        print('== %s (%d rows)' % (run, len(t)))
        rows = []
        for j, name in enumerate(ha[1:], start=1):
            d = np.abs(A[:, j] - B[:, j])
            scale = max(np.max(np.abs(A[:, j])), 1e-300)
            k = int(np.argmax(d))
            over = np.nonzero(d > 1e-6 * scale)[0]
            first = '%.6g s' % t[over[0]] if len(over) else '-'
            rows.append((d[k] / scale, name, d[k], t[k], first))
        rows.sort(reverse=True)
        for rel, name, dmax, tk, first in rows[:6]:
            print('  %-28s rel %.3g  abs %.3g at %.6g s  first above 1e-6: %s' % (name, rel, dmax, tk, first))


if __name__ == '__main__':
    main()
