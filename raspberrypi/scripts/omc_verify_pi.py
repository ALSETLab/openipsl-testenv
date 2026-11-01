"""omc_verify_pi.py - OpenModelica verification runs of the IEEE_CIGRE tests of OpenIPSL on Linux aarch64 (Raspberry
Pi 400, Raspberry Pi OS 64-bit trixie), with the lib<Name>.so files built here into Resources/Library/aarch64-linux,
and OpenModelica 1.27.2 from the build.openmodelica.org apt repository (arm64). Port (2026-11-01, ARM Linux
verification) of the macOS script omc_verify_macos.py, itself a port of the Linux kit's tests/openmodelica/omc_verify.py;
the run list, .mos text, signals, grids and metrics fields are unchanged.
Pi parts: omc path ($OMC, default /usr/bin/omc); platform string from /etc/os-release, the device-tree model and
glibc; the library binding back to the Linux form (readelf -d, ldd; run-time trace with LD_DEBUG=libs and
LD_DEBUG_OUTPUT, link-time trace with GNU ld's --verbose); the machine load and available memory from /proc (3.7 GiB
RAM: every omc process runs alone). The keys named "linux" in self_comparison.json mean "this platform".

The macOS docstring said: port of the Linux kit's script with otool/dyld instead of readelf/LD_DEBUG. The Linux
docstring follows.

Linux port (2026-10-25) of the Windows round-2 driver
  report/verification_round2/openmodelica/scripts/omc_verify.py
with the same run list, .mos text, signals, grids and metrics fields. What changed for Linux:
  * omc is /usr/bin/omc (or $OMC); no ucrt64 PATH; the environment is passed through unchanged;
  * the simulation executable has no .exe; omc runs it itself inside simulate();
  * a capped omc process is killed with its whole process group (start_new_session + killpg) instead of taskkill;
  * a cap counts as outcome "failed" (contract of the Linux workflow), not "skipped";
  * every metrics file also records platform, compiler (from the generated makefile, with its --version) and how the
    executable finds lib<Name>.so (makefile link line, readelf -d, ldd);
  * extra commands: env (versions and loaded libraries), extras (unit probe, initialization diagnostics),
    binding (LD_DEBUG=libs trace of omc's own simulate() run), compare (self-comparison against the Windows record).

Recipe of every run (identical to Windows except the paths):
  loadModel(Modelica, {"4.0.0"}, requireExactVersion=true); loadFile(<pkg>/package.mo); cd(<run folder>);
  simulate(<test>, startTime=0, stopTime=<T>, numberOfIntervals=<N>, tolerance=1e-06, method="dassl"|"euler",
           fileNamePrefix="<Test>__<solver>", outputFormat="mat", variableFilter="<contract signals>",
           simflags="-lv=LOG_STATS")
  With method="euler" OpenModelica's step equals the output interval, so N = StopTime/step (1e-5 s for the GFM tests,
  0.005 s for SCRX9) and the CSV is resampled to the contract grid afterwards.

Usage (inside the distro; options go before the command):
  /usr/bin/python3 -I omc_verify.py [--pkg DIR] [--build DIR] [--out DIR] [--win-record DIR] [--win-build DIR]
                                    [--reps N] [--cap S] <command> [<key> ...|all]
  commands: env | checks | parsechecks | extras | run <key>|all | timing <key>|all | binding | compare | table
  --pkg      the package under test, the folder that holds OpenIPSL/package.mo's directory
             (default ~/cigre_verify/pkg/1244ae93/OpenIPSL)
  --build    build tree (generated code, executables, raw .mat), ext4 (default ~/cigre_verify/openmodelica/build)
  --out      record folder (CSV, metrics JSON, raw-points files, logs/), ext4 (default ~/cigre_verify/openmodelica/record);
             tests/openmodelica/run_all.sh copies it to the Windows record folder at the end
  --win-record, --win-build   the Windows round-2 record and build tree, read only, for "compare"
  --reps     repetitions of the timing pass (median kept; default 3, as Windows round 2)
  --cap      wall-time cap per omc process in s (default 1800)
"""
import argparse
import json
import os
import platform
import re
import shutil
import signal
import struct
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser('~')
OMC = os.environ.get('OMC', '/usr/bin/omc')
LIBDIR = os.environ.get('OIPSL_LIBDIR', 'aarch64-linux')
T = 'OpenIPSL.Tests.Controls.IEEE_CIGRE'
CFG = {}   # filled by main(): pkg, build, out, win_record, win_build, reps, cap

GFM_SIG = (['gFM_GFL_IBR.out[%d]' % i for i in range(1, 13)]
           + ['gFM_GFL_IBR.P_ref_pu', 'gFM_GFL_IBR.Q_ref_pu', 'gFM_GFL_IBR.V_ref_pu']
           + ['gFM_GFL_IBR.grid_sensor_%s.voltage' % p for p in 'abc']
           + ['gFM_GFL_IBR.grid_sensor_%s.current' % p for p in 'abc'])
SCRX9_SIG = ['sCRX9.EFD', 'gENROU.EFD', 'gENROU.w', 'gENROU.ETERM', 'GEN1.v', 'gENROU.PELEC']
VS_SIG = ['dll.sCRX9.EFD', 'dll.gENROU.w', 'dll.gENROU.ETERM', 'dll.GEN1.v',
          'native.sCRX.EFD', 'native.gENROU.w', 'native.gENROU.ETERM', 'native.GEN1.v']
SCRX_SIG = ['sCRX.EFD', 'gENROU.EFD', 'gENROU.w', 'gENROU.ETERM', 'GEN1.v', 'gENROU.PELEC']
ZS_SIG = (['transformer.%s.v' % p for p in ('Ad', 'Bd', 'Cd')]
          + ['transformer.%s.i' % p for p in ('Ad', 'Bd', 'Cd')]
          + ['transformer.VSecABLL.v', 'transformer.VSecBCLL1.v',
             'transformer.VSecABLL1.v', 'transformer.VabcSum.y',
             'transformer.Bcurrent.i'])
SSF_SIG = (['smoothShortFault.%s.v' % p for p in 'ABC']
           + ['smoothShortFault.currentSensor2.i', 'smoothShortFault.currentSensor1.i',
              'smoothShortFault.currentSensor.i'])


def _gfm(name, stop):
    return (name, T + '.GFM.' + name, 'euler', stop, int(round(stop / 1e-5)), GFM_SIG, 1e-4, 1e-5)


# key -> (Test, class, solver, stop, numberOfIntervals, signals, CSV grid step, fixed step or None)
RUNS = {}
for _r in [
    ('SCRX9', T + '.SCRX9.SCRX9', 'dassl', 10.0, 2000, SCRX9_SIG, 1e-3, None),
    ('SCRX9', T + '.SCRX9.SCRX9', 'euler', 10.0, 2000, SCRX9_SIG, 1e-3, 0.005),
    ('SCRX9_vs_SCRX', T + '.SCRX9.SCRX9_vs_SCRX', 'dassl', 10.0, 2000, VS_SIG, 1e-3, None),
    ('SCRX', 'OpenIPSL.Tests.Controls.PSSE.ES.SCRX', 'dassl', 10.0, 2000, SCRX_SIG, 1e-3, None),
    _gfm('GFL_Fault', 5.8), _gfm('GFL_POCFault', 4.0), _gfm('GFL_FrequencyStep', 3.0),
    _gfm('GFL_VoltageStep', 3.0), _gfm('GFL_PowerRamp', 3.6), _gfm('GFL_FaultPSCAD', 5.8),
    _gfm('GFM_EMTPFault', 5.9), _gfm('GFM_EMTPFull', 6.0),
    ('EMTPTransformerZeroSeq', T + '.GFM.Components.EMTPTransformerZeroSeq', 'euler', 3.0, 300000, ZS_SIG, 1e-4, 1e-5),
    ('SmoothShortFault', T + '.GFM.Components.SmoothShortFault', 'euler', 5.5, 550000, SSF_SIG, 1e-4, 1e-5),
    ('GFL_PowerRamp', T + '.GFM.GFL_PowerRamp', 'dassl', 3.6, 36000, GFM_SIG, 1e-4, None),
]:
    RUNS['%s__%s' % (_r[0], _r[2])] = _r

# first disturbance of each run (s), for the "before the first disturbance" part of the self-comparison
FIRST_EVENT = {'SCRX9__dassl': 2.0025, 'SCRX9__euler': 2.0025, 'SCRX9_vs_SCRX__dassl': 2.0025, 'SCRX__dassl': 2.0,
               'EMTPTransformerZeroSeq__euler': None, 'SmoothShortFault__euler': 5.0}
