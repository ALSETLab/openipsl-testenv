"""Turn one Dymola-for-Linux run folder (run.json + logs + dsres.mat) into the data-contract files of the verification.

Linux port of report/verification_round2/dymola/scripts/post.py (Windows round 2). The CSV signals, the grid, the
resampling and the metric fields are the same; what changed:
  - the metrics carry 'platform' and 'compiler' (the compiler that really built dymosim: the .comment section of
    the executable, and what `cc` resolves to; dsbuild.sh calls `cc`);
  - compile_s is the C build time measured from the files (dymosim mtime minus dsmodel.c mtime), because Dymola for
    Linux reports "Compilation time: 0.001 s" in its translation log (it does not time the gcc build there); the
    figure Dymola reports is kept as extra.dymola_reported_compilation_time_s;
  - msl_version is read from the run (loadResource of modelica://Modelica/package.mo);
  - the message parser also knows gcc and GNU ld messages ("file:line: warning: ...", "/usr/bin/ld: ...: in
    function ..." followed by its warning line).

For run <Test>__<solver> it writes, in --out:
  <Test>__<solver>_metrics.json   the contract fields, plus 'extra' with Dymola-specific detail
  <Test>__<solver>.csv            time + the contract signals, on the common grid
  <Test>__<solver>_raw_points.txt number of points stored in dsres.mat (and of distinct time instants)
and copies the run's logs to --out/logs/<Test>__<solver>/.

Resampling (unchanged from Windows): points closer than 1e-9 s are one instant. A grid point that falls on an
instant takes the LAST stored value there (the value right after the events at that instant); a grid point between
two instants is interpolated linearly from the post-event value of the earlier instant to the pre-event value of the
later one.

Usage: python -I -B post.py --run <run folder> --name <Test>__<solver> --out <record folder> --grid <dt> --stop <s>
       python -I -B post.py --selftest <dsres.mat>
The recipe recorded in the metrics is the first line of <run folder>/driver.out (written by run_all.sh).
"""
import argparse
import json
import os
import re
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsres import DsRes, check_reader  # noqa: E402

PLATFORM = 'linux64, Ubuntu 24.04.5, glibc 2.39'

GFM_SIGNALS = (['gFM_GFL_IBR.out[%d]' % i for i in range(1, 13)]
               + ['gFM_GFL_IBR.P_ref_pu', 'gFM_GFL_IBR.Q_ref_pu', 'gFM_GFL_IBR.V_ref_pu']
               + ['gFM_GFL_IBR.grid_sensor_%s.voltage' % p for p in 'abc']
               + ['gFM_GFL_IBR.grid_sensor_%s.current' % p for p in 'abc'])

SIGNALS = {
    'OpenIPSL.Tests.Controls.IEEE_CIGRE.SCRX9.SCRX9':
        ['sCRX9.EFD', 'gENROU.EFD', 'gENROU.w', 'gENROU.ETERM', 'GEN1.v', 'gENROU.PELEC'],
    'OpenIPSL.Tests.Controls.IEEE_CIGRE.SCRX9.SCRX9_vs_SCRX':
        ['dll.sCRX9.EFD', 'native.sCRX.EFD', 'dll.gENROU.w', 'native.gENROU.w',
         'dll.gENROU.ETERM', 'native.gENROU.ETERM', 'dll.GEN1.v', 'native.GEN1.v'],
    'OpenIPSL.Tests.Controls.PSSE.ES.SCRX':
        ['sCRX.EFD', 'gENROU.EFD', 'gENROU.w', 'gENROU.ETERM', 'GEN1.v', 'gENROU.PELEC'],
    'OpenIPSL.Tests.Controls.IEEE_CIGRE.GFM.Components.SmoothShortFault':
        ['smoothShortFault.A.v', 'smoothShortFault.B.v', 'smoothShortFault.C.v',
         'smoothShortFault.currentSensor2.i', 'smoothShortFault.currentSensor1.i', 'smoothShortFault.currentSensor.i'],
    'OpenIPSL.Tests.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformerZeroSeq':
        ['transformer.Ad.v', 'transformer.Bd.v', 'transformer.Cd.v',
         'transformer.Ad.i', 'transformer.Bd.i', 'transformer.Cd.i',
         'transformer.VSecABLL.v', 'transformer.VSecBCLL1.v',
         'transformer.VSecABLL1.v', 'transformer.VabcSum.y',
         'transformer.Bcurrent.i'],
}
for _t in ('GFL_Fault', 'GFL_POCFault', 'GFL_FrequencyStep', 'GFL_VoltageStep', 'GFL_PowerRamp', 'GFL_FaultPSCAD',
           'GFM_EMTPFault', 'GFM_EMTPFull'):
    SIGNALS['OpenIPSL.Tests.Controls.IEEE_CIGRE.GFM.' + _t] = GFM_SIGNALS

