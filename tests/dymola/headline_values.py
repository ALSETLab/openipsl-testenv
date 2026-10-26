"""Headline values of the Windows round-2 Dymola record, recomputed from the Linux CSVs and the Windows CSVs side by
side (the numbers the Windows README section 8 quotes), so a reader sees that the Linux record reproduces them.

Usage: python -I -B headline_values.py --linux <Linux record> --windows <Windows round-2 record> [--out <file.json>]
"""
import argparse
import json
import os

import numpy as np


def load(path):
    with open(path, encoding='utf-8') as f:
        h = f.readline().strip().split(',')
    d = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2)
    return {n: d[:, i] for i, n in enumerate(h)}


def mean(c, sig, t0, t1):
    t = c['time']
    k = (t >= t0 - 1e-12) & (t < t1 - 1e-12)
    return float(np.mean(c[sig][k]))


def at(c, sig, t):
    return float(c[sig][int(np.argmin(np.abs(c['time'] - t)))])


ITEMS = [
    ('SCRX9__dassl', 'EFD(0) [pu]', lambda c: at(c, 'sCRX9.EFD', 0.0)),
    ('SCRX9__dassl', 'EFD(2.005 s) [pu]', lambda c: at(c, 'sCRX9.EFD', 2.005)),
    ('SCRX9__dassl', 'EFD(10 s) [pu]', lambda c: at(c, 'sCRX9.EFD', 10.0)),
    ('SCRX9__euler', 'EFD(10 s) [pu]', lambda c: at(c, 'sCRX9.EFD', 10.0)),
    ('SCRX9_vs_SCRX__dassl', 'max |dll - native EFD| before 2.0025 s [pu]',
     lambda c: float(np.max(np.abs((c['dll.sCRX9.EFD'] - c['native.sCRX.EFD'])[c['time'] < 2.0025])))),
    ('SCRX9_vs_SCRX__dassl', 'dll - native EFD at 10 s [pu]',
     lambda c: at(c, 'dll.sCRX9.EFD', 10.0) - at(c, 'native.sCRX.EFD', 10.0)),
    ('SCRX__dassl', 'EFD(10 s) [pu]', lambda c: at(c, 'sCRX.EFD', 10.0)),
    ('GFL_Fault__euler', 'P mean [5.7, 5.8) s [MW]', lambda c: mean(c, 'gFM_GFL_IBR.out[11]', 5.7, 5.8)),
    ('GFL_Fault__euler', 'Q mean [5.7, 5.8) s [Mvar]', lambda c: mean(c, 'gFM_GFL_IBR.out[12]', 5.7, 5.8)),
    ('GFL_Fault__euler', 'f at 5.8 s [Hz]', lambda c: at(c, 'gFM_GFL_IBR.out[10]', 5.8)),
    ('GFL_FaultPSCAD__euler', 'P mean [4.5, 5.0) s [MW]', lambda c: mean(c, 'gFM_GFL_IBR.out[11]', 4.5, 5.0)),
    ('GFL_FaultPSCAD__euler', 'Q mean [4.5, 5.0) s [Mvar]', lambda c: mean(c, 'gFM_GFL_IBR.out[12]', 4.5, 5.0)),
    ('GFL_FaultPSCAD__euler', 'Q at 5.8 s [Mvar]', lambda c: at(c, 'gFM_GFL_IBR.out[12]', 5.8)),
    ('GFL_FaultPSCAD__euler', 'Vd = out[8] mean [4.5, 5.0) s [pu]', lambda c: mean(c, 'gFM_GFL_IBR.out[8]', 4.5, 5.0)),
    ('GFL_FrequencyStep__euler', 'f at 3 s [Hz]', lambda c: at(c, 'gFM_GFL_IBR.out[10]', 3.0)),
    ('GFL_VoltageStep__euler', 'Q at 3 s [Mvar]', lambda c: at(c, 'gFM_GFL_IBR.out[12]', 3.0)),
    ('GFM_EMTPFault__euler', 'max |grid_sensor_c.current| in CSV [A]',
     lambda c: float(np.max(np.abs(c['gFM_GFL_IBR.grid_sensor_c.current'])))),
    ('GFL_PowerRamp__dassl', 'P at 3.6 s [MW]', lambda c: at(c, 'gFM_GFL_IBR.out[11]', 3.6)),
    ('SmoothShortFault__euler', 'max |currentSensor.i| [A]', lambda c: float(np.max(np.abs(c['smoothShortFault.currentSensor.i'])))),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--linux', required=True)
    ap.add_argument('--windows', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    cache, rows = {}, []
    print('| run | value | Linux | Windows round 2 | Linux - Windows |')
    print('|---|---|---|---|---|')
    for run, label, fn in ITEMS:
        for side, d in (('L', a.linux), ('W', a.windows)):
            if (side, run) not in cache:
                cache[(side, run)] = load(os.path.join(d, run + '.csv'))
        vl, vw = fn(cache[('L', run)]), fn(cache[('W', run)])
        rows.append({'run': run, 'value': label, 'linux': vl, 'windows': vw, 'difference': vl - vw})
        print('| %s | %s | %.10g | %.10g | %.3g |' % (run, label, vl, vw, vl - vw))
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(rows, f, indent=1)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
