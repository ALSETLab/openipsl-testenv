"""Print the table of runs (Markdown) from the *_metrics.json files of the Dymola verification folder.
(Copy of the Windows round-2 table.py; unchanged.)

Usage: python -I -B table.py <record folder>
"""
import glob
import json
import os
import sys


def fmt(x, nd=3):
    if x is None:
        return 'null'
    if isinstance(x, float) and x.is_integer() and abs(x) >= 1:
        return '%d' % x
    if isinstance(x, float):
        return ('%.' + str(nd) + 'g') % x
    return str(x)


def main():
    out = sys.argv[1]
    rows = []
    order = ['SCRX9__dassl', 'SCRX9__euler', 'SCRX9_vs_SCRX__dassl', 'SCRX__dassl', 'GFL_Fault__euler',
             'GFL_POCFault__euler', 'GFL_FrequencyStep__euler', 'GFL_VoltageStep__euler', 'GFL_PowerRamp__euler',
             'GFL_FaultPSCAD__euler', 'GFM_EMTPFault__euler', 'GFM_EMTPFull__euler', 'EMTPTransformerZeroSeq__euler',
             'SmoothShortFault__euler', 'GFL_PowerRamp__dassl']

    def key(p):
        n = os.path.basename(p)[:-len('_metrics.json')]
        return order.index(n) if n in order else len(order)

    for p in sorted(glob.glob(os.path.join(out, '*_metrics.json')), key=key):
        m = json.load(open(p, encoding='utf-8'))
        e = m['extra']
        name = os.path.basename(p)[:-len('_metrics.json')]
        rows.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            name, m['solver'], fmt(m['step']), fmt(m['stop_time']), m['outcome'], fmt(m['translate_s']),
            fmt(m['compile_s']), fmt(m['simulate_wall_s'], 3), fmt(m['cpu_integration_s']), fmt(m['steps']),
            fmt(m['f_evaluations']), fmt(m['jacobian_evaluations']), fmt(m['time_events']), fmt(m['state_events']),
            fmt(m['result_points']), '%s / %s' % (e['csv'].get('nan_cells'), len(e['csv'].get('missing_signals') or []))))
    print('| run | solver | step (s) | stop (s) | outcome | translate (s) | compile (s) | simulate wall (s) | '
          'CPU integration (s) | steps | f-evals | Jacobians | time events | state events | result points | NaN cells / missing signals |')
    print('|' + '---|' * 16)
    print('\n'.join(rows))


if __name__ == '__main__':
    main()
