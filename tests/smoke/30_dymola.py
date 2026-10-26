"""Smoke test 30 (normal user): Dymola for Linux, headless through the Dymola Python interface, checks the
licence, builds and simulates the SCRX9 DLL test with the shipped libSCRX9.so, and shows how dymosim finds
the library (dsmodel.c library path entries, RUNPATH, ldd).

Usage (the kit's Python environment has the Dymola wheel):
    /opt/openipsl-kit/venv-dymola/bin/python -I tests/smoke/30_dymola.py <package dir .../OpenIPSL> [<site.env>]
"""
import os
import re
import shutil
import subprocess
import sys
import time

from dymola.dymola_interface import DymolaInterface

pkg = os.path.realpath(sys.argv[1])
site = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'site.env')
env = {}
for line in open(site, encoding='utf-8'):
    m = re.match(r'\s*([A-Za-z_]\w*)=(.*)$', line)
    if m:
        env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
dymola_dir = env.get('DYMOLA_DIR', '/opt/dymola-2026xRefresh1-x86_64')
model = 'OpenIPSL.Tests.Controls.IEEE_CIGRE.SCRX9.SCRX9'
work = os.path.expanduser('~/cigre_verify/smoke/dymola')
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)

exe = os.path.join(dymola_dir, 'bin64', 'dymola.sh')
if not os.path.exists(exe):
    exe = '/usr/local/bin/dymola'
print('Dymola start script:', exe)
t0 = time.perf_counter()
d = DymolaInterface(dymolapath=exe, showwindow=False)
print('started in %.1f s' % (time.perf_counter() - t0))
ok_all = True
try:
    print('DymolaVersion:', d.DymolaVersion())
    d.ExecuteCommand('Advanced.UI.SkipMessageDialogs = true')
    print('RequestOption("Standard"):', d.ExecuteCommand('RequestOption("Standard")'))
    d.cd(work)
    print('openModel:', d.openModel(os.path.join(pkg, 'package.mo'), changeDirectory=False))
    t0 = time.perf_counter()
    ok = d.simulateModel(model, startTime=0, stopTime=10, numberOfIntervals=2000, tolerance=1e-6,
                         method='Dassl', resultFile='SCRX9')
    print('simulateModel: %s in %.1f s' % (ok, time.perf_counter() - t0))
    if not ok:
        ok_all = False
        print(d.getLastErrorLog())
    else:
        r = d.readTrajectory(os.path.join(work, 'SCRX9.mat'), ['sCRX9.EFD'], d.readTrajectorySize(os.path.join(work, 'SCRX9.mat')))
        print('EFD_0 %.8f EFD_10 %.8f' % (r[0][0], r[0][-1]))
finally:
    d.close()

print('== how dymosim finds libSCRX9.so')
src = os.path.join(work, 'dsmodel.c')
if os.path.exists(src):
    for line in open(src, encoding='utf-8', errors='replace'):
        if 'dllLibraryPath' in line or ('SCRX9' in line and ('.so' in line or 'linux64' in line)):
            print('dsmodel.c:', line.strip()[:220])
for f in ('dsbuild.log', 'dslog.txt'):
    p = os.path.join(work, f)
    if os.path.exists(p):
        for line in open(p, encoding='utf-8', errors='replace'):
            if re.search(r'linux64|rpath|SCRX9|error', line, re.I):
                print(f + ':', line.strip()[:220])
dymosim = os.path.join(work, 'dymosim')
if os.path.exists(dymosim):
    print(subprocess.run(['bash', '-c', "readelf -d dymosim | grep -E 'NEEDED|RUNPATH|RPATH'; ldd dymosim | grep -E 'SCRX9|not found'"],
                         cwd=work, capture_output=True, text=True).stdout)
sys.exit(0 if ok_all else 1)