MSG_START = re.compile(r'^\s*(Warning|WARNING|Error|ERROR|error|Some 32-bit libraries|.*warning C\d+|.*error C\d+'
                       r'|.*: (warning|error|fatal error):|/usr/bin/ld: .*|collect2: .*)')


def strip_html(s):
    return re.sub(r'<[^>]+>', '', s)


def message_blocks(text, source):
    """Warnings and errors of a log as blocks: a line that starts one, plus its indented continuation lines.
    A GNU ld line ".../ld: <object>: in function `f':" and the warning line after it are one block."""
    out, cur = [], None
    for raw in strip_html(text).splitlines():
        line = raw.rstrip()
        if cur is not None and cur[0].startswith('Some 32-bit'):
            if line.strip():
                cur.append(line.strip())
            if line.strip().startswith('If this is not desired') or not line.strip():
                out.append(cur)
                cur = None
            continue
        if cur is not None and line.startswith('Dymola has selected default initial conditions'):
            cur.append(line.strip())
            continue
        if cur is not None and len(cur) == 1 and cur[0].rstrip().endswith("':") and 'in function' in cur[0] \
                and re.search(r': (warning|error):', line):
            cur.append(line.strip())
            out.append(cur)
            cur = None
            continue
        if MSG_START.match(line):
            if cur:
                out.append(cur)
            cur = [line.strip()]
        elif (cur is not None and line.startswith((' ', '\t')) and line.strip() and 'warning C' not in cur[0]
              and not re.match(r'^\s*(CPU-time|Number of|Minimum integration|Maximum integration)', line)):
            cur.append(line.strip())
        else:
            if cur:
                out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return ['[%s] %s' % (source, ' | '.join(b)) for b in out]


def conversion_notice(text):
    """The library-conversion notice that openModel prints between two dashed lines, as one message."""
    m = re.search(r'-{10,}\s*\n(.*?)\n\s*-{10,}', text, re.S)
    if not m:
        return []
    lines = [re.sub(r'\s+', ' ', l.strip()) for l in m.group(1).splitlines() if l.strip()]
    return ['[openModel, notice] ' + ' | '.join(lines)]


def read(path):
    if not os.path.isfile(path):
        return ''
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def resample(rd, names, grid):
    """Piecewise-linear reconstruction of a Dymola trajectory on the grid (same as the Windows post.py)."""
    t = rd.time()
    new = np.ones(len(t), dtype=bool)
    new[1:] = (t[1:] - t[:-1]) > 1e-9
    f = np.flatnonzero(new)
    l = np.append(f[1:] - 1, len(t) - 1)
    tu = t[l]
    k = np.searchsorted(tu, grid + 1e-9, side='right') - 1
    inside = (k >= 0) & (grid <= tu[-1] + 1e-9)
    kk = np.clip(k, 0, len(tu) - 1)
    on = inside & (np.abs(grid - tu[kk]) <= 1e-9)
    kn = np.clip(kk + 1, 0, len(tu) - 1)
    span = tu[kn] - tu[kk]
    w = np.where(span > 0, (grid - tu[kk]) / np.where(span > 0, span, 1.0), 0.0)
    cols, missing = [], []
    for n in names:
        if not rd.has(n):
            missing.append(n)
            cols.append(np.full(len(grid), np.nan))
            continue
        y = rd.values(n)
        yl, yf = y[l], y[f]
        v = yl[kk] + (yf[kn] - yl[kk]) * w
        v = np.where(on, yl[kk], v)
        v = np.where(inside, v, np.nan)
        cols.append(v)
    return np.column_stack([grid] + cols), missing, int(len(f))


def msl_version(rec):
    p = rec.get('msl_package_file') or ''
    m = re.search(r'Modelica ([0-9.]+)/package\.mo', p)
    v = m.group(1) if m else 'unknown'
    return ('%s (the only MSL in Dymola 2026x Refresh 1 for Linux, %s; OpenIPSL uses 4.0.0, Dymola reports no '
            'conversion needed)' % (v, p))


