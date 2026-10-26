"""Self-comparison of the Dymola-for-Linux runs against the Windows round-2 Dymola record of the same runs.

For every run <Test>__<solver> present in both records:
  - CSV (the data contract): the header and the time grid must be equal; per signal max |Linux - Windows| over the
    whole run and before the run's first disturbance, the time of the maximum, the scale max |Windows| and the
    relative difference, and the first grid time where the two differ by more than 1e-9 relative;
  - metrics: steps, f-evaluations, Jacobians, time and state events, result points, translate/compile/simulate/CPU
    times side by side;
  - raw stored points (when both dsres.mat files are reachable): number of stored points, whether the stored time
    vectors are equal, and per signal max |difference| over the stored points (exact doubles, no resampling).

Usage: python -I -B compare_windows.py --linux <Linux record> --windows <Windows round-2 record> --out <dir>
           [--linux-runs ~/cigre_verify/dymola/runs]
           [--windows-runs <Windows round-2 build tree>/dymola/runs]   (default: $WINDOWS_RAW_ROOT/dymola/runs)
           [--title <heading>] [--name <base name>]
Writes <out>/<name>.json and <out>/logs/<name>.md (default name self_comparison). With --windows and --windows-runs
pointing at a second Linux record it compares two Linux records (used for Evaluate=true against Evaluate=false and
for the repeatability check).
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsres import DsRes  # noqa: E402
from post import SIGNALS  # noqa: E402

RUNS = ['SCRX9__dassl', 'SCRX9__euler', 'SCRX9_vs_SCRX__dassl', 'SCRX__dassl', 'GFL_Fault__euler',
        'GFL_POCFault__euler', 'GFL_FrequencyStep__euler', 'GFL_VoltageStep__euler', 'GFL_PowerRamp__euler',
        'GFL_FaultPSCAD__euler', 'GFM_EMTPFault__euler', 'GFM_EMTPFull__euler', 'EMTPTransformerZeroSeq__euler',
        'SmoothShortFault__euler', 'GFL_PowerRamp__dassl']

# nominal instant of the first disturbance of each test (report/round2_changes.md section 2)
FIRST_EVENT = {'SCRX9': 2.0025, 'SCRX9_vs_SCRX': 2.0025, 'SCRX': 2.0, 'SmoothShortFault': 5.0,
               'EMTPTransformerZeroSeq': float('inf')}
for _t in ('GFL_Fault', 'GFL_POCFault', 'GFL_FrequencyStep', 'GFL_VoltageStep', 'GFL_PowerRamp', 'GFL_FaultPSCAD',
           'GFM_EMTPFault', 'GFM_EMTPFull'):
    FIRST_EVENT[_t] = 2.000005

METRICS = ['steps', 'f_evaluations', 'jacobian_evaluations', 'time_events', 'state_events', 'result_points',
           'translate_s', 'compile_s', 'simulate_wall_s', 'cpu_integration_s', 'outcome']


def load_csv(path):
    with open(path, encoding='utf-8') as f:
        header = f.readline().strip().split(',')
    data = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2)
    return header, data


def csv_compare(lin, win, t_ev):
    hl, dl = load_csv(lin)
    hw, dw = load_csv(win)
    r = {'header_equal': hl == hw, 'rows_linux': int(dl.shape[0]), 'rows_windows': int(dw.shape[0])}
    if hl != hw or dl.shape != dw.shape:
        r['note'] = 'header or shape differs; no comparison'
        return r
    r['grid_max_abs_dt'] = float(np.max(np.abs(dl[:, 0] - dw[:, 0])))
    t = dw[:, 0]
    pre = t < t_ev - 1e-9
    sig = {}
    worst_rel, worst = 0.0, None
    for j, name in enumerate(hl[1:], 1):
        d = np.abs(dl[:, j] - dw[:, j])
        scale = float(np.max(np.abs(dw[:, j])))
        i = int(np.argmax(d))
        tol = 1e-9 * max(scale, 1e-300)
        over = np.flatnonzero(d > tol)
        row = {'max_abs': float(d[i]), 't_of_max': float(t[i]), 'scale_max_abs_windows': scale,
               'rel': float(d[i] / scale) if scale > 0 else (0.0 if d[i] == 0 else float('inf')),
               'max_abs_before_first_event': float(np.max(d[pre])) if pre.any() else None,
               'first_t_rel_diff_over_1e-9': float(t[over[0]]) if over.size else None,
               'identical': bool(np.all(dl[:, j] == dw[:, j]))}
        sig[name] = row
        if row['rel'] >= worst_rel:
            worst_rel, worst = row['rel'], name
    r['signals'] = sig
    r['worst_signal'] = worst
    r['worst_rel'] = worst_rel
    r['all_identical'] = all(v['identical'] for v in sig.values())
    r['identical_before_first_event'] = all((v['max_abs_before_first_event'] or 0.0) == 0.0 for v in sig.values())
    return r


def raw_compare(lin, win, names):
    if not (os.path.isfile(lin) and os.path.isfile(win)):
        return {'note': 'raw result file missing: linux %s, windows %s' % (os.path.isfile(lin), os.path.isfile(win))}
    a, b = DsRes(lin), DsRes(win)
    ta, tb = a.time(), b.time()
    r = {'points_linux': int(a.npoints), 'points_windows': int(b.npoints)}
    if a.npoints != b.npoints:
        n = min(a.npoints, b.npoints)
        k = np.flatnonzero(np.abs(ta[:n] - tb[:n]) > 1e-12)
        r['first_index_time_differs'] = int(k[0]) if k.size else n
        i = r['first_index_time_differs']
        r['times_around_first_difference_linux'] = [float(x) for x in ta[max(0, i - 2):i + 3]]
        r['times_around_first_difference_windows'] = [float(x) for x in tb[max(0, i - 2):i + 3]]
        # stored instants that only one of the two files has (points closer than 1e-9 s merged)
        ua = np.unique(np.round(ta, 9))
        ub = np.unique(np.round(tb, 9))
        r['instants_only_linux'] = [float(x) for x in np.setdiff1d(ua, ub)[:20]]
        r['instants_only_windows'] = [float(x) for x in np.setdiff1d(ub, ua)[:20]]
        # compare at the instants both have, last stored value at each instant
        def last_at(t):
            new = np.ones(len(t), dtype=bool)
            new[1:] = (t[1:] - t[:-1]) > 1e-9
            f = np.flatnonzero(new)
            return np.append(f[1:] - 1, len(t) - 1)
        la, lb = last_at(ta), last_at(tb)
        common, ia, ib = np.intersect1d(np.round(ta[la], 9), np.round(tb[lb], 9), return_indices=True)
        r['common_instants'] = int(common.size)
        sig = {}
        for nme in names:
            if a.has(nme) and b.has(nme):
                d = np.abs(a.values(nme)[la][ia] - b.values(nme)[lb][ib])
                sig[nme] = float(np.max(d)) if d.size else None
        r['max_abs_at_common_instants_post_event'] = sig
        return r
    r['time_max_abs_diff'] = float(np.max(np.abs(ta - tb)))
    sig = {}
    for nme in names:
        if a.has(nme) and b.has(nme):
            d = np.abs(a.values(nme) - b.values(nme))
            i = int(np.argmax(d))
            sig[nme] = {'max_abs': float(d[i]), 't_of_max': float(ta[i]), 'identical': bool(d[i] == 0.0)}
    r['signals'] = sig
    r['all_identical'] = all(v['identical'] for v in sig.values())
    return r


def fmt(x):
    if x is None:
        return 'null'
    if isinstance(x, float):
        if x == 0:
            return '0'
        if x.is_integer() and abs(x) < 1e9:
            return '%d' % x
        return '%.3g' % x
    return str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--linux', required=True)
    ap.add_argument('--windows', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--linux-runs', default=os.path.expanduser('~/cigre_verify/dymola/runs'))
    raw_root = os.environ.get('WINDOWS_RAW_ROOT', '')
    ap.add_argument('--windows-runs', default=os.path.join(raw_root, 'dymola', 'runs') if raw_root else '',
                    help='Windows build tree with <run>/dsres.mat; without it the raw comparison is skipped')
    ap.add_argument('--title', default='Self-comparison: Dymola for Linux against the Windows round-2 Dymola record',
                    help='heading of the Markdown file (the script also compares two Linux records: A = --linux, '
                         'B = --windows)')
    ap.add_argument('--name', default='self_comparison', help='base name of the output files')
    a = ap.parse_args()
    res = {'linux_record': a.linux, 'windows_record': a.windows, 'linux_runs': a.linux_runs,
           'windows_runs': a.windows_runs, 'runs': {}}
    md = ['# ' + a.title, '',
          'CSV: max |Linux - Windows| on the contract grid; "rel" = max |difference| / max |Windows value| of the '
          'signal; "before" = the maximum before the run\'s first disturbance. Raw: the stored doubles of the two '
          'dsres.mat files.', '',
          '| run | CSV identical | worst signal (rel) | max abs (t) | before first disturbance (worst abs) | '
          'first t with rel diff > 1e-9 | raw points L / W | raw identical |',
          '|---|---|---|---|---|---|---|---|']
    mdm = ['', '## Solver statistics and timings, Linux / Windows', '',
           '| run | ' + ' | '.join(METRICS) + ' |', '|---|' + '---|' * len(METRICS)]
    for run in RUNS:
        test = run.split('__')[0]
        lc, wc = os.path.join(a.linux, run + '.csv'), os.path.join(a.windows, run + '.csv')
        if not (os.path.isfile(lc) and os.path.isfile(wc)):
            res['runs'][run] = {'note': 'csv missing: linux %s, windows %s' % (os.path.isfile(lc), os.path.isfile(wc))}
            md.append('| %s | missing | | | | | | |' % run)
            continue
        c = csv_compare(lc, wc, FIRST_EVENT[test])
        ml = json.load(open(os.path.join(a.linux, run + '_metrics.json'), encoding='utf-8'))
        mw = json.load(open(os.path.join(a.windows, run + '_metrics.json'), encoding='utf-8'))
        mt = {k: [ml.get(k), mw.get(k)] for k in METRICS}
        names = SIGNALS[ml['test']]
        rw = raw_compare(os.path.join(a.linux_runs, run, 'dsres.mat'), os.path.join(a.windows_runs, run, 'dsres.mat'),
                         names)
        res['runs'][run] = {'csv': c, 'metrics_linux_windows': mt, 'raw': rw}
        if 'signals' in c:
            w = c['worst_signal']
            s = c['signals'][w]
            pre = max((v['max_abs_before_first_event'] or 0.0) for v in c['signals'].values())
            firsts = [v['first_t_rel_diff_over_1e-9'] for v in c['signals'].values()
                      if v['first_t_rel_diff_over_1e-9'] is not None]
            md.append('| %s | %s | %s (%s) | %s (%s s) | %s | %s | %s / %s | %s |' % (
                run, 'yes' if c['all_identical'] else 'no', w, fmt(s['rel']), fmt(s['max_abs']), fmt(s['t_of_max']),
                fmt(pre), fmt(min(firsts)) if firsts else 'none', rw.get('points_linux'), rw.get('points_windows'),
                rw.get('all_identical', 'n/a (points differ)' if 'points_linux' in rw else rw.get('note'))))
        else:
            md.append('| %s | %s | | | | | | |' % (run, c.get('note')))
        mdm.append('| %s | %s |' % (run, ' | '.join('%s / %s' % (fmt(x), fmt(y)) for x, y in mt.values())))
    md += mdm
    md += ['', '## Per signal (CSV), max |Linux - Windows| / max |Windows|', '']
    for run, r in res['runs'].items():
        c = r.get('csv', {})
        if 'signals' not in c:
            continue
        md.append('- %s: ' % run + '; '.join('%s %s (%s)' % (n, fmt(v['max_abs']), fmt(v['rel']))
                                           for n, v in c['signals'].items()))
    os.makedirs(os.path.join(a.out, 'logs'), exist_ok=True)
    with open(os.path.join(a.out, a.name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(a.out, 'logs', a.name + '.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print('\n'.join(md))
    return 0


if __name__ == '__main__':
    sys.exit(main())
