#!/usr/bin/env python3
"""compare_arm.py - the ARM macOS (Apple Silicon) runs of the IEEE/CIGRE DLL verification against the x64 records:
Windows round 2 (report/verification_round2/<tool>/) and Linux x86_64 (report/linux/<tool>/), the same tool and run,
the way report/linux/compare_linux.py compares Linux with Windows. The statistics functions are IMPORTED from
compare_linux.py (lw_compare, metric_deltas, cross_tool, settled_values, steady_start, dll_vs_native,
scrx9_vs_native_test, csv_digits, read_csv, worst, g, md_table, RUNS, ORDER), so the definitions are identical:
  - per signal, on the common contract CSV grid: max |ARM - x64|, RMS, the time of the max, over all grid points
    ("all") and with the grid points within one DLL sample Ts of a disturbance instant excluded ("excl"); relative
    to Sbase for P and Q, 60 Hz for f, 1 pu for speed and the x64 signal's range otherwise; the CSV print floor
    (two units of the last printed digit at the instant of the max) marks differences the CSVs cannot resolve;
  - the counters (steps, f_evaluations, jacobian_evaluations, time_events, state_events, result_points) exactly, the
    wall times as ARM/x64 ratios;
  - settled values (GFM: mean of P, Q, f over the last 0.1 s, current and voltage peaks over the last 0.05 s; SCRX:
    final values), ARM against each x64 platform with the same scale rules (flag above 1e-3);
  - SCRX9 DLL against master's native SCRX on ARM (steady start, DLL minus native, test against test);
  - cross-tool on ARM (OpenModelica against System Modeler) when both ARM records exist, beside the Windows and Linux
    cross-tool numbers of the same pair read from their comparison JSONs.
In the output, "linux" keys produced by the imported functions mean "ARM" (the first argument) and "windows" keys the
x64 side named in the block.

    python3 -I compare_arm.py --sm <ARM System Modeler record> [--om <ARM OpenModelica record>] [--sm-lookup <dir>]
                             --win <report/verification_round2> --linux <report/linux> --out <dir> [--no-figs]
Outputs: comparison_arm.json, comparison_arm_tables.md, figs/*.png.
Written 2026-10-31 for the ARM macOS verification (Claude Fable 5.1).
"""
import argparse
import datetime
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'records', 'report', 'linux'))
import compare_linux as CL  # noqa: E402

TOOLS = ['systemmodeler', 'openmodelica']
X64 = ['windows', 'linux']
LABEL = {'windows': 'Windows round 2 (x64)', 'linux': 'Linux x86_64 (WSL2)', 'arm': 'macOS arm64 (Apple M2 Pro)'}