def compiler_text(rec):
    b = rec.get('build_after_simulate') or rec.get('build') or {}
    return ('%s (dymosim .comment; dsbuild.sh "Using CC=%s", cc -> %s); dsbuild.sh defaults, no user options: '
            '-O1 -D_LINUX64 -DUNIX -DSkip_f2c_Undefs, PIE (Ubuntu gcc default), -Wl,--no-as-needed '
            '-Wl,--no-undefined -Wl,--allow-multiple-definition; the library linked with '
            '-L<pkg>/Resources/Library/linux64 -Wl,-rpath=<same> -l<Name> (DT_RUNPATH)'
            % (b.get('dymosim_comment'), b.get('buildlog_using_cc'), b.get('cc_resolves_to')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run')
    ap.add_argument('--name')
    ap.add_argument('--out')
    ap.add_argument('--grid', type=float)
    ap.add_argument('--stop', type=float)
    ap.add_argument('--recipe', default=None, help='the exact command that ran the simulation')
    ap.add_argument('--outcome', default=None, help='override the outcome (e.g. skipped) with --reason')
    ap.add_argument('--reason', default=None)
    ap.add_argument('--selftest', default=None)
    a = ap.parse_args()
    if a.selftest:
        print('max |reader - scipy| =', check_reader(a.selftest, ['sCRX9.EFD', 'gENROU.w', 'GEN1.v', 'sCRX9.T_E']))
        return 0

    rec = json.loads(read(os.path.join(a.run, 'run.json')))
    model = rec['model']
    ar = rec['args']
    dsl = rec.get('dslog') or {}
    ok = bool(rec.get('ok', {}).get('translate')) and bool(rec.get('ok', {}).get('simulate'))
    t_reached = dsl.get('T reached')
    outcome = 'ok' if ok and t_reached is not None and abs(t_reached - ar['stop']) < 1e-9 else 'failed'
    reason = None
    if outcome == 'failed':
        reason = 'translate=%s simulate=%s, dslog: %s' % (rec.get('ok', {}).get('translate'),
                                                          rec.get('ok', {}).get('simulate'), dsl.get('termination line'))
    if a.outcome:
        outcome, reason = a.outcome, a.reason

    msgs = []
    open_log = read(os.path.join(a.run, 'dymola_open_log.txt'))
    msgs += conversion_notice(open_log)
    msgs += message_blocks(open_log, 'openModel')
    msgs += message_blocks(read(os.path.join(a.run, 'dymola_translation_log.txt')), 'translateModel')
    msgs += message_blocks(read(os.path.join(a.run, 'buildlog.txt')), 'buildlog (C compiler)')
    simlog = read(os.path.join(a.run, 'dymola_simulation_log.txt'))
    msgs += message_blocks(simlog, 'simulateExtendedModel')
    msgs += message_blocks(read(os.path.join(a.run, 'dslog.txt')), 'dslog')
    all_msgs = msgs[:]
    msgs = msgs[:20]

    res = os.path.join(a.run, 'dsres.mat')
    raw_points = None
    csv_info = {}
    os.makedirs(a.out, exist_ok=True)
    if os.path.isfile(res) and os.path.getsize(res) > 0:
        rd = DsRes(res)
        raw_points = rd.npoints
        n = int(round(a.stop / a.grid))
        grid = np.round(np.arange(n + 1) * a.grid, 10)
        names = SIGNALS[model]
        data, missing, distinct = resample(rd, names, grid)
        np.savetxt(os.path.join(a.out, a.name + '.csv'), data, delimiter=',', fmt='%.12g',
                   header=','.join(['time'] + names), comments='')
        tt = rd.time()
        csv_info = {'grid_points': int(len(grid)), 'missing_signals': missing, 'distinct_time_instants': distinct,
                    'result_precision': rd.precision, 'first_time': float(tt[0]), 'last_time': float(tt[-1]),
                    'nan_cells': int(np.isnan(data[:, 1:]).sum())}
        with open(os.path.join(a.out, a.name + '_raw_points.txt'), 'w', encoding='utf-8') as f:
            f.write('stored points in dsres.mat: %d\n' % raw_points)
            f.write('distinct time instants (points closer than 1e-9 s merged): %d\n' % distinct)
            f.write('first/last stored time: %.12g / %.12g s\n' % (tt[0], tt[-1]))
            f.write('storage: %s, values before and after every event stored (Dymola default)\n' % rd.precision)
            f.write('file: %s (%d bytes), kept in the build tree\n' % (res, os.path.getsize(res)))

    tms = rec.get('times_s', {})
    b = rec.get('build') or {}
    m = {
        'tool': 'Dymola',
        'tool_version': rec.get('dymola_version'),
        'msl_version': msl_version(rec),
        'platform': PLATFORM,
        'compiler': compiler_text(rec),
        'test': model,
        'solver': ar['solver'],
        'step': ar['step'] if ar['solver'] == 'euler' else None,
        'tolerance': ar['tolerance'],
        'start_time': ar['start'],
        'stop_time': ar['stop'],
        'output_interval': ar['interval'],
        'translate_s': tms.get('dymola_total_translation_time_s'),
        'compile_s': b.get('build_s_from_mtimes'),
        'simulate_wall_s': tms.get('simulateExtendedModel_wall'),
        'cpu_integration_s': dsl.get('CPU-time for integration'),
        'steps': dsl.get('Number of accepted steps'),
        'f_evaluations': dsl.get('Number of f-evaluations (dynamics)'),
        'jacobian_evaluations': dsl.get('Number of Jacobian-evaluations'),
        'time_events': dsl.get('Number of model time events'),
        'state_events': dsl.get('Number of state events'),
        'result_points': dsl.get('Number of result points', raw_points),
        'outcome': outcome,
        'tool_messages': msgs,
        'recipe': a.recipe or (read(os.path.join(a.run, 'driver.out')).splitlines() or [' '.join(rec.get('argv', []))])[0],
        'extra': {
            'reason': reason,
            'simulate_command': rec.get('simulate_command'),
            'translateModel_wall_s': tms.get('translateModel_wall'),
            'dymola_reported_compilation_time_s': tms.get('dymola_compilation_time_s'),
            'compile_s_definition': 'dymosim mtime minus dsmodel.c mtime (the gcc build of dsbuild.sh); Dymola for '
                                    'Linux reports only the figure in dymola_reported_compilation_time_s',
            'start_dymola_s': tms.get('start_dymola'),
            'open_package_s': tms.get('open_package'),
            'session_total_wall_s': tms.get('total_wall'),
            'cpu_initialization_s': dsl.get('CPU-time for initialization'),
            'grid_points': dsl.get('Number of grid points'),
            'crossing_function_evaluations': dsl.get('Number of crossing function evaluations'),
            'input_time_events': dsl.get('Number of input time events'),
            'step_events': dsl.get('Number of step events'),
            'min_step': dsl.get('Minimum integration stepsize'),
            'max_step': dsl.get('Maximum integration stepsize'),
            'max_order': dsl.get('Maximum integration order'),
            'method_line': dsl.get('method line'),
            'termination_line': dsl.get('termination line'),
            'T_reached': t_reached,
            'raw_points_in_file': raw_points,
            'csv': csv_info,
            'experiment_annotation': rec.get('experiment_annotation'),
            'dsin_lprec_line': rec.get('dsin_lprec_line'),
            'msl_package_file': rec.get('msl_package_file'),
            'compiler_GetDymolaCompiler': rec.get('compiler'),
            'build': rec.get('build'),
            'build_after_simulate': rec.get('build_after_simulate'),
            'request_option_standard': rec.get('request_option_standard'),
            'evaluate_in_effect': rec.get('evaluate_in_effect'),
            'flags_read_only': rec.get('flags_read_only'),
            'platform_detail': rec.get('platform'),
            'flags_before': rec.get('flags_before'),
            'flags_restored': rec.get('flags_restored'),
            'flags_after_restore': rec.get('flags_after_restore'),
            'messages_total': len(all_msgs),
        },
    }
    with open(os.path.join(a.out, a.name + '_metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(m, f, indent=2, default=str)
    logdir = os.path.join(a.out, 'logs', a.name)
    os.makedirs(logdir, exist_ok=True)
    for fn in ('run.json', 'dymola_open_log.txt', 'dymola_translation_log.txt', 'dymola_simulation_log.txt',
               'dymola_command_log.txt', 'dslog.txt', 'buildlog.txt', 'dir_after_translate.txt', 'dir_after_simulate.txt',
               'driver.out'):
        p = os.path.join(a.run, fn)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(logdir, fn))
    with open(os.path.join(logdir, 'all_messages.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_msgs) + '\n')
    print(json.dumps({k: m[k] for k in ('test', 'solver', 'outcome', 'translate_s', 'compile_s', 'simulate_wall_s',
                                         'cpu_integration_s', 'steps', 'time_events', 'state_events', 'result_points')}),
          'csv:', csv_info)
    return 0


if __name__ == '__main__':
    sys.exit(main())
