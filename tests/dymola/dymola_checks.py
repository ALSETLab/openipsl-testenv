"""Dymola for Linux: checkModel, normal and pedantic, of every class of Electrical.Controls.IEEE_CIGRE and
Tests.Controls.IEEE_CIGRE (Linux port of the Windows round-2 recipe: report/round2/scripts/dymola_checks_round2.py
for both modes, report/verification_round2/dymola/scripts/dymola_pedantic.py for the pedantic mode).

One hidden Dymola session, DymolaInterface(dymolapath=<.../bin64/dymola.sh>, showwindow=False);
RequestOption("Standard") recorded; Advanced.UI.SkipMessageDialogs read, set to true and written back before close;
openModel(<lib>/package.mo, changeDirectory=False); cd to a build folder outside Dropbox; checkModel(cls) and
checkModel(cls, pedantic=True) once per class. The classes are the packages (folders) and the entries of every
package.order under the two trees, in package.order order.

Writes <out>/dymola_checks.json and <out>/dymola_checks.txt (every message verbatim, HTML tags removed).
Usage: python -I -B dymola_checks.py --lib <OpenIPSL folder> --work <build dir> --out <record dir>
           [--dymola /opt/dymola-2026xRefresh1-x86_64/bin64/dymola.sh] [--evaluate true|false|keep]
"""
import argparse
import json
import os
import re
import sys
import time

from dymola.dymola_interface import DymolaInterface

DEFAULT_DYMOLA = '/opt/dymola-2026xRefresh1-x86_64/bin64/dymola.sh'


def classes_of(lib):
    out = []

    def walk(folder, pkg):
        out.append(pkg)
        op = os.path.join(folder, 'package.order')
        order = []
        if os.path.isfile(op):
            with open(op, encoding='utf-8') as f:
                order = [l.strip() for l in f if l.strip()]
        for name in order:
            sub = os.path.join(folder, name)
            if os.path.isdir(sub):
                walk(sub, pkg + '.' + name)
            else:
                out.append(pkg + '.' + name)

    for rel in ('Electrical/Controls/IEEE_CIGRE', 'Tests/Controls/IEEE_CIGRE'):
        walk(os.path.join(lib, rel), 'OpenIPSL.' + rel.replace('/', '.'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lib', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dymola', default=DEFAULT_DYMOLA)
    ap.add_argument('--evaluate', choices=['true', 'false', 'keep'], default='true',
                    help='Dymola flag Evaluate (read before, written back); true as in the Windows round-2 setup')
    a = ap.parse_args()
    lib = os.path.abspath(a.lib)
    pkg = os.path.join(lib, 'package.mo')
    os.makedirs(a.work, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    cls = classes_of(lib)
    rec = {'package': pkg, 'classes': cls, 'results': [], 'argv': sys.argv}
    t_start = time.perf_counter()
    d = DymolaInterface(dymolapath=a.dymola, showwindow=False)
    rec['start_dymola_s'] = time.perf_counter() - t_start
    try:
        rec['version'] = d.DymolaVersion()
        rec['skip_before'] = d.ExecuteCommand('Advanced.UI.SkipMessageDialogs')
        rec['evaluate_before'] = d.ExecuteCommand('Evaluate')
        d.ExecuteCommand('Advanced.UI.SkipMessageDialogs = true')
        if a.evaluate != 'keep':
            d.ExecuteCommand('Evaluate = %s' % a.evaluate)
        rec['evaluate_in_effect'] = d.ExecuteCommand('Evaluate')
        rec['request_option_standard'] = d.ExecuteCommand('RequestOption("Standard")')
        t0 = time.perf_counter()
        ok = d.openModel(pkg, changeDirectory=False)
        rec['open'] = {'ok': ok, 'log': d.getLastErrorLog(), 'wall_s': time.perf_counter() - t0}
        if not ok:
            print(rec['open'])
            return 1
        d.cd(os.path.abspath(a.work))
        for mode in ('normal', 'pedantic'):
            for c in cls:
                t0 = time.perf_counter()
                okc = d.checkModel(c, pedantic=(mode == 'pedantic'))
                log = re.sub(r'<[^>]+>', '', d.getLastErrorLog() or '')
                row = {'class': c, 'mode': mode, 'ok': okc, 'wall_s': round(time.perf_counter() - t0, 3), 'log': log,
                       'warning_lines': [l.strip() for l in log.splitlines() if re.search(r'\bwarning\b', l, re.I)],
                       'error_lines': [l.strip() for l in log.splitlines() if re.search(r'\berror\b', l, re.I)]}
                rec['results'].append(row)
                print('%-8s %-85s ok=%s warnings=%d errors=%d' % (mode, c, okc, len(row['warning_lines']),
                                                                 len(row['error_lines'])), flush=True)
    finally:
        try:
            v = rec.get('skip_before')
            if isinstance(v, bool):
                d.ExecuteCommand('Advanced.UI.SkipMessageDialogs = %s' % ('true' if v else 'false'))
                rec['skip_restored'] = v
                rec['skip_after_restore'] = d.ExecuteCommand('Advanced.UI.SkipMessageDialogs')
            v = rec.get('evaluate_before')
            if isinstance(v, bool):
                d.ExecuteCommand('Evaluate = %s' % ('true' if v else 'false'))
                rec['evaluate_after_restore'] = d.ExecuteCommand('Evaluate')
        except Exception as e:  # noqa: BLE001
            rec['skip_restored'] = 'failed: %s' % e
        d.close()
        rec['session_wall_s'] = time.perf_counter() - t_start
    with open(os.path.join(a.out, 'dymola_checks.json'), 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=1)
    with open(os.path.join(a.out, 'dymola_checks.txt'), 'w', encoding='utf-8') as f:
        f.write('Dymola: %s\nRequestOption("Standard"): %s\nEvaluate: %s (before %s, after %s)\nopenModel: %s\n%s\n'
                % (rec.get('version'), rec.get('request_option_standard'), rec.get('evaluate_in_effect'),
                   rec.get('evaluate_before'), rec.get('evaluate_after_restore'), rec['open']['ok'],
                   rec['open']['log']))
        for r in rec['results']:
            f.write('\n===== %s | %s | ok=%s | warnings=%d | errors=%d | %.2f s\n%s\n'
                    % (r['class'], r['mode'], r['ok'], len(r['warning_lines']), len(r['error_lines']), r['wall_s'],
                       r['log']))
    summary = {}
    for mode in ('normal', 'pedantic'):
        rows = [r for r in rec['results'] if r['mode'] == mode]
        summary[mode] = {'classes': len(rows), 'failed': [r['class'] for r in rows if not r['ok']],
                         'with_warnings': [r['class'] for r in rows if r['warning_lines']]}
        print('%s: %d classes, failed: %s, with warnings: %s' % (mode, len(rows), summary[mode]['failed'],
                                                                 summary[mode]['with_warnings']))
    with open(os.path.join(a.out, 'dymola_checks_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1)
    bad = any(summary[m]['failed'] for m in summary)
    return 2 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