def load_json(p):
    try:
        with open(p, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def metrics_path(root, key):
    return os.path.join(root, key + '_metrics.json')


def frame(root, key):
    p = os.path.join(root, key + '.csv')
    return (CL.read_csv(p), p) if os.path.exists(p) else (None, p)


def settled_vs(key, sa, sb):
    """ARM settled values against one x64 platform's, the scale rules of compare_linux.settled_compare."""
    r = CL.RUNS[key]
    out, flags = {}, []
    for c, va in sa.items():
        if c not in sb:
            continue
        for fld, x in va.items():
            y = sb[c][fld]
            if c in (CL.P_, CL.Q_):
                scale = r['Sbase']
            elif c == CL.F_:
                scale = 60.0
            elif c.endswith('gENROU.w'):
                scale = 1.0
            else:
                scale = max(abs(x), abs(y)) or None
            d = abs(x - y)
            rr = d / scale if scale else None
            out['%s|%s' % (c, fld)] = {'arm': x, 'x64': y, 'abs': d, 'scale': scale, 'rel': rr}
            if rr is not None and rr > CL.SETTLED_REL and not c.endswith('VabcSum.y'):
                flags.append({'run': key, 'signal': c, 'field': fld, 'rel': rr, 'abs': d})
    return out, flags


def perf(m, tool):
    if m is None or m.get('outcome') != 'ok':
        return None
    if tool == 'openmodelica' and m.get('nostats_simulate_wall_s') is not None:
        return CL.fnum(m.get('nostats_simulate_wall_s'))
    return CL.fnum(m.get('simulate_wall_s'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sm', required=True)
    ap.add_argument('--om', default=None)
    ap.add_argument('--sm-lookup', default=None, help='folder with one sub-folder per library layout (SCRX9__euler)')
    ap.add_argument('--win', required=True)
    ap.add_argument('--linux', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--om-raw', default=None, help='OpenModelica build tree with <run>/<run>_res.mat: the cross-tool block then uses the OpenModelica series rebuilt from the raw result with the round-2 instant rule (compare_linux.rebuild_from_raw), as the x64 cross-tool numbers were')
    ap.add_argument('--no-figs', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    arm = {'systemmodeler': a.sm, 'openmodelica': a.om}
    x64 = {'windows': a.win, 'linux': a.linux}
    J = {'meta': {'created': datetime.datetime.now().isoformat(timespec='seconds'), 'script': 'scripts/compare_arm.py',
                  'functions_from': os.path.relpath(CL.__file__, os.path.dirname(HERE)),
                  'python': sys.version.split()[0], 'numpy': np.__version__,
                  'arm_records': {t: os.path.relpath(p, os.path.dirname(HERE)) for t, p in arm.items() if p},
                  'x64_records': {p: os.path.relpath(x64[p], os.path.dirname(HERE)) for p in X64},
                  'notes': ['Differences are ARM minus x64; keys named "linux" inside linux_vs_* blocks are the ARM '
                            'side, "windows" the x64 side (the imported functions name their arguments so).',
                            '"excl" drops the grid points within one DLL sample (Ts) of a disturbance instant.',
                            'Relative numbers: Sbase for P and Q, 60 Hz for f, 1 pu for speed, the x64 signal range '
                            'otherwise.',
                            'System Modeler on Windows and Linux failed to build SCRX9_vs_SCRX and SCRX (master\'s '
                            'native SCRX); where ARM succeeds, those two ARM runs are compared with the x64 diagnostic '
                            'runs made with the separate fix b48d49e8 (systemmodeler_diag).']},
         'tools': {}, 'runs': {}, 'summary': {}, 'flags': []}
    for tool in TOOLS:
        if not arm[tool]:
            continue
        mA = load_json(metrics_path(arm[tool], 'GFL_Fault__euler')) or load_json(metrics_path(arm[tool], 'SCRX9__euler')) or {}
        J['tools'][tool] = {'arm': {f: mA.get(f) for f in ('tool_version', 'msl_version', 'compiler', 'platform')}}
        for p in X64:
            mX = load_json(metrics_path(os.path.join(x64[p], tool), 'GFL_Fault__euler')) or {}
            J['tools'][tool][p] = {f: mX.get(f) for f in ('tool_version', 'msl_version', 'compiler', 'platform')}
    for key in CL.ORDER:
        r = CL.RUNS[key]
        R = {'test': r['test'], 'solver': r['solver'], 'family': r['family'], 'Ts': r['Ts'], 'grid': r['grid'],
             'stop': r['stop'], 'events': [[e, n] for e, n in r['events']], 'outcome': {}, 'metrics_delta': {},
             'arm_vs_x64': {}, 'csv_digits': {}, 'settled': {}, 'settled_vs_x64': {}}
        dataA = {}
        for tool in TOOLS:
            if not arm[tool]:
                continue
            mA = load_json(metrics_path(arm[tool], key))
            A, pA = frame(arm[tool], key)
            R['outcome'].setdefault(tool, {})['arm'] = mA and mA.get('outcome')
            if mA and tool == 'systemmodeler':
                R.setdefault('sm_arm_facts', {})
                R['sm_arm_facts'] = {'library_folder_used': mA.get('wsm_library_folder_used'),
                                     'sample_time_parameters': mA.get('wsm_sample_time_parameters'),
                                     'evaluator_link_failures': mA.get('wsm_evaluator_link_failures'),
                                     'dll_status_max_abs': mA.get('wsm_dll_status_max_abs'),
                                     'tool_messages_total': mA.get('wsm_tool_messages_total'),
                                     'first_messages': (mA.get('tool_messages') or [])[:3]}
            if A is not None:
                dataA[tool] = A
                R['csv_digits'].setdefault(tool, {})['arm'] = CL.csv_digits(pA)
                R['settled'][tool] = CL.settled_values(key, A)
            for p in X64:
                diag = False
                mX = load_json(metrics_path(os.path.join(x64[p], tool), key))
                X, pX = frame(os.path.join(x64[p], tool), key)
                if X is None and tool == 'systemmodeler' and key in CL.SM_DIAG:
                    X, pX = frame(os.path.join(x64[p], CL.SM_DIAG_DIR), key)
                    mX = load_json(metrics_path(os.path.join(x64[p], CL.SM_DIAG_DIR), key)) or mX
                    diag = X is not None
                R['outcome'][tool][p] = (mX and mX.get('outcome')) and ((mX.get('outcome') + ' (diagnostic run with b48d49e8)') if diag else mX.get('outcome'))
                R['metrics_delta'].setdefault(tool, {})[p] = CL.metric_deltas(mA, mX)
                if X is not None:
                    R['csv_digits'].setdefault(tool, {})[p] = CL.csv_digits(pX)
                if A is not None and X is not None:
                    dig = min(R['csv_digits'][tool]['arm'], R['csv_digits'][tool][p])
                    blk = CL.lw_compare(key, A, X, dig)
                    blk['x64_platform'] = p
                    blk['x64_is_diagnostic_b48d49e8'] = diag
                    R['arm_vs_x64'].setdefault(tool, {})[p] = blk
                    sv, fl = settled_vs(key, R['settled'][tool], CL.settled_values(key, X))
                    R['settled_vs_x64'].setdefault(tool, {})[p] = sv
                    for f in fl:
                        f.update(tool=tool, x64=p)
                    J['flags'] += fl
        # SCRX blocks on ARM
        if r['family'] == 'scrx':
            R['steady_start'] = {t: CL.steady_start(d, 'sCRX9.EFD', 'gENROU.w', 'GEN1.v') for t, d in dataA.items()}
        if r['family'] == 'scrx_native':
            R['steady_start'] = {t: CL.steady_start(d, 'sCRX.EFD', 'gENROU.w', 'GEN1.v') for t, d in dataA.items()}
        if r['family'] == 'scrx_pair':
            R['dll_vs_native'] = {t: CL.dll_vs_native(d) for t, d in dataA.items()}
        # cross-tool on ARM
        if len(dataA) == 2:
            dig = {t: (R['csv_digits'].get(t) or {}).get('arm') for t in TOOLS}
            dig['dymola'] = None
            dct = dict(dataA)
            R['cross_tool_om_series'] = 'OpenModelica CSV as recorded (%s digits)' % dig['openmodelica']
            if a.om_raw:
                rawp = os.path.join(a.om_raw, key, key + '_res.mat')
                if os.path.exists(rawp):
                    dct['openmodelica'] = CL.rebuild_from_raw(rawp, dataA['openmodelica'])
                    dig['openmodelica'] = None
                    R['cross_tool_om_series'] = 'OpenModelica rebuilt from %s at full precision (round-2 instant rule)' % os.path.relpath(rawp, os.path.dirname(HERE))
            R['cross_tool_arm'] = CL.cross_tool(key, {'dymola': None, **dct}, dig).get('openmodelica-systemmodeler')
            R['cross_tool_arm_worst'] = {v: CL.worst_rel(R['cross_tool_arm'], key, v) for v in ('all', 'excl')}
            JW = load_json(os.path.join(a.win, 'comparison.json')) or {}
            JL = load_json(os.path.join(a.linux, 'comparison_linux.json')) or {}
            R['cross_tool_x64_worst'] = {
                'windows': {v: CL.worst_rel(((JW.get('runs') or {}).get(key) or {}).get('cross_tool', {}).get('openmodelica-systemmodeler'), key, v) for v in ('all', 'excl')},
                'linux': {v: CL.worst_rel(((JL.get('runs') or {}).get(key) or {}).get('cross_tool', {}).get('openmodelica-systemmodeler'), key, v) for v in ('all', 'excl')}}
        J['runs'][key] = R
    # SCRX9 test against the native test, per tool on ARM
    for tool in TOOLS:
        if not arm[tool]:
            continue
        A, _ = frame(arm[tool], 'SCRX9__dassl')
        B, _ = frame(arm[tool], 'SCRX__dassl')
        if A is not None and B is not None:
            J['runs']['SCRX9__dassl'].setdefault('scrx9_test_vs_native_test', {})[tool] = CL.scrx9_vs_native_test(A, B)
    # lookup experiment
    if a.sm_lookup and os.path.isdir(a.sm_lookup):
        L = {}
        for v in sorted(os.listdir(a.sm_lookup)):
            m = load_json(os.path.join(a.sm_lookup, v, 'SCRX9__euler_metrics.json'))
            if m:
                L[v] = {'folders_present': list((m.get('wsm_library_folders_present') or {}).keys()),
                        'outcome': m.get('outcome'), 'folder_used': m.get('wsm_library_folder_used'),
                        'evaluator_link_failures': m.get('wsm_evaluator_link_failures'),
                        'sim_external_libraries': m.get('wsm_sim_external_libraries'),
                        'first_failure': next((x for x in (m.get('tool_messages') or []) if x.startswith('FAILED')), None)}
        J['sm_folder_lookup'] = L
    # summary
    S = {'arm_vs_x64': {}, 'counts': {}, 'performance': {}}
    for tool in TOOLS:
        if not arm[tool]:
            continue
        for p in X64:
            cands = []
            for key in CL.ORDER:
                x = (J['runs'][key]['arm_vs_x64'].get(tool) or {}).get(p)
                if x and x['worst_all']:
                    cands.append(dict(x['worst_all'], run=key))
            cands.sort(key=lambda c: -c['rel_max'])
            S['arm_vs_x64'].setdefault(tool, {})[p] = {'worst': cands[0] if cands else None,
                                                       'runs_compared': len(cands),
                                                       'all': [{'run': c['run'], 'signal': c['signal'], 'rel_max': c['rel_max'], 'max_abs': c['max_abs'], 't_max': c['t_max'], 'at_floor': c.get('at_floor')} for c in cands]}
            eq = tot = 0
            diffs = []
            for key in CL.ORDER:
                md = (J['runs'][key]['metrics_delta'].get(tool) or {}).get(p)
                if not md:
                    continue
                for f in CL.COUNT_FIELDS:
                    if md[f]['equal'] is not None:
                        tot += 1
                        eq += int(md[f]['equal'])
                        if not md[f]['equal']:
                            diffs.append({'run': key, 'field': f, 'arm': md[f]['linux'], 'x64': md[f]['windows']})
            S['counts'].setdefault(tool, {})[p] = {'equal': eq, 'total': tot, 'differences': diffs}
            rat = {'simulate': [], 'translate': [], 'compile': []}
            per = {}
            for key in CL.ORDER:
                mA = load_json(metrics_path(arm[tool], key))
                root = os.path.join(x64[p], tool)
                mX = load_json(metrics_path(root, key))
                if mX is None or mX.get('outcome') != 'ok':
                    mX2 = load_json(metrics_path(os.path.join(x64[p], CL.SM_DIAG_DIR), key)) if tool == 'systemmodeler' else None
                    mX = mX2 or mX
                sA, sX = perf(mA, tool), perf(mX, tool)
                e = {'simulate_arm_s': sA, 'simulate_x64_s': sX, 'simulate_ratio': (sA / sX) if (sA and sX) else None}
                for f, n in (('translate_s', 'translate'), ('compile_s', 'compile')):
                    va, vx = CL.fnum((mA or {}).get(f)), CL.fnum((mX or {}).get(f))
                    e[n + '_arm_s'], e[n + '_x64_s'] = va, vx
                    e[n + '_ratio'] = (va / vx) if (va and vx) else None
                    if e[n + '_ratio'] is not None:
                        rat[n].append(e[n + '_ratio'])
                if e['simulate_ratio'] is not None:
                    rat['simulate'].append(e['simulate_ratio'])
                per[key] = e
            S['performance'].setdefault(tool, {})[p] = {
                'per_run': per,
                'ranges': {k: ({'min': min(v), 'median': float(np.median(v)), 'max': max(v), 'n': len(v)} if v else None)
                           for k, v in rat.items()}}
    J['summary'] = S
    with open(os.path.join(a.out, 'comparison_arm.json'), 'w', encoding='utf-8') as fh:
        json.dump(CL.to_jsonable(J), fh, indent=1)
    tables(J, a)
    if not a.no_figs:
        figures(J, arm, x64, a.out)
    print('written', os.path.join(a.out, 'comparison_arm.json'))


def tables(J, a):
    g, md = CL.g, CL.md_table
    out = ['# ARM macOS against the x64 records: tables (generated by scripts/compare_arm.py, %s)\n' % J['meta']['created']]
    if 'sm_folder_lookup' in J:
        out.append('## System Modeler: which Resources/Library folder is used (SCRX9__euler per package layout)\n')
        rows = []
        for v, L in J['sm_folder_lookup'].items():
            rows.append([v, ', '.join(L['folders_present']), L['outcome'], ', '.join(L['folder_used'] or []) or '-',
                         L['evaluator_link_failures'], (L['first_failure'] or '-').split('\n')[0][:60]])
        out.append(md(['package layout', 'folders present', 'build + run', 'folder in the .sim', 'evaluator link failures', 'first failure'], rows))
    for tool in TOOLS:
        if tool not in J['tools']:
            continue
        out.append('## %s: outcome and counters, ARM against Windows and Linux\n' % CL.SHORT[tool])
        rows = []
        for key in CL.ORDER:
            R = J['runs'][key]
            oc = R['outcome'].get(tool) or {}
            cells = [key, oc.get('arm'), oc.get('windows'), oc.get('linux')]
            for p in X64:
                md_ = (R['metrics_delta'].get(tool) or {}).get(p)
                if md_:
                    ne = [f for f in CL.COUNT_FIELDS if md_[f]['equal'] is False]
                    neq = sum(1 for f in CL.COUNT_FIELDS if md_[f]['equal'] is not None)
                    cells.append('%d/%d equal%s' % (neq - len(ne), neq, (' (' + ', '.join('%s %s/%s' % (f, g(md_[f]['linux']), g(md_[f]['windows'])) for f in ne) + ')') if ne else ''))
                else:
                    cells.append('-')
            rows.append(cells)
        out.append(md(['run', 'ARM', 'Windows', 'Linux', 'counters ARM = Windows', 'counters ARM = Linux'], rows))
        out.append('## %s: largest difference per run, ARM against each x64 platform (contract CSV grid)\n' % CL.SHORT[tool])
        rows = []
        for key in CL.ORDER:
            R = J['runs'][key]
            cells = [key]
            for p in X64:
                b = (R['arm_vs_x64'].get(tool) or {}).get(p)
                if not b or not b['worst_all']:
                    cells += ['-', '-']
                    continue
                w, we = b['worst_all'], b['worst_excl']
                cells.append('%s: %s rel, %s abs at %s s%s%s' % (CL.short(w['signal']), g(w['rel_max'], '%.2g'), g(w['max_abs'], '%.2g'), g(w['t_max'], '%.5g'),
                                                                   ' (CSV floor)' if w.get('at_floor') else '', ' [x64 = diag b48d49e8]' if b.get('x64_is_diagnostic_b48d49e8') else ''))
                cells.append('%s rel' % g(we['rel_max'], '%.2g') if we else '-')
            rows.append(cells)
        out.append(md(['run', 'vs Windows: worst signal (all points)', 'vs Windows: excl', 'vs Linux: worst signal (all points)', 'vs Linux: excl'], rows))
        out.append('## %s: wall times, ARM against each x64 platform\n' % CL.SHORT[tool])
        rows = []
        for key in CL.ORDER:
            cells = [key]
            for p in X64:
                e = ((J['summary']['performance'].get(tool) or {}).get(p) or {}).get('per_run', {}).get(key)
                if not e:
                    cells += ['-'] * 3
                    continue
                cells += ['%s / %s = %s' % (g(e['translate_arm_s'], '%.1f'), g(e['translate_x64_s'], '%.1f'), g(e['translate_ratio'], '%.2f')),
                          '%s / %s = %s' % (g(e['compile_arm_s'], '%.1f'), g(e['compile_x64_s'], '%.1f'), g(e['compile_ratio'], '%.2f')),
                          '%s / %s = %s' % (g(e['simulate_arm_s'], '%.2f'), g(e['simulate_x64_s'], '%.2f'), g(e['simulate_ratio'], '%.2f'))]
            rows.append(cells)
        out.append(md(['run', 'translate ARM/Win (s)', 'compile ARM/Win (s)', 'simulate ARM/Win (s)', 'translate ARM/Linux (s)', 'compile ARM/Linux (s)', 'simulate ARM/Linux (s)'], rows))
        out.append('## %s: settled values on ARM and the largest relative change against each x64 platform\n' % CL.SHORT[tool])
        rows = []
        for key in CL.ORDER:
            R = J['runs'][key]
            sv = R['settled'].get(tool)
            if not sv:
                continue
            for c, flds in sv.items():
                for fld, x in flds.items():
                    cells = [key, CL.short(c), fld, g(x, '%.10g')]
                    for p in X64:
                        e = ((R['settled_vs_x64'].get(tool) or {}).get(p) or {}).get('%s|%s' % (c, fld))
                        cells.append('%s (rel %s)' % (g(e['x64'], '%.10g'), g(e['rel'], '%.1e')) if e else '-')
                    rows.append(cells)
        out.append(md(['run', 'signal', 'quantity', 'ARM', 'Windows (rel diff)', 'Linux (rel diff)'], rows))
    # SCRX blocks
    rows = []
    for key in ('SCRX9__dassl', 'SCRX9__euler', 'SCRX__dassl'):
        for t, s in (J['runs'][key].get('steady_start') or {}).items():
            rows.append([key, CL.SHORT[t], g(s['EFD0'], '%.8g'), g(s['max_abs_EFD_minus_EFD0_t_lt_2s'], '%.2g'), g(s['max_abs_w_t_lt_2s'], '%.2g'), g(s.get('V_range_t_lt_2s'), '%.2g')])
    if rows:
        out.append('## Steady start before the fault on ARM (t < 2 s)\n')
        out.append(md(['run', 'tool', 'EFD(0)', 'max |EFD - EFD(0)|', 'max |w|', 'GEN1.v range'], rows))
    rows = []
    for t, d in (J['runs']['SCRX9_vs_SCRX__dassl'].get('dll_vs_native') or {}).items():
        for name, s in d.items():
            rows.append([CL.SHORT[t], name, g(s['before_fault']['max_abs'], '%.3g'), g(s['after_fault_sample_instants']['max_abs'], '%.3g'), g(s['t_ge_2p3s_sample_instants']['max_abs'], '%.3g'), g(s['at_10s'], '%.3g')])
    if rows:
        out.append('## SCRX9_vs_SCRX on ARM: DLL minus native\n')
        out.append(md(['tool', 'signal', 'before fault', 'after fault, 5 ms samples', 't >= 2.3 s, samples', 'at 10 s'], rows))
    rows = []
    for key in CL.ORDER:
        R = J['runs'][key]
        if 'cross_tool_arm_worst' in R:
            w = R['cross_tool_arm_worst']['all']
            ww = (R.get('cross_tool_x64_worst') or {}).get('windows', {}).get('all')
            wl = (R.get('cross_tool_x64_worst') or {}).get('linux', {}).get('all')
            rows.append([key, '%s: %s' % (CL.short(w['signal']), g(w['rel_max'], '%.3g')) if w else '-',
                         g(ww and ww['rel_max'], '%.3g'), g(wl and wl['rel_max'], '%.3g')])
    if rows:
        out.append('## Cross-tool on ARM, OpenModelica minus System Modeler (worst relative, key signals), beside the x64 numbers\n')
        out.append(md(['run', 'ARM', 'Windows round 2', 'Linux x64'], rows))
    with open(os.path.join(a.out, 'comparison_arm_tables.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))


def figures(J, arm, x64, outdir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fd = os.path.join(outdir, 'figs')
    os.makedirs(fd, exist_ok=True)
    picks = [('SCRX9__dassl', 'sCRX9.EFD', 'EFD (pu)'), ('GFL_Fault__euler', CL.P_, 'P (MW)'),
             ('GFL_Fault__euler', 'gFM_GFL_IBR.out[6]', 'out[6] Iqref (pu)'), ('GFM_EMTPFull__euler', CL.F_, 'f (Hz)')]
    for tool in TOOLS:
        if not arm[tool]:
            continue
        for key, sig, lab in picks:
            A, _ = frame(arm[tool], key)
            W, _ = frame(os.path.join(x64['windows'], tool), key)
            L, _ = frame(os.path.join(x64['linux'], tool), key)
            if A is None or sig not in A:
                continue
            fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
            ax[0].plot(A['time'], A[sig], color='#2a78d6', lw=1.0, label='ARM macOS')
            if W is not None and sig in W:
                ax[0].plot(W['time'], W[sig], color='#8a8984', lw=0.8, ls='--', label='Windows x64')
                t, (ia, iw) = CL.align([A, W], CL.RUNS[key]['grid'])
                ax[1].plot(t, A[sig][ia] - W[sig][iw], color='#8a8984', lw=0.8, label='ARM - Windows')
            if L is not None and sig in L:
                t, (ia, il) = CL.align([A, L], CL.RUNS[key]['grid'])
                ax[1].plot(t, A[sig][ia] - L[sig][il], color='#eb6834', lw=0.8, label='ARM - Linux x64')
            ax[0].set_ylabel(lab)
            ax[0].set_title('%s, %s: %s' % (CL.SHORT[tool], key, sig))
            ax[1].set_ylabel('difference')
            ax[1].set_xlabel('time (s)')
            for x in ax:
                x.grid(True, color='#d9d8d4', lw=0.5)
                x.legend(loc='best', fontsize=8)
            fig.tight_layout()
            fig.savefig(os.path.join(fd, '%s_%s_%s.png' % (tool, key, sig.replace('.', '_').replace('[', '').replace(']', ''))), dpi=150)
            plt.close(fig)


if __name__ == '__main__':
    main()