for _k in RUNS:
    FIRST_EVENT.setdefault(_k, 2.000005)
DLL_OF = {'SCRX9__dassl': 'SCRX9', 'SCRX9__euler': 'SCRX9', 'SCRX9_vs_SCRX__dassl': 'SCRX9'}
for _k in RUNS:
    if _k.startswith(('GFL_', 'GFM_')):
        DLL_OF[_k] = 'GFM_GFL_IBR'


def mos_str(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def regex_for(signals):
    return '|'.join(['time'] + [re.sub(r'([.\[\]])', r'\\\1', s) for s in signals])


def sh(cmd, **kw):
    """Run a command, return its stdout+stderr text (never raises)."""
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', **kw)
        return r.stdout
    except Exception as e:  # noqa
        return 'ERROR %r' % (e,)


def os_release():
    try:
        txt = open('/etc/os-release', encoding='utf-8').read()
    except OSError:
        return '?'
    mm = re.search(r'^PRETTY_NAME="?([^"\n]*)"?', txt, re.M)
    return mm.group(1) if mm else '?'


def board_model():
    try:
        return open('/proc/device-tree/model', 'rb').read().rstrip(b'\0').decode('ascii', 'replace')
    except OSError:
        return '?'


def platform_str():
    return 'aarch64-linux, %s, glibc %s, %s, kernel %s, %s' % (
        os_release(), platform.libc_ver()[1], board_model(), platform.release(), platform.machine())


def commit_of_pkg():
    p = os.path.join(os.path.dirname(CFG['pkg']), 'COMMIT')
    try:
        return open(p, encoding='utf-8').read().strip()
    except OSError:
        return None


def header():
    return ('print("OMC_VERSION " + getVersion() + "\\n");\n'
            'okm := loadModel(Modelica, {"4.0.0"}, requireExactVersion=true);\n'
            'print("MSL_LOADED " + String(okm) + " " + getVersion(Modelica) + "\\n");\n'
            'print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
            'okl := loadFile("%s/package.mo");\n'
            'print("LIB_LOADED " + String(okl) + "\\n");\n'
            'print("ERR " + getErrorString() + "\\nENDERR\\n");\n' % CFG['pkg'])


def run_omc(d, mos, cap, extra_env=None):
    """omc run.mos in folder d, in its own session; a capped run is killed with its whole process group."""
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'run.mos'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(mos)
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    t0 = time.perf_counter()
    p = subprocess.Popen([OMC, 'run.mos'], cwd=d, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8', errors='replace', start_new_session=True)
    timed_out = False
    try:
        out, _ = p.communicate(timeout=cap)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(p.pid, signal.SIGTERM)
            time.sleep(2.0)
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = p.communicate()
    wall = time.perf_counter() - t0
    with open(os.path.join(d, 'log.txt'), 'w', encoding='utf-8') as f:
        f.write(out)
    return out, wall, timed_out


def machine_load():
    try:
        la = open('/proc/loadavg', encoding='ascii').read().split()[:3]
    except OSError:
        la = None
    mem = None
    try:
        mm = re.search(r'^MemAvailable:\s+(\d+) kB', open('/proc/meminfo', encoding='ascii').read(), re.M)
        mem = round(int(mm.group(1)) / 1048576.0, 2) if mm else None
    except OSError:
        pass
    procs = sh(['ps', '-eo', 'pid,etime,comm,args'])
    other = [l.strip()[:160] for l in procs.splitlines()
             if re.search(r'dymola|dymosim|WSMKernel|wolfram|SystemModeler|\bomc\b', l)
             and 'omc_verify' not in l and 'ps -eo' not in l]
    return {'loadavg_1_5_15': la, 'mem_available_gib': mem, 'other_tool_processes': other}


# ---------------------------------------------------------------- MAT v4 reader (complete or truncated files)
class Mat4:
    """OpenModelica result file (MATLAB v4, Aclass 'binTrans'). Reads a truncated data_2 too (a killed run)."""

    def __init__(self, path):
        with open(path, 'rb') as f:
            buf = f.read()
        pos, mats = 0, {}
        self.truncated = False
        while pos + 20 <= len(buf):
            typ, mrows, ncols, imagf, namlen = struct.unpack_from('<5i', buf, pos)
            pos += 20
            name = buf[pos:pos + namlen].rstrip(b'\0').decode('ascii', 'replace')
            pos += namlen
            prec = (typ // 10) % 10
            dt = {0: '<f8', 1: '<f4', 2: '<i4', 3: '<i2', 4: '<u2', 5: '<u1'}[prec]
            es = np.dtype(dt).itemsize
            nbytes = mrows * ncols * es
            if name == 'data_2' and (ncols == 0 or pos + nbytes > len(buf)):
                avail = (len(buf) - pos) // (mrows * es)
                self.truncated = True
                ncols = avail
                nbytes = mrows * ncols * es
            a = np.frombuffer(buf, dtype=dt, count=mrows * ncols, offset=pos).reshape(ncols, mrows)
            mats[name] = a
            pos += nbytes
        self.aclass = [''.join(chr(int(c)) for c in row).rstrip('\0 ') for row in mats['Aclass']]
        self.names = [''.join(chr(int(c)) for c in row).rstrip('\0 ') for row in mats['name']]
        self.info = mats['dataInfo'].astype(int)
        self.d1 = mats['data_1'].astype(float)
        self.d2 = mats['data_2'].astype(float)
        self.index = {n: i for i, n in enumerate(self.names)}
        self.time = self.d2[:, 0].copy()

    def has(self, n):
        return n in self.index

    def get(self, n):
        i = self.index[n]
        if n == 'time' or i == 0:
            return self.time.copy()
        mat, col = int(self.info[i, 0]), int(self.info[i, 1])
        s = 1.0 if col > 0 else -1.0
        c = abs(col) - 1
        if mat == 1:
            return np.full_like(self.time, s * self.d1[0, c])
        if mat == 0:
            return self.time.copy()
        return s * self.d2[:, c]


def resample(t, y, grid):
    """Linear interpolation; at an instant stored twice (an event) the value after the event is taken."""
    n = len(t)
    idx = np.searchsorted(t, grid, side='right') - 1
    idx = np.clip(idx, 0, n - 2)
    t0, t1 = t[idx], t[idx + 1]
    y0, y1 = y[idx], y[idx + 1]
    dt = t1 - t0
    w = np.where(dt > 0, (grid - t0) / np.where(dt > 0, dt, 1.0), 1.0)
    w = np.clip(w, 0.0, 1.0)
    return y0 + w * (y1 - y0)


# ---------------------------------------------------------------- log parsing (as on Windows)
def parse_record(log):
    rec = {}
    m = re.search(r'record SimulationResult(.*?)end SimulationResult;', log, re.S)
    if not m:
        return None, log
    body = m.group(1)
    mm = re.search(r'resultFile = "([^"]*)"', body)
    rec['resultFile'] = mm.group(1) if mm else ''
    mm = re.search(r'messages = "(.*?)",\s*\n\s*timeFrontend', body, re.S)
    if not mm:
        mm = re.search(r'messages = "(.*?)"\s*\n', body, re.S)
    rec['messages'] = mm.group(1) if mm else ''
    for k in ('timeFrontend', 'timeBackend', 'timeSimCode', 'timeTemplates', 'timeCompile', 'timeSimulation', 'timeTotal'):
        mm = re.search(k + r' = ([0-9.eE+-]+)', body)
        rec[k] = float(mm.group(1)) if mm else None
    return rec, log[m.end():]


def split_errorstring(s):
    """Split the text of getErrorString() into messages (a message starts with '[' or Warning/Error/Notification)."""
    s = s.strip()
    if s.startswith('"'):
        s = s[1:]
    if s.endswith('"'):
        s = s[:-1]
    s = s.replace('\\"', '"')
    msgs, cur = [], []
    for line in s.splitlines():
        if re.match(r'^(\[|Warning:|Error:|Notification:)', line) and cur:
            msgs.append('\n'.join(cur).strip())
            cur = []
        if line.strip():
            cur.append(line.rstrip())
    if cur:
        msgs.append('\n'.join(cur).strip())
    return [m for m in msgs if m]


def parse_stats(messages):
    st = {'timers': {}}
    for line in messages.splitlines():
        mm = re.match(r'^\|.*\|\s+([0-9.eE+-]+)s\s+(?:\[\s*[0-9.]+%\]\s+)?(\S.*)$', line)
        if mm:
            st['timers'][mm.group(2).strip()] = float(mm.group(1))
    for key, pat in (('state_events', r'(\d+) state events'), ('time_events', r'(\d+) time events'),
                     ('steps_taken', r'(\d+) steps taken'), ('functionODE_calls', r'(\d+) calls of functionODE'),
                     ('jacobian_evaluations', r'(\d+) evaluations of jacobian'),
                     ('error_test_failures', r'(\d+) error test failures'),
                     ('convergence_test_failures', r'(\d+) convergence test failures')):
        mm = re.search(pat, messages)
        st[key] = int(mm.group(1)) if mm else None
    mm = re.search(r'solver: (\S+)', messages)
    st['solver'] = mm.group(1) if mm else None
    return st


def sim_messages(messages):
    """Simulation messages other than the LOG_STATS block and the LOG_SUCCESS lines, verbatim."""
    keep, in_stats = [], False
    for line in messages.splitlines():
        if line.startswith('LOG_STATS'):
            in_stats = True
            continue
        if in_stats and line.startswith('|'):
            continue
        in_stats = False
        if line.startswith('LOG_SUCCESS') or not line.strip():
            continue
        keep.append(line.rstrip())
    return keep


# ---------------------------------------------------------------- compiler and library binding of one build
_CC_CACHE = {}


def compiler_info(makefile):
    """C compiler named in the generated makefile (CC=...), resolved on PATH, with its --version."""
    info = {'makefile': makefile}
    try:
        mk = open(makefile, encoding='utf-8', errors='replace').read()
    except OSError:
        return info
    for var in ('CC', 'CXX', 'LINK', 'OMC_CFLAGS_OPTIMIZATION', 'CFLAGS', 'RUNTIME_LIBS', 'LDFLAGS', 'EXEEXT', 'DLLEXT'):
        mm = re.search(r'^%s=(.*)$' % var, mk, re.M)
        info[var] = mm.group(1).strip() if mm else None
    cc = (info.get('CC') or '').split()[0] if info.get('CC') else None
    if cc:
        if cc not in _CC_CACHE:
            path = shutil.which(cc)
            real = os.path.realpath(path) if path else None
            ver = sh([cc, '--version']).splitlines()
            _CC_CACHE[cc] = (path, real, ver[0].strip() if ver else None)
        path, real, ver = _CC_CACHE[cc]
        info['cc_path'] = path
        info['cc_realpath'] = real
        info['cc_version'] = ver
        mm = re.search(r'clang version (\S+)', ver or '') or re.search(r'\) (\d+\.\d+\.\d+)', ver or '')
        info['summary'] = '%s %s (%s; %s -> %s; CC=%s in the generated makefile, %s)' % (
            cc, mm.group(1) if mm else '?', ver, path, real, info.get('CC'), info.get('OMC_CFLAGS_OPTIMIZATION'))
    return info


def binding_info(d, key):
    """How the executable of run folder d was linked against lib<Name>.so and how it finds it (readelf, ldd)."""
    exe = os.path.join(d, key)
    mk = os.path.join(d, key + '.makefile')
    b = {'executable': exe}
    try:
        txt = open(mk, encoding='utf-8', errors='replace').read()
        mm = re.search(r'^omc_main_target:.*\n\t(.*)$', txt, re.M)
        line = mm.group(1) if mm else ''
        b['link_L'] = re.findall(r'-L"?([^" ]+)"?', line)
        b['link_rpath'] = re.findall(r'-Wl,-rpath[=,]"?([^" ]+)"?', line)
        mm = re.search(r'^LDFLAGS=(.*)$', txt, re.M)
        b['ldflags_rpath'] = re.findall(r'-Wl,-rpath[=,]"?([^" ]+)"?', mm.group(1)) if mm else []
        mm = re.search(r'^DIREXTRA=(.*)$', txt, re.M)
        b['dirextra'] = mm.group(1).strip() if mm else None
        b['link_libs'] = re.findall(r'\s-l(\S+)', line)
        mm = re.search(r'^RUNTIME_LIBS=(.*)$', txt, re.M)
        b['disable_new_dtags'] = bool(mm and '--disable-new-dtags' in mm.group(1))
    except OSError:
        pass
    if os.path.isfile(exe):
        rd = sh(['readelf', '-d', exe])
        b['readelf_needed'] = re.findall(r'\(NEEDED\)\s+Shared library: \[([^\]]+)\]', rd)
        mm = re.search(r'\((RPATH|RUNPATH)\)\s+Library (?:rpath|runpath): \[([^\]]*)\]', rd)
        b['dt_tag'] = mm.group(1) if mm else None
        b['dt_path'] = mm.group(2).split(':') if mm else []
        b['ldd'] = [l.strip() for l in sh(['ldd', exe]).splitlines() if re.search(r'SCRX9|GFM_GFL_IBR', l)]
        b['file'] = sh(['file', '-b', exe]).strip()
    b['LD_LIBRARY_PATH'] = os.environ.get('LD_LIBRARY_PATH')
    return b


# ---------------------------------------------------------------- one run
def do_run(key):
    test, cls, solver, stop, n, sigs, grid_dt, step = RUNS[key]
    build, out, cap = CFG['build'], CFG['out'], CFG['cap']
    d = os.path.join(build, key)
    for f in os.listdir(d) if os.path.isdir(d) else []:
        if f.endswith('_res.mat'):
            os.remove(os.path.join(d, f))
    flt = regex_for(sigs)
    simline = ('simulate(%s, startTime=0, stopTime=%s, numberOfIntervals=%d, tolerance=1e-06, method="%s", '
               'fileNamePrefix="%s", outputFormat="mat", variableFilter="%s", simflags="-lv=LOG_STATS");'
               % (cls, repr(float(stop)), n, solver, key, mos_str(flt)))
    mos = header() + 'cd("%s");\n' % d + simline + '\nprint("SIMERR " + getErrorString() + "\\nEND\\n");\n'
    load = machine_load()
    print('[%s] %s start (load %s)' % (time.strftime('%H:%M:%S'), key, load['loadavg_1_5_15']), flush=True)
    log, wall, timed_out = run_omc(d, mos, cap)
    rdir = os.path.join(out, 'logs', key)
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, 'run.mos'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(mos)
    with open(os.path.join(rdir, 'log.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('$ cd %s && %s run.mos   (environment unchanged; LD_LIBRARY_PATH=%s)\n[%.2f s wall%s]\n\n'
                % (d, OMC, os.environ.get('LD_LIBRARY_PATH'), wall,
                   ', KILLED (process group) at the %d s cap' % cap if timed_out else ''))
        f.write(log)

    ver = re.search(r'OMC_VERSION (.*)', log)
    msl = re.search(r'MSL_LOADED (\S+) (\S+)', log)
    rec, rest = parse_record(log)
    msgs = []
    for m in re.finditer(r'^ERR (.*?)\nENDERR', log, re.M | re.S):
        msgs += split_errorstring(m.group(1))
    if rec is not None:
        mm = re.search(r'SIMERR (.*?)\nEND', rest, re.S)
        if mm:
            msgs += split_errorstring(mm.group(1))
        msgs += sim_messages(rec['messages'])
    st = parse_stats(rec['messages']) if rec else {'timers': {}}
    res_path = os.path.join(d, key + '_res.mat')
    cinfo = compiler_info(os.path.join(d, key + '.makefile'))
    metrics = {
        'tool': 'OpenModelica', 'tool_version': ver.group(1).strip() if ver else None,
        'msl_version': msl.group(2) if msl else None,
        'platform': platform_str(), 'compiler': cinfo.get('summary'),
        'test': cls, 'solver': solver, 'step': step,
        'tolerance': 1e-6, 'start_time': 0.0, 'stop_time': float(stop), 'output_interval': float(stop) / n,
        'translate_s': None, 'compile_s': None, 'simulate_wall_s': None, 'cpu_integration_s': None,
        'steps': None, 'f_evaluations': None, 'jacobian_evaluations': st.get('jacobian_evaluations'),
        'time_events': st.get('time_events'), 'state_events': st.get('state_events'), 'result_points': None,
        'outcome': 'failed', 'tool_messages': msgs[:20], 'recipe': None,
    }
    if rec:
        tr = [rec[k] for k in ('timeFrontend', 'timeBackend', 'timeSimCode', 'timeTemplates')]
        metrics['translate_s'] = round(sum(x for x in tr if x is not None), 4)
        metrics['compile_s'] = rec['timeCompile']
        metrics['simulate_wall_s'] = rec['timeSimulation']
    if solver == 'dassl':
        metrics['steps'] = st.get('steps_taken')
        metrics['f_evaluations'] = st.get('functionODE_calls')
    metrics['recipe'] = ('cd %s && %s run.mos  (Linux aarch64, environment unchanged); run.mos = %s ; script %s'
                         % (d, OMC, ' '.join(mos.splitlines()), os.path.abspath(__file__)))
    extra = {'omc_times': {k: rec[k] for k in rec if k.startswith('time')} if rec else None,
             'omc_log_stats': st, 'omc_process_wall_s': round(wall, 2), 'timed_out': timed_out,
             'cap_s': cap, 'numberOfIntervals': n, 'variableFilter': flt, 'result_file': res_path,
             'library': '%s (git archive of %s)' % (CFG['pkg'], commit_of_pkg()), 'messages_total': len(msgs),
             'compiler_detail': cinfo, 'library_binding': binding_info(d, key), 'machine_load_at_start': load}
    tm = st.get('timers', {})
    if 'total' in tm:
        extra['omc_stats_total_s'] = tm['total']
        extra['omc_stats_integration_s'] = round(tm['total'] - tm.get('pre-initialization', 0.0) - tm.get('initialization', 0.0), 6)
    time_reached = None
    if os.path.isfile(res_path):
        try:
            r = Mat4(res_path)
            extra['result_file_bytes'] = os.path.getsize(res_path)
            extra['result_truncated'] = r.truncated
            t = r.time
            time_reached = float(t[-1]) if len(t) else None
            metrics['result_points'] = int(len(t))
            missing = [s for s in sigs if not r.has(s)]
            extra['missing_signals'] = missing
            nint = int(round(stop / grid_dt))
            grid = np.arange(nint + 1) * grid_dt
            if time_reached is not None:
                grid = grid[grid <= time_reached + 1e-9]
            cols = [grid]
            for s in sigs:
                cols.append(resample(t, r.get(s), grid) if r.has(s) else np.full_like(grid, np.nan))
            arr = np.column_stack(cols)
            with open(os.path.join(out, key + '.csv'), 'w', encoding='utf-8', newline='\n') as f:
                f.write(','.join(['time'] + sigs) + '\n')
                np.savetxt(f, arr, delimiter=',', fmt='%.10g')
            with open(os.path.join(out, key + '_raw_points.txt'), 'w', encoding='utf-8', newline='\n') as f:
                f.write('%d\n' % len(t))
                f.write('stored points (rows of data_2) in %s, %d bytes%s\n'
                        % (res_path, os.path.getsize(res_path), ', TRUNCATED (run killed)' if r.truncated else ''))
                f.write('distinct time values %d; first %.17g, last %.17g; output interval %g, numberOfIntervals %d\n'
                        % (len(np.unique(t)), t[0], t[-1], float(stop) / n, n))
                f.write('variables in the file: %d (with parameters and aliases)\n' % len(r.names))
            keep = [i + 1 for i, s in enumerate(sigs) if s not in missing]
            extra['all_signals_finite'] = bool(np.all(np.isfinite(arr[:, keep])))
        except Exception as e:  # noqa
            extra['result_read_error'] = repr(e)
    extra['time_reached'] = time_reached
    ok = (rec is not None and 'The simulation finished successfully' in rec['messages'] and not timed_out
          and time_reached is not None and abs(time_reached - stop) < 1e-9 * max(1.0, stop)
          and not extra.get('missing_signals') and extra.get('all_signals_finite', False))
    if ok:
        metrics['outcome'] = 'ok'
    elif timed_out:
        extra['reason'] = 'wall-time cap of %d s reached (contract: a cap counts as failed); time reached %s s of %s s' % (
            cap, time_reached, stop)
    else:
        extra['reason'] = 'simulation did not finish successfully or a contract signal is missing/not finite (see tool_messages and logs/%s/log.txt)' % key
    metrics.update(extra)
    with open(os.path.join(out, key + '_metrics.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(metrics, f, indent=1)
    print('[%s] %s %s  translate %s compile %s simulate %s  points %s  events %s/%s  wall %.1f s' %
          (time.strftime('%H:%M:%S'), key, metrics['outcome'], metrics['translate_s'], metrics['compile_s'],
           metrics['simulate_wall_s'], metrics['result_points'], metrics['time_events'], metrics['state_events'],
           wall), flush=True)
    return metrics


# ---------------------------------------------------------------- static checks
def new_classes():
    lib = CFG['pkg']
    out = []
    for sub in (('Electrical', 'Controls', 'IEEE_CIGRE'), ('Tests', 'Controls', 'IEEE_CIGRE')):
        root = os.path.join(lib, *sub)
        for dp, dn, fn in sorted(os.walk(root)):
            dn.sort()
            rel = os.path.relpath(dp, lib)
            pkg = 'OpenIPSL.' + rel.replace('/', '.')
            if 'package.mo' not in fn:
                continue
            order = []
            po = os.path.join(dp, 'package.order')
            if os.path.isfile(po):
                order = [l.strip() for l in open(po, encoding='utf-8') if l.strip()]
            out.append(pkg)
            for c in order:
                if os.path.isfile(os.path.join(dp, c + '.mo')):
                    out.append(pkg + '.' + c)
    return out


def do_checks():
    classes = new_classes()
    for job, opt in (('checkModel', None), ('unitChecking', '--unitChecking')):
        d = os.path.join(CFG['build'], 'checks_' + job)
        mos = header()
        if opt:
            mos += ('print("SETOPT " + String(setCommandLineOptions("%s")) + "\\n"); '
                    'print("ERR " + getErrorString() + "\\nENDERR\\n");\n' % opt)
        mos += 'cd("%s");\n' % d
        for c in classes:
            mos += ('print("CHECK %s\\n"); print("RESULT " + checkModel(%s) + "\\n"); '
                    'print("CERR " + getErrorString() + "\\nENDCHECK\\n");\n' % (c, c))
        print('[%s] checks %s: %d classes' % (time.strftime('%H:%M:%S'), job, len(classes)), flush=True)
        log, wall, to = run_omc(d, mos, CFG['cap'])
        rdir = os.path.join(CFG['out'], 'logs', 'checks_' + job)
        os.makedirs(rdir, exist_ok=True)
        with open(os.path.join(rdir, 'run.mos'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(mos)
        with open(os.path.join(rdir, 'log.txt'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('$ cd %s && %s run.mos\n[%.2f s wall]\n\n' % (d, OMC, wall))
            f.write(log)
    parse_checks()


def parse_checks():
    """Parse logs/checks_<job>/log.txt into logs/checks_summary.json."""
    res = {}
    for job in ('checkModel', 'unitChecking'):
        p = os.path.join(CFG['out'], 'logs', 'checks_' + job, 'log.txt')
        log = open(p, encoding='utf-8').read()
        wall = float(re.search(r'\[([0-9.]+) s wall\]', log).group(1))
        per = []
        for m in re.finditer(r'^CHECK (\S+)\s*\n+RESULT (.*?)\n+CERR (.*?)\nENDCHECK', log, re.M | re.S):
            per.append({'class': m.group(1), 'result': m.group(2).strip(), 'messages': split_errorstring(m.group(3))})
        setopt = re.search(r'SETOPT (\S+)', log)
        hdr = [split_errorstring(m.group(1)) for m in re.finditer(r'^ERR (.*?)\nENDERR', log, re.M | re.S)]
        res[job] = {'wall_s': wall, 'setCommandLineOptions': setopt.group(1) if setopt else None, 'n': len(per),
                    'ok': sum(1 for q in per if 'completed successfully' in q['result']),
                    'with_messages': sum(1 for q in per if q['messages']),
                    'load_messages': [x for h in hdr for x in h], 'classes': per}
        print('%s: %d checked, %d completed successfully, %d with messages, %.1f s' %
              (job, len(per), res[job]['ok'], res[job]['with_messages'], wall), flush=True)
    with open(os.path.join(CFG['out'], 'logs', 'checks_summary.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1)


def do_extras():
    """The two auxiliary probes of the Windows record: the unit check can fail (UnitProbe.mo), and what the
    initialization/alias warnings name (-d=initialization,aliasConflicts, translateModel only)."""
    up = os.path.join(HERE, 'UnitProbe.mo')
    d = os.path.join(CFG['build'], 'unitprobe')
    mos = ('print("OMC_VERSION " + getVersion() + "\\n");\n'
           'loadModel(Modelica, {"4.0.0"}, requireExactVersion=true); getErrorString();\n'
           'loadFile("%s"); getErrorString();\n' % up +
           'cd("%s");\n' % d +
           'print("--- without --unitChecking\\n");\n'
           'print("CHECK WrongUnit: " + checkModel(UnitProbe.WrongUnit) + "\\n"); print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           'print("SETOPT " + String(setCommandLineOptions("--unitChecking")) + "\\n"); print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           'print("--- with --unitChecking: checkModel\\n");\n'
           'print("CHECK WrongUnit: " + checkModel(UnitProbe.WrongUnit) + "\\n"); print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           'print("CHECK WrongUnitDer: " + checkModel(UnitProbe.WrongUnitDer) + "\\n"); print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           'print("CHECK RightUnit: " + checkModel(UnitProbe.RightUnit) + "\\n"); print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           'print("--- with --unitChecking: instantiateModel\\n");\n'
           's := instantiateModel(UnitProbe.WrongUnit); print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           's := instantiateModel(UnitProbe.WrongUnitDer); print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           'print("--- with --unitChecking: translateModel\\n");\n'
           'print("TRANSLATE WrongUnitDer " + String(translateModel(UnitProbe.WrongUnitDer)) + "\\n"); print("ERR " + getErrorString() + "\\nENDERR\\n");\n')
    log, wall, _ = run_omc(d, mos, CFG['cap'])
    _save_log('unitprobe', d, mos, log, wall)
    tests = ['GFM.GFL_POCFault', 'GFM.GFL_FrequencyStep', 'GFM.GFL_VoltageStep', 'GFM.GFL_PowerRamp',
             'GFM.GFL_FaultPSCAD', 'GFM.GFM_EMTPFault', 'GFM.GFM_EMTPFull', 'GFM.Components.SmoothShortFault',
             'SCRX9.SCRX9', 'SCRX9.SCRX9_vs_SCRX']
    d = os.path.join(CFG['build'], 'init_diag')
    mos = ('print("OMC_VERSION " + getVersion() + "\\n");\n'
           'loadModel(Modelica, {"4.0.0"}, requireExactVersion=true); getErrorString();\n'
           'loadFile("%s/package.mo"); getErrorString();\n' % CFG['pkg'] +
           'cd("%s");\n' % d +
           'print("SETOPT " + String(setCommandLineOptions("-d=initialization,aliasConflicts")) + "\\n"); getErrorString();\n')
    for c in [T + '.' + x for x in tests] + ['OpenIPSL.Tests.Controls.PSSE.ES.SCRX']:
        mos += 'print("\\n=== %s\\n"); translateModel(%s); print(getErrorString() + "\\n");\n' % (c, c)
    log, wall, _ = run_omc(d, mos, CFG['cap'])
    _save_log('init_diag', d, mos, log, wall)
    # translateModel of all 12 tests without flags (the round-2 changes table: 12/12 true)
    d = os.path.join(CFG['build'], 'translate_all')
    mos = header() + 'cd("%s");\n' % d
    keys = []
    for k, r in RUNS.items():
        if r[1] not in keys:
            keys.append(r[1])
    for c in keys:
        mos += ('print("TRANSLATE %s " + String(translateModel(%s)) + "\\n"); '
                'print("TERR " + getErrorString() + "\\nENDT\\n");\n' % (c, c))
    log, wall, _ = run_omc(d, mos, CFG['cap'])
    _save_log('translate_all', d, mos, log, wall)
    summ = []
    for m in re.finditer(r'^TRANSLATE (\S+) (\S+)\s*\nTERR (.*?)\nENDT', log, re.M | re.S):
        summ.append({'class': m.group(1), 'result': m.group(2), 'messages': split_errorstring(m.group(3))})
    with open(os.path.join(CFG['out'], 'logs', 'translate_all', 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summ, f, indent=1)
    print('translateModel: %d of %d true' % (sum(1 for s in summ if s['result'] == 'true'), len(summ)))


def _save_log(name, d, mos, log, wall):
    rdir = os.path.join(CFG['out'], 'logs', name)
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, 'run.mos'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(mos)
    with open(os.path.join(rdir, 'log.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('$ cd %s && %s run.mos\n[%.2f s wall]\n\n' % (d, OMC, wall))
        f.write(log)
    print('[%s] %s done, %.1f s -> %s' % (time.strftime('%H:%M:%S'), name, wall, rdir), flush=True)


# ---------------------------------------------------------------- environment and run-time binding
def do_env():
    """Versions, compilers, the shipped libraries and what omc loads (logs/env.txt and logs/env.json)."""
    lib64 = os.path.join(CFG['pkg'], 'Resources', 'Library', LIBDIR)
    lines = []

    def add(title, text):
        lines.append('== ' + title)
        lines.append(text.rstrip())
    add('uname -a', sh(['uname', '-a']))
    add('/etc/os-release', open('/etc/os-release', encoding='utf-8').read() if os.path.isfile('/etc/os-release') else '?')
    add('board', board_model())
    add('platform', platform_str())
    add('free -h', sh(['free', '-h']))
    add('nproc', sh(['nproc']))
    add('ldd --version (glibc)', sh(['ldd', '--version']).splitlines()[0])
    add('omc --version (%s)' % OMC, sh([OMC, '--version']))
    add('omc realpath', os.path.realpath(OMC))
    add('dpkg -l (OpenModelica, clang)', '\n'.join(l for l in sh(['dpkg', '-l']).splitlines()
                                                     if re.search(r'^ii\s+(omc|omlibrary|libomc|openmodelica|clang)', l)))
    add('clang --version', sh(['clang', '--version']))
    add('clang realpath', os.path.realpath(shutil.which('clang') or 'clang'))
    add('gcc --version', sh(['gcc', '--version']).splitlines()[0])
    add('python', sys.version + ' numpy ' + np.__version__)
    add('environment', 'LD_LIBRARY_PATH=%s\nPATH=%s\nOPENMODELICALIBRARY=%s\nOPENMODELICAHOME=%s\nMODELICAPATH=%s' % (
        os.environ.get('LD_LIBRARY_PATH'), os.environ.get('PATH'), os.environ.get('OPENMODELICALIBRARY'),
        os.environ.get('OPENMODELICAHOME'), os.environ.get('MODELICAPATH')))
    add('package', '%s (commit %s)' % (CFG['pkg'], commit_of_pkg()))
    add('folders in Resources/Library', sh(['ls', '-la'] + [os.path.join(CFG['pkg'], 'Resources', 'Library')]))
    add('sha256 ' + LIBDIR, sh(['sha256sum'] + sorted(os.path.join(lib64, f) for f in os.listdir(lib64))))
    for so in sorted(os.listdir(lib64)):
        p = os.path.join(lib64, so)
        add('file ' + so, sh(['file', '-b', p]))
        add('readelf -d ' + so, sh(['readelf', '-d', p]))
        add('ldd ' + so, sh(['ldd', p]))
        dyn = sh(['nm', '-D', '--defined-only', p])
        add('exported symbols of ' + so, '\n'.join(l for l in dyn.splitlines() if l.strip()))
    d = os.path.join(CFG['build'], 'env')
    mos = (header() +
           'print("COMPILER " + getCompiler() + "\\n");\n'
           'print("TARGET " + getTarget() + "\\n");\n'
           'print("TEMP " + getTempDirectoryPath() + "\\n");\n'
           'print("CXXCOMPILER " + getCXXCompiler() + "\\n");\n'
           'print("CFLAGS " + getCFlags() + "\\n");\n'
           'print("LINKER " + getLinker() + "\\n");\n'
           'print("LINKERFLAGS " + getLinkerFlags() + "\\n");\n'
           'print("INSTALLDIR " + getInstallationDirectoryPath() + "\\n");\n'
           'print("MODELICAPATH " + getModelicaPath() + "\\n");\n'
           'print("MSL_FILE " + getSourceFile(Modelica) + "\\n");\n'
           'print("LIB_FILE " + getSourceFile(OpenIPSL) + "\\n");\n'
           'print("OPENIPSL_VERSION " + getVersion(OpenIPSL) + "\\n");\n'
           'print("ERR " + getErrorString() + "\\nENDERR\\n");\n'
           'getLoadedLibraries();\n')
    log, wall, _ = run_omc(d, mos, CFG['cap'])
    _save_log('env_omc', d, mos, log, wall)
    add('omc scripting (getCompiler, getCFlags, getLinker, MSL source file, loaded libraries)', log)
    os.makedirs(os.path.join(CFG['out'], 'logs'), exist_ok=True)
    with open(os.path.join(CFG['out'], 'logs', 'env.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def do_binding():
    """Run-time trace of a short SCRX9 and GFL_Fault simulate() run done by omc itself, with LD_DEBUG=libs and
    LD_DEBUG_OUTPUT=<run folder>/lddebug in the environment (one file per process), plus the same executable launched
    by hand without LD_LIBRARY_PATH: shows where ld.so found lib<Name>.so and which paths it tried (DT_RPATH entries,
    or LD_LIBRARY_PATH). Link time: the executable is relinked with the generated makefile and GNU ld's --verbose,
    which names every file the linker tried and the one it used."""
    res = {}
    for key, cls, stop, n, so in (('SCRX9', T + '.SCRX9.SCRX9', 0.1, 20, 'libSCRX9.so'),
                                  ('GFL_Fault', T + '.GFM.GFL_Fault', 0.001, 100, 'libGFM_GFL_IBR.so')):
        d = os.path.join(CFG['build'], 'binding_' + key)
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        simline = ('simulate(%s, startTime=0, stopTime=%s, numberOfIntervals=%d, tolerance=1e-06, method="%s", '
                   'fileNamePrefix="%s", outputFormat="mat", variableFilter="time", simflags="-lv=LOG_STATS");'
                   % (cls, repr(stop), n, 'dassl' if key == 'SCRX9' else 'euler', key))
        mos = header() + 'cd("%s");\n' % d + simline + '\nprint("SIMERR " + getErrorString() + "\\nEND\\n");\n'
        env = {'LD_DEBUG': 'libs', 'LD_DEBUG_OUTPUT': os.path.join(d, 'lddebug')}
        log, wall, _ = run_omc(d, mos, CFG['cap'], extra_env=env)
        rec, _ = parse_record(log)
        stem = so[3:-3]
        trace = []
        for fn in sorted(f for f in os.listdir(d) if f.startswith('lddebug.')):
            txt = open(os.path.join(d, fn), encoding='utf-8', errors='replace').read()
            lines = [re.sub(r'^\s*\d+:\s*', '', l).strip() for l in txt.splitlines()]
            i0 = next((i for i, l in enumerate(lines) if l.startswith('find library=' + so)), None)
            if i0 is None:
                continue
            blk = []
            for l in lines[i0:]:
                if l.startswith('find library=') and blk and not l.startswith('find library=' + so):
                    break
                if l.startswith(('find library=', 'search path=', 'trying file=')):
                    blk.append(l)
            sp = next((l for l in blk if l.startswith('search path=')), '')
            mm = re.search(r'\(([^)]*)\)\s*$', sp)
            init = [l for l in lines if l.startswith('calling init:') and stem in l]
            trace.append({'debug_file': fn, 'pid': fn.split('.')[-1], 'lines': blk[:60], 'calling_init': init,
                          'loaded_from': init[0].split(':', 1)[1].strip() if init else None,
                          'search_path_source': mm.group(1) if mm else None,
                          'LD_LIBRARY_PATH_in_trace': 'LD_LIBRARY_PATH' in sp,
                          'system_search_path_in_trace': 'system search path' in sp})
        # the executable by hand, without LD_LIBRARY_PATH: ldd, and a run to a tiny stop time
        exe = os.path.join(d, key)
        hand = {}
        if os.path.isfile(exe):
            e2 = dict(os.environ)
            e2.pop('LD_LIBRARY_PATH', None)
            try:
                p = subprocess.run([exe, '-override=stopTime=1e-6', '-lv=LOG_STATS'], cwd=d, env=e2, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, errors='replace', timeout=600)
                txt = p.stdout + '\n' + p.stderr
                hand = {'returncode': p.returncode,
                        'ldd_lines_for_library': [l.strip() for l in sh(['ldd', exe], env=e2).splitlines() if stem in l],
                        'cannot_open_shared_object': 'cannot open shared object' in txt,
                        'finished': 'The simulation finished successfully' in txt}
            except Exception as e:  # noqa
                hand = {'error': repr(e)}
        binding = binding_info(d, key)
        mk = sh(['make', '-f', key + '.makefile', 'omc_main_target', 'MODELICAUSERCFLAGS=-Wl,--verbose'], cwd=d)
        with open(os.path.join(d, 'link_trace.txt'), 'w', encoding='utf-8') as fh:
            fh.write(mk)
        link_lines = [l.strip() for l in mk.splitlines() if stem in l and l.lstrip().startswith(('attempt to open', 'opened script', 'found'))]
        res[key] = {'simulate_ok': bool(rec and 'The simulation finished successfully' in rec['messages']),
                    'omc_wall_s': round(wall, 2), 'library': so, 'processes_that_loaded_it': len(trace),
                    'trace': trace, 'executable_by_hand_without_LD_LIBRARY_PATH': hand,
                    'binding': binding, 'link_time_trace': link_lines,
                    'link_time_succeeded': [l for l in link_lines if l.endswith('succeeded')]}
        _save_log('binding_' + key, d, mos, log, wall)
    with open(os.path.join(CFG['out'], 'logs', 'binding.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1)
    for k, v in res.items():
        print('== %s: simulate ok %s; %s %s; loaded from %s' % (k, v['simulate_ok'], v['binding'].get('dt_tag'),
              v['binding'].get('dt_path'), [t['loaded_from'] for t in v['trace']]))
        print('   link time (ld --verbose): %s' % v['link_time_succeeded'][:2])
        print('   by hand: %s' % v['executable_by_hand_without_LD_LIBRARY_PATH'])


def do_timing(key, reps):
    """The same simulate() call without -lv=LOG_STATS (simflags="-s=<method>"), in <key>_nostats; adds nostats_* fields
    to the run's metrics file (median of the repetitions), the contract fields are left as they are."""
    test, cls, solver, stop, n, sigs, grid_dt, step = RUNS[key]
    d = os.path.join(CFG['build'], key + '_nostats')
    flt = regex_for(sigs)
    # simflags must not be empty: with simflags="" simulate() takes the flags of the model's
    # __OpenModelica_simulationFlags annotation (s="euler" in the GFM tests), which override method="dassl"
    simline = ('simulate(%s, startTime=0, stopTime=%s, numberOfIntervals=%d, tolerance=1e-06, method="%s", '
               'fileNamePrefix="%s", outputFormat="mat", variableFilter="%s", simflags="-s=%s");'
               % (cls, repr(float(stop)), n, solver, key, mos_str(flt), solver))
    mos = header() + 'cd("%s");\n' % d + simline + '\nprint("SIMERR " + getErrorString() + "\\nEND\\n");\n'
    sims, comps, loads = [], [], []
    rec, log, wall = None, '', 0.0
    for k in range(reps):
        loads.append(machine_load())
        log, wall, timed_out = run_omc(d, mos, CFG['cap'])
        rec, rest = parse_record(log)
        if rec:
            sims.append(rec['timeSimulation'])
            comps.append(rec['timeCompile'])
    rdir = os.path.join(CFG['out'], 'logs', key + '_nostats')
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, 'run.mos'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(mos)
    with open(os.path.join(rdir, 'log.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('$ cd %s && %s run.mos\n[%.2f s wall, last of %d]\n\n' % (d, OMC, wall, reps))
        f.write(log)
    prof = sorted(f for f in os.listdir(d) if '_prof.' in f)
    ok = bool(rec) and 'The simulation finished successfully' in rec['messages']
    p = os.path.join(CFG['out'], key + '_metrics.json')
    m = json.load(open(p, encoding='utf-8'))
    m['nostats_simulate_wall_s'] = float(np.median(sims)) if sims else None
    m['nostats_simulate_wall_s_all'] = sims
    m['nostats_compile_s_all'] = comps
    m['nostats_ok'] = ok
    m['nostats_prof_files'] = prof
    m['nostats_machine_load'] = [l['loadavg_1_5_15'] for l in loads]
    m['nostats_recipe'] = 'the same simulate() call with simflags="-s=%s" in %s (logs/%s_nostats)' % (solver, d, key)
    if rec:
        mm = re.search(r"simflags = '([^\n]*)'\"", log)
        m['nostats_simflags_used'] = mm.group(1) if mm else None
    if sims and ok:
        b = Mat4(os.path.join(d, key + '_res.mat'))
        a = Mat4(os.path.join(CFG['build'], key, key + '_res.mat'))
        same_t = len(a.time) == len(b.time) and bool(np.array_equal(a.time, b.time))
        m['nostats_same_result'] = bool(same_t and all(np.array_equal(a.get(s), b.get(s)) for s in sigs if a.has(s)))
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(m, f, indent=1)
    print('[%s] %s without LOG_STATS: ok %s, timeSimulation %s (LOG_STATS run %s), same result %s'
          % (time.strftime('%H:%M:%S'), key, ok, sims, m['simulate_wall_s'], m.get('nostats_same_result')), flush=True)


# ---------------------------------------------------------------- self-comparison against the Windows record
def load_csv(p):
    with open(p, encoding='utf-8') as fh:
        head = fh.readline().strip().split(',')
    a = np.loadtxt(p, delimiter=',', skiprows=1, ndmin=2)
    return head, a


def compare_raw(key, sigs, t_ev):
    """Raw stored points of both builds: same time vector? first difference? event instants."""
    lw = os.path.join(CFG['build'], key, key + '_res.mat')
    ww = os.path.join(CFG['win_build'], key, key + '_res.mat')
    if not (os.path.isfile(lw) and os.path.isfile(ww)):
        return {'available': False}
    a, b = Mat4(lw), Mat4(ww)
    ta, tb = a.time, b.time
    r = {'available': True, 'linux_points': int(len(ta)), 'windows_points': int(len(tb))}
    # duplicated instants = stored event pairs
    da = np.unique(ta[1:][np.diff(ta) == 0])
    db = np.unique(tb[1:][np.diff(tb) == 0])
    r['linux_event_instants'] = int(len(da))
    r['windows_event_instants'] = int(len(db))
    if len(da) < 20000 and len(db) < 20000:
        ra, rb = set(np.round(da, 9)), set(np.round(db, 9))
        r['event_instants_only_linux'] = sorted(float(x) for x in ra - rb)[:20]
        r['event_instants_only_windows'] = sorted(float(x) for x in rb - ra)[:20]
    # off-grid event instants (not a multiple of the DLL sample), compared to 1e-12 s
    step = 0.005 if key.startswith('SCRX9') else 1e-5
    def offgrid(dd):
        k = np.round(dd / step)
        return dd[np.abs(dd - k * step) > 1e-9]
    oa, ob = offgrid(da), offgrid(db)
    r['offgrid_event_instants_linux'] = [float('%.13g' % x) for x in oa[:20]]
    r['offgrid_event_instants_windows'] = [float('%.13g' % x) for x in ob[:20]]
    if len(oa) == len(ob):
        r['offgrid_event_instants_max_abs_diff'] = float(np.max(np.abs(oa - ob))) if len(oa) else 0.0
    if len(ta) == len(tb):
        r['same_length'] = True
        r['time_bitwise_equal'] = bool(np.array_equal(ta, tb))
        r['time_max_abs_diff'] = float(np.max(np.abs(ta - tb)))
        per = {}
        first_any = None
        for s in sigs:
            if not (a.has(s) and b.has(s)):
                continue
            ya, yb = a.get(s), b.get(s)
            dif = np.abs(ya - yb)
            nz = np.nonzero(dif > 0)[0]
            fi = float(ta[nz[0]]) if len(nz) else None
            pre = ta < (t_ev if t_ev is not None else np.inf)
            per[s] = {'max_abs_diff': float(np.max(dif)), 'first_time_not_bitwise_equal': fi,
                      'max_abs_diff_before_first_event': float(np.max(dif[pre])) if np.any(pre) else None,
                      'bitwise_equal_points_fraction': float(np.mean(dif == 0))}
            if fi is not None and (first_any is None or fi < first_any):
                first_any = fi
        r['signals'] = per
        r['first_time_any_signal_differs'] = first_any
    else:
        r['same_length'] = False
        n = min(len(ta), len(tb))
        neq = np.nonzero(ta[:n] != tb[:n])[0]
        r['first_index_time_differs'] = int(neq[0]) if len(neq) else n
        if len(neq):
            i = int(neq[0])
            r['first_time_differs'] = {'linux': float(ta[i]), 'windows': float(tb[i])}
    return r


def do_compare():
    if not CFG['win_record'] or not os.path.isdir(CFG['win_record']):
        print('compare skipped: no Windows record (set --win-record, or WINDOWS_RECORD_ROOT in site.env)')
        return
    rows, out = [], {}
    for key, (test, cls, solver, stop, n, sigs, grid_dt, step) in RUNS.items():
        lp = os.path.join(CFG['out'], key + '.csv')
        wp = os.path.join(CFG['win_record'], key + '.csv')
        if not (os.path.isfile(lp) and os.path.isfile(wp)):
            out[key] = {'available': False}
            continue
        hl, al = load_csv(lp)
        hw, aw = load_csv(wp)
        t_ev = FIRST_EVENT.get(key)
        r = {'headers_equal': hl == hw, 'rows_linux': int(al.shape[0]), 'rows_windows': int(aw.shape[0])}
        nrow = min(al.shape[0], aw.shape[0])
        r['grid_max_abs_diff'] = float(np.max(np.abs(al[:nrow, 0] - aw[:nrow, 0])))
        tt = al[:nrow, 0]
        per = {}
        for j, s in enumerate(hl[1:], start=1):
            if s not in hw:
                continue
            jw = hw.index(s)
            yl, yw = al[:nrow, j], aw[:nrow, jw]
            dif = np.abs(yl - yw)
            i = int(np.argmax(dif))
            scale = float(np.max(np.abs(yw)))
            pre = tt < (t_ev if t_ev is not None else np.inf)
            thr = 1e-6 * max(scale, 1e-12)
            big = np.nonzero(dif > thr)[0]
            per[s] = {'max_abs_diff': float(dif[i]), 'at_time': float(tt[i]), 'max_abs_windows': scale,
                      'rel_to_max_abs': float(dif[i] / scale) if scale > 0 else None,
                      'max_abs_diff_before_first_event': float(np.max(dif[pre])) if np.any(pre) else None,
                      'first_time_diff_above_1e-6_of_max': float(tt[big[0]]) if len(big) else None,
                      'final_linux': float(yl[-1]), 'final_windows': float(yw[-1])}
        r['signals'] = per
        r['first_event_s'] = t_ev
        try:
            r['raw'] = compare_raw(key, sigs, t_ev)
        except Exception as e:  # noqa
            r['raw'] = {'error': repr(e)}
        # metrics side by side
        ml = json.load(open(os.path.join(CFG['out'], key + '_metrics.json'), encoding='utf-8'))
        mw = json.load(open(os.path.join(CFG['win_record'], key + '_metrics.json'), encoding='utf-8'))
        mk = ['outcome', 'time_events', 'state_events', 'result_points', 'steps', 'f_evaluations', 'jacobian_evaluations',
              'translate_s', 'compile_s', 'simulate_wall_s', 'nostats_simulate_wall_s', 'omc_stats_integration_s']
        r['metrics'] = {k: {'linux': ml.get(k), 'windows': mw.get(k)} for k in mk}
        r['metrics']['error_test_failures'] = {'linux': ml.get('omc_log_stats', {}).get('error_test_failures'),
                                               'windows': mw.get('omc_log_stats', {}).get('error_test_failures')}
        out[key] = r
        worst = max(per.items(), key=lambda kv: (kv[1]['rel_to_max_abs'] or 0.0))
        rows.append((key, r, worst))
        print('%-32s headers %s rows %d/%d  worst rel %s = %.3g (abs %.3g at %.6g s); pre-event max abs %s; raw same length %s, first diff %s'
              % (key, r['headers_equal'], r['rows_linux'], r['rows_windows'], worst[0], worst[1]['rel_to_max_abs'] or 0,
                 worst[1]['max_abs_diff'], worst[1]['at_time'],
                 '%.3g' % max((v['max_abs_diff_before_first_event'] or 0.0) for v in per.values()),
                 r['raw'].get('same_length'), r['raw'].get('first_time_any_signal_differs')), flush=True)
    with open(os.path.join(CFG['out'], 'logs', 'self_comparison.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1)
    write_compare_md(out)


def write_compare_md(out):
    """Markdown tables of the self-comparison (logs/self_comparison.md)."""
    cnt = ['time_events', 'state_events', 'result_points', 'steps', 'f_evaluations', 'jacobian_evaluations',
           'error_test_failures']
    t1 = ['| Run | headers, grid | raw time vector | off-grid event instants | counts equal (%s) | largest relative raw difference (signal: abs / max abs) | largest raw difference before the first disturbance (signal: abs) | first instant not bitwise equal (s) |' % ', '.join(cnt),
          '|---|---|---|---|---|---|---|---|']
    t2 = ['| Run | signal | CSV grid: max abs diff | at (s) | max abs (Windows) | relative | raw points: max abs diff | before the first disturbance | final Pi | final Windows |',
          '|---|---|---|---|---|---|---|---|---|---|']
    key_sig = re.compile(r'(out\[1[012]\]|grid_sensor_a\.|sCRX9\.EFD|sCRX\.EFD|GEN1\.v|gENROU\.w|transformer\.Ad\.|smoothShortFault\.A\.v|currentSensor2)')
    for key, r in out.items():
        if not r.get('signals'):
            t1.append('| %s | not compared | | | | | | |' % key)
            continue
        raw = r.get('raw', {})
        rs = raw.get('signals', {})
        eq = [k for k in cnt if r['metrics'][k]['linux'] == r['metrics'][k]['windows']]
        ne = ['%s %s/%s' % (k, r['metrics'][k]['linux'], r['metrics'][k]['windows']) for k in cnt if k not in eq]
        worst = None
        for s, v in rs.items():
            sc = r['signals'][s]['max_abs_windows']
            rel = v['max_abs_diff'] / sc if sc > 0 else 0.0
            if s.endswith('VabcSum.y'):
                continue   # a sum that is zero by construction; its relative difference is meaningless
            if worst is None or rel > worst[1]:
                worst = (s, rel, v['max_abs_diff'], sc)
        pre = max(((s, v['max_abs_diff_before_first_event']) for s, v in rs.items()
                   if v['max_abs_diff_before_first_event'] is not None), key=lambda x: x[1], default=None)
        tvec = ('%d points, bitwise equal' % raw['linux_points'] if raw.get('time_bitwise_equal') else
                '%d/%d points, max diff %.2g s' % (raw.get('linux_points', 0), raw.get('windows_points', 0),
                                                   raw.get('time_max_abs_diff', float('nan'))))
        og = raw.get('offgrid_event_instants_linux', [])
        ogd = raw.get('offgrid_event_instants_max_abs_diff')
        t1.append('| %s | %s, %d rows | %s | %d, max diff %s s | %s | %s | %s | %s |' % (
            key, 'same' if r['headers_equal'] and r['grid_max_abs_diff'] == 0 else 'DIFFER', r['rows_linux'], tvec,
            len(og), '%.2g' % ogd if ogd is not None else '-', 'all' if not ne else 'not: ' + '; '.join(ne),
            '%s: %.2g / %.4g (%.1e)' % (worst[0], worst[2], worst[3], worst[1]) if worst else '-',
            '%s: %.2g' % pre if pre else '-', raw.get('first_time_any_signal_differs')))
        for s, v in r['signals'].items():
            if not key_sig.search(s):
                continue
            w = rs.get(s, {})
            t2.append('| %s | `%s` | %.3g | %.6g | %.5g | %s | %s | %s | %.10g | %.10g |' % (
                key, s, v['max_abs_diff'], v['at_time'], v['max_abs_windows'],
                '%.1e' % v['rel_to_max_abs'] if v['rel_to_max_abs'] is not None else '-',
                '%.3g' % w['max_abs_diff'] if w else '-',
                '%.3g' % w['max_abs_diff_before_first_event'] if w and w.get('max_abs_diff_before_first_event') is not None else '-',
                v['final_linux'], v['final_windows']))
    txt = ('# Self-comparison: OpenModelica on the Raspberry Pi (Linux aarch64) against the Windows round-2 record\n\n'
           'Pi record: %s. Windows record: %s (CSV, metrics). Windows raw result files: %s.\n\n'
           '## Per run\n\n%s\n\n## Key signals\n\n%s\n' % (CFG['out'], CFG['win_record'], CFG['win_build'],
                                                          '\n'.join(t1), '\n'.join(t2)))
    with open(os.path.join(CFG['out'], 'logs', 'self_comparison.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)


def table():
    rows = []
    for key in RUNS:
        p = os.path.join(CFG['out'], key + '_metrics.json')
        if not os.path.isfile(p):
            rows.append('| %s | not run |' % key)
            continue
        m = json.load(open(p, encoding='utf-8'))

        def f(v):
            return '-' if v is None else ('%g' % v if isinstance(v, float) else str(v))
        rows.append('| %s | %s | %s | %s | %.3f | %.2f | %.3f | %.3f | %.3f | %s | %s | %s | %s | %s | %s | %.1f |' % (
            key, m['outcome'], f(m['step']), m.get('numberOfIntervals'), m['translate_s'] or float('nan'),
            m['compile_s'] or float('nan'), m['simulate_wall_s'] or float('nan'),
            m.get('nostats_simulate_wall_s') or float('nan'), m.get('omc_stats_integration_s') or float('nan'),
            f(m['steps']), f(m['f_evaluations']), f(m['jacobian_evaluations']), f(m['time_events']),
            f(m['state_events']), f(m['result_points']), m.get('omc_process_wall_s') or float('nan')))
    txt = ('| Run | outcome | step (s) | intervals | translate (s) | compile (s) | simulate wall (s) | '
           'simulate wall without LOG_STATS, median (s) | LOG_STATS timer total - init (s) | steps | f-evals | Jacobians | '
           'time events | state events | result points | omc process wall (s) |\n' + '|' + '---|' * 16 + '\n'
           + '\n'.join(rows) + '\n')
    os.makedirs(os.path.join(CFG['out'], 'logs'), exist_ok=True)
    with open(os.path.join(CFG['out'], 'logs', 'runs_table.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    print(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pkg', default=os.environ.get('OIPSL_PKG', ''),
                    help='the exported package .../OpenIPSL (tests/export_package.sh); default $OIPSL_PKG')
    ap.add_argument('--build', default=os.path.join(HOME, 'arm-verify', 'build', 'om_runs'))
    ap.add_argument('--out', default=os.path.join(HOME, 'arm-verify', 'raw', 'openmodelica', 'record'))
    rec_root = os.environ.get('WINDOWS_RECORD_ROOT', '')
    raw_root = os.environ.get('WINDOWS_RAW_ROOT', '')
    ap.add_argument('--win-record', default=os.path.join(rec_root, 'openmodelica') if rec_root else '',
                    help='Windows round-2 OpenModelica record; default $WINDOWS_RECORD_ROOT/openmodelica')
    ap.add_argument('--win-build', default=os.path.join(raw_root, 'openmodelica') if raw_root else '',
                    help='Windows round-2 OpenModelica build tree (raw .mat); default $WINDOWS_RAW_ROOT/openmodelica')
    ap.add_argument('--reps', type=int, default=int(os.environ.get('OMC_TIMING_REPS', '3')))
    ap.add_argument('--cap', type=float, default=1800.0)
    ap.add_argument('command')
    ap.add_argument('keys', nargs='*')
    a = ap.parse_args()
    CFG.update(pkg=os.path.abspath(a.pkg), build=os.path.abspath(a.build), out=os.path.abspath(a.out),
               win_record=a.win_record, win_build=a.win_build, reps=a.reps, cap=a.cap)
    if not os.path.isfile(os.path.join(CFG['pkg'], 'package.mo')):
        sys.exit('no package.mo in --pkg %s' % CFG['pkg'])
    os.makedirs(CFG['build'], exist_ok=True)
    os.makedirs(os.path.join(CFG['out'], 'logs'), exist_ok=True)
    keys = list(RUNS) if a.keys == ['all'] else a.keys
    for k in keys:
        if k not in RUNS:
            sys.exit('unknown run key %s; keys: %s' % (k, ', '.join(RUNS)))
    if a.command == 'env':
        do_env()
    elif a.command == 'checks':
        do_checks()
    elif a.command == 'parsechecks':
        parse_checks()
    elif a.command == 'extras':
        do_extras()
    elif a.command == 'binding':
        do_binding()
    elif a.command == 'run':
        for k in keys:
            do_run(k)
    elif a.command == 'timing':
        for k in keys:
            do_timing(k, CFG['reps'])
    elif a.command == 'compare':
        do_compare()
    elif a.command == 'table':
        table()
    else:
        sys.exit('unknown command ' + a.command)


if __name__ == '__main__':
    main()
