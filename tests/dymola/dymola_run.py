"""Translate and simulate one OpenIPSL test in Dymola for Linux, headlessly (Linux port of the Windows round-2 recipe).

Port of report/verification_round2/dymola/scripts/dymola_run.py (Windows, Dymola 2026x Refresh 1). Same recipe:
a fresh hidden Dymola per run through the Dymola Python interface; Advanced.UI.SkipMessageDialogs = true;
openModel(<package.mo>, changeDirectory=false); cd to the run folder; translateModel and simulateExtendedModel timed
with time.perf_counter; Dymola's own translation and compilation times from Advanced.Translation.Log.Timing; the
statistics block of dslog.txt; Advanced.Simulation.MaxRunTime = <cap> (Dymola's own wall-clock limit of the
simulation); experimentSetupOutput(doublePrecision=true); every Advanced flag set here is read before and written
back before the session closes, and the output setup is put back to Dymola's defaults (experimentSetupOutput()).

What the Linux port adds (nothing in the simulation recipe changes):
  - Dymola is started with DymolaInterface(dymolapath=<.../bin64/dymola.sh>, showwindow=False);
  - RequestOption("Standard") is recorded (licence check);
  - after the build, the facts of how dymosim finds lib<Name>.so: the compiler line of buildlog.txt
    ("Using CC=..."), the compiler that `cc` resolves to and its version, the .comment section of dymosim
    (the compiler that really built it), readelf -d (NEEDED, RUNPATH/RPATH), ldd for the OpenIPSL libraries, and the
    dllLibraryPath[] entries of dsmodel.c;
  - --translate-only, for the build diagnostics (no simulation);
  - --evaluate true|false|keep sets Dymola's flag Evaluate (read before, written back). Default true, because the
    Windows round-2 record ran with Evaluate = true (a persistent flag of its setup.dymx, printed as "Settings |
    Evaluate = true" in each of its translation logs) while Dymola's default, and this distro's setup, is false.

Usage (python = /opt/openipsl-kit/venv-dymola/bin/python):
  python -I -B dymola_run.py --package <OpenIPSL/package.mo> --model <Pkg.Model> --work <dir>
      --solver dassl|euler [--step 1e-5] --stop <s> --interval <s> --tolerance 1e-6 [--maxruntime 1800]
      [--dymola /opt/dymola-2026xRefresh1-x86_64/bin64/dymola.sh] [--translate-only] [--evaluate true|false|keep]

Writes run.json in --work (the raw record that post.py turns into the data-contract files) plus
dymola_open_log.txt, dymola_translation_log.txt, dymola_simulation_log.txt, dymola_command_log.txt and Dymola's own
dsin.txt, dslog.txt, buildlog.txt, dsres.mat. Exit status 0 when translation and simulation both succeeded.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

from dymola.dymola_interface import DymolaInterface

DEFAULT_DYMOLA = '/opt/dymola-2026xRefresh1-x86_64/bin64/dymola.sh'

STAT_KEYS = [
    'CPU-time for integration',
    'CPU-time for one grid interval',
    'CPU-time for initialization',
    'Number of result points',
    'Number of grid points',
    'Number of accepted steps',
    'Number of f-evaluations (dynamics)',
    'Number of crossing function evaluations',
    'Number of Jacobian-evaluations',
    'Number of model time events',
    'Number of input time events',
    'Number of state events',
    'Number of step events',
    'Minimum integration stepsize',
    'Maximum integration stepsize',
    'Maximum integration order',
]

FLAGS = ['Advanced.UI.SkipMessageDialogs', 'Advanced.Translation.Log.Timing', 'Advanced.Simulation.MaxRunTime', 'Evaluate']
# read only, for the record (the Windows round-2 setup.dymx had it as a persistent flag, value true)
READ_ONLY_FLAGS = ['Advanced.Translation.SmartSimulateExtended']


def parse_dslog(text):
    stats = {}
    for key in STAT_KEYS:
        m = re.search(re.escape(key) + r'\s*:\s*([-+0-9.eE]+)', text)
        if m:
            try:
                stats[key] = float(m.group(1))
            except ValueError:
                stats[key] = m.group(1)
    m = re.search(r'^.*Integration started.*$', text, re.M)
    stats['method line'] = m.group(0).strip() if m else None
    m = re.search(r'^.*(Integration terminated|terminated successfully|failed|stopped|Simulation terminated).*$', text, re.M)
    stats['termination line'] = m.group(0).strip() if m else None
    m = re.search(r'(?:terminated|stopped)[^\n]*?at T\s*=\s*([-+0-9.eE]+)', text)
    stats['T reached'] = float(m.group(1)) if m else None
    return stats


def listing(d):
    rows = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        rows.append('%12d  %s' % (os.path.getsize(p), name) if os.path.isfile(p) else '%12s  %s/' % ('<dir>', name))
    return '\n'.join(rows) + '\n'


def write(path, text):
    with open(path, 'w', encoding='utf-8', errors='replace') as f:
        f.write(text if text is not None else '')


def as_dymola_literal(val):
    if isinstance(val, bool):
        return 'true' if val else 'false'
    if isinstance(val, (int, float)):
        return repr(val)
    return None


def sh(cmd, cwd=None):
    """Output of a shell command (stdout and stderr), for the build facts; never raises."""
    try:
        r = subprocess.run(['bash', '-c', cmd], cwd=cwd, capture_output=True, text=True, timeout=120)
        return (r.stdout + r.stderr).rstrip('\n')
    except Exception as e:  # noqa: BLE001
        return 'failed: %s' % e


def build_facts(work):
    """How the generated dymosim was built and how it finds the OpenIPSL shared libraries."""
    f = {}
    blog = os.path.join(work, 'buildlog.txt')
    if os.path.isfile(blog):
        with open(blog, encoding='utf-8', errors='replace') as fh:
            m = re.search(r'^Using CC=(.*)$', fh.read(), re.M)
        f['buildlog_using_cc'] = m.group(1).strip() if m else None
    cc = shutil.which('cc')
    f['cc_on_path'] = cc
    f['cc_resolves_to'] = os.path.realpath(cc) if cc else None
    f['cc_version'] = sh('cc --version | head -n1')
    f['clang_version'] = sh('clang --version 2>/dev/null | head -n1')
    dym = os.path.join(work, 'dymosim')
    if os.path.isfile(dym):
        f['dymosim_comment'] = sh("readelf -p .comment dymosim | sed -n 's/^ *\\[ *[0-9a-f]*\\] *//p'", cwd=work)
        f['readelf_dynamic'] = sh("readelf -d dymosim | grep -E 'NEEDED|RUNPATH|RPATH'", cwd=work)
        f['ldd_openipsl'] = sh("ldd ./dymosim | grep -E 'SCRX9|GFM_GFL_IBR|not found' || echo '(no OpenIPSL library needed)'",
                               cwd=work)
    src = os.path.join(work, 'dsmodel.c')
    if os.path.isfile(src):
        with open(src, encoding='utf-8', errors='replace') as fh:
            txt = fh.read()
        m = re.search(r'dllLibraryPath\[\]=\{(.*?)\n0\};', txt, re.S)
        f['dsmodel_dllLibraryPath'] = re.findall(r'"([^"]+)"', m.group(1)) if m else None
    # Dymola for Linux reports "Compilation time: 0.001 s" in the translation log (it does not time the C build),
    # so the build time is measured from the files: dsmodel.c is written last by the translator, dymosim last by
    # the linker of dsbuild.sh (ext4, nanosecond timestamps).
    if os.path.isfile(src) and os.path.isfile(dym):
        f['dsmodel_c_mtime_ns'] = os.stat(src).st_mtime_ns
        f['dymosim_mtime_ns'] = os.stat(dym).st_mtime_ns
        f['build_s_from_mtimes'] = (f['dymosim_mtime_ns'] - f['dsmodel_c_mtime_ns']) / 1e9
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--package', required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--solver', required=True, choices=['dassl', 'euler'])
    ap.add_argument('--step', type=float, default=None)
    ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--stop', type=float, required=True)
    ap.add_argument('--interval', type=float, required=True)
    ap.add_argument('--tolerance', type=float, default=1e-6)
    ap.add_argument('--maxruntime', type=float, default=1800.0)
    ap.add_argument('--dymola', default=DEFAULT_DYMOLA, help='Dymola start script')
    ap.add_argument('--translate-only', action='store_true', help='diagnostics: translate (and build) only')
    ap.add_argument('--evaluate', choices=['true', 'false', 'keep'], default='true',
                    help='Dymola flag Evaluate for the translation. Default true: the setting in effect in the Windows '
                         'round-2 record (a persistent flag of its setup.dymx; its translation logs print '
                         '"Settings | Evaluate = true"). false = the Dymola default; keep = leave it as it is')
    a = ap.parse_args()

    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    pkg = os.path.abspath(a.package)
    if not os.path.isfile(pkg):
        sys.exit('no such file: ' + pkg)
    method = 'Dassl' if a.solver == 'dassl' else 'Euler'
    if a.solver == 'euler' and not a.step:
        sys.exit('--step is required for euler')

    rec = {'model': a.model, 'package': pkg, 'work': work, 'args': vars(a), 'argv': sys.argv,
           'times_s': {}, 'ok': {}, 'flags_before': {}, 'flags_set': {}, 'flags_restored': {},
           'platform': {'uname': sh('uname -srm'), 'os': sh('. /etc/os-release && echo "$PRETTY_NAME"'),
                        'glibc': sh('ldd --version | head -n1')}}
    t_all = time.perf_counter()
    t0 = time.perf_counter()
    dymola = DymolaInterface(dymolapath=a.dymola, showwindow=False)
    rec['times_s']['start_dymola'] = time.perf_counter() - t0
    rec['dymola_version'] = dymola.DymolaVersion()
    rec['dymola_version_number'] = dymola.DymolaVersionNumber()
    ok_all = False
    try:
        for name in FLAGS:
            try:
                rec['flags_before'][name] = dymola.ExecuteCommand(name)
            except Exception as e:  # noqa: BLE001
                rec['flags_before'][name] = 'query failed: %s' % e
        for name in READ_ONLY_FLAGS:
            try:
                rec['flags_read_only'] = rec.get('flags_read_only', {})
                rec['flags_read_only'][name] = dymola.ExecuteCommand(name)
            except Exception as e:  # noqa: BLE001
                rec['flags_read_only'][name] = 'query failed: %s' % e
        cmds = ['Advanced.UI.SkipMessageDialogs = true', 'Advanced.Translation.Log.Timing = true',
                'Advanced.Simulation.MaxRunTime = %r' % float(a.maxruntime)]
        if a.evaluate != 'keep':
            cmds.append('Evaluate = %s' % a.evaluate)
        for cmd in cmds:
            rec['flags_set'][cmd] = dymola.ExecuteCommand(cmd)
        rec['evaluate_in_effect'] = dymola.ExecuteCommand('Evaluate')
        try:
            rec['request_option_standard'] = dymola.ExecuteCommand('RequestOption("Standard")')
        except Exception as e:  # noqa: BLE001
            rec['request_option_standard'] = 'failed: %s' % e
        rec['experimentSetupOutput'] = dymola.experimentSetupOutput(doublePrecision=True)
        rec['compiler'] = dymola.GetDymolaCompiler()

        t0 = time.perf_counter()
        ok = dymola.openModel(pkg, changeDirectory=False)
        rec['times_s']['open_package'] = time.perf_counter() - t0
        open_log = dymola.getLastErrorLog()
        write(os.path.join(work, 'dymola_open_log.txt'), '=== openModel(%s) -> %s\n%s\n' % (pkg, ok, open_log))
        rec['ok']['open'] = ok
        if not ok:
            return 1
        try:
            rec['msl_package_file'] = dymola.ExecuteCommand(
                'Modelica.Utilities.Files.loadResource("modelica://Modelica/package.mo")')
            rec['complex_package_file'] = dymola.ExecuteCommand(
                'Modelica.Utilities.Files.loadResource("modelica://Complex.mo")')
        except Exception as e:  # noqa: BLE001
            rec['msl_package_file'] = 'query failed: %s' % e
        dymola.cd(work)

        t0 = time.perf_counter()
        ok = dymola.translateModel(a.model)
        rec['times_s']['translateModel_wall'] = time.perf_counter() - t0
        rec['ok']['translate'] = ok
        tlog = dymola.getLastErrorLog()
        write(os.path.join(work, 'dymola_translation_log.txt'), tlog)
        write(os.path.join(work, 'dir_after_translate.txt'), listing(work))
        for key, pat in (('dymola_total_translation_time_s', r'Total translation time:\s*([0-9.eE+-]+)\s*s'),
                         ('dymola_compilation_time_s', r'Compilation time:\s*([0-9.eE+-]+)\s*s')):
            m = re.search(pat, tlog)
            rec['times_s'][key] = float(m.group(1)) if m else None
        try:
            rec['experiment_annotation'] = list(dymola.getExperiment())
        except Exception as e:  # noqa: BLE001
            rec['experiment_annotation'] = 'getExperiment failed: %s' % e
        if os.path.isfile(os.path.join(work, 'buildlog.txt')):
            shutil.copy2(os.path.join(work, 'buildlog.txt'), os.path.join(work, 'buildlog_after_translate.txt'))
        rec['build'] = build_facts(work)
        if not ok:
            return 1
        if a.translate_only:
            ok_all = True
            return 0

        kw = dict(problem=a.model, startTime=a.start, stopTime=a.stop, numberOfIntervals=0,
                  outputInterval=a.interval, method=method, tolerance=a.tolerance,
                  fixedstepsize=(a.step if a.solver == 'euler' else 0.0), resultFile='dsres', finalNames=[],
                  autoLoad=False)
        rec['simulate_kwargs'] = dict(kw)
        rec['simulate_command'] = ('simulateExtendedModel(problem="%s", startTime=%r, stopTime=%r, numberOfIntervals=0, '
                                   'outputInterval=%r, method="%s", tolerance=%r, fixedstepsize=%r, resultFile="dsres")'
                                   % (a.model, a.start, a.stop, a.interval, method, a.tolerance, kw['fixedstepsize']))
        t0 = time.perf_counter()
        ok, _vals = dymola.simulateExtendedModel(**kw)
        rec['times_s']['simulateExtendedModel_wall'] = time.perf_counter() - t0
        rec['ok']['simulate'] = ok
        write(os.path.join(work, 'dymola_simulation_log.txt'), dymola.getLastErrorLog())
        write(os.path.join(work, 'dir_after_simulate.txt'), listing(work))
        dslog_path = os.path.join(work, 'dslog.txt')
        if os.path.isfile(dslog_path):
            with open(dslog_path, encoding='utf-8', errors='replace') as f:
                rec['dslog'] = parse_dslog(f.read())
        dsin_path = os.path.join(work, 'dsin.txt')
        if os.path.isfile(dsin_path):
            with open(dsin_path, encoding='utf-8', errors='replace') as f:
                m = re.search(r'^\s*(\S+)\s+#\s*lprec\b.*$', f.read(), re.M)
            rec['dsin_lprec_line'] = m.group(0).strip() if m else None
        # the simulate call could rebuild dymosim; take the build facts again from what ran
        rec['build_after_simulate'] = build_facts(work)
        ok_all = ok
    finally:
        for name, val in rec['flags_before'].items():
            txt = as_dymola_literal(val)
            if txt is None:
                rec['flags_restored'][name] = 'not restored (value before: %r)' % (val,)
                continue
            try:
                dymola.ExecuteCommand('%s = %s' % (name, txt))
                rec['flags_restored'][name] = txt
            except Exception as e:  # noqa: BLE001
                rec['flags_restored'][name] = 'restore failed: %s' % e
        try:
            rec['flags_after_restore'] = {n: dymola.ExecuteCommand(n) for n in rec['flags_before']}
        except Exception as e:  # noqa: BLE001
            rec['flags_after_restore'] = 'query failed: %s' % e
        try:
            rec['experimentSetupOutput_restored'] = dymola.experimentSetupOutput()
        except Exception as e:  # noqa: BLE001
            rec['experimentSetupOutput_restored'] = 'failed: %s' % e
        try:
            dymola.savelog(os.path.join(work, 'dymola_command_log.txt'))
        except Exception:  # noqa: BLE001
            pass
        t0 = time.perf_counter()
        dymola.close()
        rec['times_s']['close_dymola'] = time.perf_counter() - t0
        rec['times_s']['total_wall'] = time.perf_counter() - t_all
        with open(os.path.join(work, 'run.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, indent=2, default=str)
        print(json.dumps({k: rec.get(k) for k in ('model', 'ok', 'times_s', 'dslog', 'flags_restored',
                                                  'request_option_standard')},
                         indent=2, default=str))
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
