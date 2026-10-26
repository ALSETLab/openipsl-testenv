"""wsm_run_linux.py - one contract run of the IEEE/CIGRE DLL verification in Wolfram System Modeler 15.0 for Linux,
headlessly, through the standalone kernel (WSMKernelX) and the simulation executable it builds; writes the run's
record in the data contract of the Windows rounds (report/verification_round2/<tool>/), so that the synthesis can
put the Linux and the Windows numbers side by side.

    /usr/bin/python3 -I wsm_run_linux.py --spec runs.json --run <run id> --pkg <.../OpenIPSL> --out <record dir>
                     --work <build root> [--compiler /opt/openipsl-kit/bin/g++-nopie | default]
                     [--timeout 1800] [--no-count-events] [--progress-log] [--wsm-home <dir>]

Port of the kernel route of report/verification_round2/systemmodeler/scripts/wsm_run.py (Windows). Only the
platform parts changed:
  1. <work>/<Test>__<solver>/ is made empty; ModelicaPath.txt names System Modeler's own Modelica Standard Library
     4.0.0 and SystemModelerExtras (<wsm>/L/...).
  2. build.mos: setStopOnError(false); setTempDirectoryPath; setCompilerPath(<compiler>) unless --compiler default;
     loadLibrary(Modelica); loadFile(<pkg>/package.mo); buildModel(<model>, fileNamePrefix=...). The default compiler
     is the kit's /opt/openipsl-kit/bin/g++-nopie: Ubuntu's g++ links position-independent executables by default
     and the kernel's external-function evaluator links lib/linux64/libserializer.a, which is not PIC (measured
     2026-10-25, provision/30_systemmodeler.sh). "--compiler default" leaves the kernel's own choice ("g++" from
     PATH) to show that failure. WSMKernelX build.mos is timed; "Step 4 of 4" in <Short>_build.log splits
     translate_s from compile_s, as on Windows. While the kernel compiles, <Short>.ninja (the kernel deletes it at
     the end) is copied to keep_<Short>.ninja: it holds the exact compile and link lines.
  3. The .sim written by buildModel is rewritten exactly as on Windows (end, method, stepSize, outputSteps=0,
     tolerance, resultFilePath, StopAtMaxNoOutputPoints).
  4. <Short>.exe -f <Short>.sim -r <res>.mat, stdout to sim_out.txt and stderr to sim_err.txt (one shared file
     loses the stderr text on Linux, probes.sh P5). The executable has no RUNPATH/RPATH and does not find lib<Name>.so by
     itself: the directories of the .sim's <ExternalLibraries> are put on LD_LIBRARY_PATH (on Windows the same
     directories go on PATH). readelf -d and ldd (without and with that LD_LIBRARY_PATH) are recorded.
  5. Unless --no-count-events: the executable once more with -v4 -ls event, streamed and counted, not timed.
  6. The .mat is read and resampled to the contract grid exactly as on Windows; writes <Test>__<solver>.csv,
     _metrics.json (contract fields + platform + compiler + wsm_* extras), _raw_points.txt, and logs/<tag>/.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

import numpy as np

NOPIE = "/opt/openipsl-kit/bin/g++-nopie"
SAME_INSTANT = 1e-12


# ----------------------------------------------------------------------------------------------- environment
def os_release():
    info = {}
    try:
        for line in open("/etc/os-release", encoding="utf-8"):
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                info[k] = v.strip('"')
    except OSError:
        pass
    return info


def platform_string():
    rel = os_release().get("PRETTY_NAME", "Linux").replace(" LTS", "")
    libc = platform.libc_ver()[1] or "?"
    return "linux64, %s, glibc %s" % (rel, libc)


def run_text(cmd, env=None, timeout=60):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=timeout)
        return p.stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired) as e:
        return "<%s>" % e


def compiler_info(compiler):
    """Name and version of the C/C++ compiler the kernel really runs."""
    if compiler == "default":
        gxx = shutil.which("g++") or "g++"
        ver = run_text([gxx, "--version"]).splitlines()[0]
        return {"name": "g++ (the kernel's default: \"g++\" from PATH = %s, links PIE executables)" % os.path.realpath(gxx),
                "version": ver, "path": None}
    ver = run_text(["/usr/bin/g++", "--version"]).splitlines()[0]
    return {"name": "g++ through %s (runs /usr/bin/g++, adds -no-pie when linking an executable)" % compiler,
            "version": ver, "path": compiler}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ----------------------------------------------------------------------------------------------- MAT v4 reader
def read_mat4(path):
    """Return {name: (array or memmap)} for every matrix of a MAT v4 file (little endian, double/single/int32/char)."""
    out = {}
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        pos = 0
        while pos + 20 <= size:
            fh.seek(pos)
            hdr = np.frombuffer(fh.read(20), dtype="<i4")
            mopt, mrows, ncols, imagf, namlen = [int(x) for x in hdr]
            name = fh.read(namlen).rstrip(b"\x00").decode("latin-1")
            p = (mopt // 10) % 10
            dtype = {0: "<f8", 1: "<f4", 2: "<i4", 3: "<i2", 4: "<u2", 5: "<u1"}[p]
            itemsize = np.dtype(dtype).itemsize
            start = pos + 20 + namlen
            count = mrows * ncols
            if count:
                arr = np.memmap(path, dtype=dtype, mode="r", offset=start, shape=(ncols, mrows))
            else:
                arr = np.zeros((ncols, mrows), dtype=dtype)
            out[name] = arr
            pos = start + count * itemsize * (2 if imagf else 1)
    return out


class Result:
    """Dymola result format 1.1 as System Modeler writes it (Aclass, name, description, dataInfo, data_1, data_2)."""

    def __init__(self, path):
        m = read_mat4(path)
        a = np.asarray(m["Aclass"])
        rows_t = ["".join(chr(int(c)) for c in a[:, i]).rstrip() for i in range(a.shape[1])]
        rows_n = ["".join(chr(int(c)) for c in a[i, :]).rstrip() for i in range(a.shape[0])]
        trans = any(r.startswith("binTrans") for r in rows_t + rows_n)
        self.trans = trans
        nm = np.asarray(m["name"])
        if trans:
            self.names = ["".join(chr(int(c)) for c in nm[i, :]).rstrip("\x00 ").strip() for i in range(nm.shape[0])]
            info = np.asarray(m["dataInfo"])
            self.d2 = m["data_2"]
            self.d1 = np.asarray(m["data_1"])
        else:
            self.names = ["".join(chr(int(c)) for c in nm[:, j]).rstrip("\x00 ").strip() for j in range(nm.shape[1])]
            info = np.asarray(m["dataInfo"]).T
            self.d2 = np.asarray(m["data_2"]).T
            self.d1 = np.asarray(m["data_1"]).T
        self.info = info
        self.index = {n: i for i, n in enumerate(self.names)}
        self.time = np.array(self.d2[:, 0], dtype=float)

    def has(self, name):
        return name in self.index

    def get_many(self, names):
        cols, specs = [], []
        for n in names:
            i = self.index[n]
            mat, col = int(self.info[i, 0]), int(self.info[i, 1])
            sign = 1.0 if col > 0 else -1.0
            col = abs(col) - 1
            specs.append((mat, col, sign))
            if mat in (0, 2):
                cols.append(col)
        uniq = sorted(set(cols))
        block = np.array(self.d2[:, uniq], dtype=float) if uniq else None
        pos = {c: k for k, c in enumerate(uniq)}
        res = []
        for (mat, col, sign) in specs:
            if mat == 1:
                res.append(np.full_like(self.time, sign * float(self.d1[0, col] if self.d1.shape[0] else self.d1[col])))
            else:
                res.append(sign * block[:, pos[col]])
        return res


def resample(t, v, grid):
    """Linear interpolation on the grid that respects events (identical to the Windows wsm_run.py).

    Stored times closer than SAME_INSTANT form one instant (an event stores the values before and after it at the
    same time). A grid point on an instant takes the last value stored there (after the event); a grid point between
    two instants interpolates from the last value of the left instant to the FIRST value of the right one (before
    its event), so that no grid point before an event sees the jump.
    """
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float)
    new = np.ones(len(t), dtype=bool)
    new[1:] = (t[1:] - t[:-1]) > SAME_INSTANT
    first = np.flatnonzero(new)
    last = np.append(first[1:] - 1, len(t) - 1)
    u = t[first]
    k = np.searchsorted(u, grid, side="right") - 1
    n = len(u)
    k = np.clip(k, 0, n - 1)
    k1 = np.minimum(k + 1, n - 1)
    a = v[last[k]]
    b = v[first[k1]]
    du = u[k1] - u[k]
    frac = np.where(du > 0, (grid - u[k]) / np.where(du > 0, du, 1.0), 0.0)
    out = a + (b - a) * frac
    on_right = (k + 1 < n) & (np.abs(u[k1] - grid) <= SAME_INSTANT)
    out = np.where(on_right, v[last[k1]], out)
    on_left = np.abs(grid - u[k]) <= SAME_INSTANT
    out = np.where(on_left, a, out)
    return out


# ----------------------------------------------------------------------------------------------- build
MSG_START = re.compile(r"^(\[[^\]]*\]\s*)?(Notification|Warning|Error|Internal error)\b")


def kernel_messages(text):
    """The kernel's Notification/Warning/Error messages (as on Windows) plus, in their place, every failed build of
    the external-function evaluator (from "FAILED:" to "ninja: build stopped"), verbatim."""
    msgs, cur, ev = [], None, None
    for line in text.splitlines():
        if ev is not None:
            ev.append(line)
            if line.startswith("ninja: build stopped"):
                msgs.append("\n".join(ev))
                ev = None
            continue
        if line.startswith("FAILED:"):
            if cur:
                msgs.append("\n".join(cur))
                cur = None
            ev = [line]
            continue
        if MSG_START.match(line):
            if cur:
                msgs.append("\n".join(cur))
            cur = [line]
        elif cur is not None and line.strip() and not re.match(r"^(true|false|\{.*\})$", line.strip()):
            cur.append(line)
        else:
            if cur:
                msgs.append("\n".join(cur))
            cur = None
    if ev:
        msgs.append("\n".join(ev))
    if cur:
        msgs.append("\n".join(cur))
    return msgs


def evaluator_lines(text):
    """Every line of the kernel output about the external-function evaluator (builds, link errors, evaluations)."""
    keep = []
    for line in text.splitlines():
        if (re.search(r"evaluator|External evaluation|FAILED:|/usr/bin/ld|collect2|ninja: build stopped", line)
                and line.strip()):
            keep.append(line)
    return keep


def build(work, pkg_mo, model, short, timeout, wsm, compiler, extra_files=()):
    with open(os.path.join(work, "ModelicaPath.txt"), "w", encoding="utf-8") as fh:
        fh.write(os.path.join(wsm, "L", "Modelica 4.0.0") + "\n" + os.path.join(wsm, "L", "SystemModelerExtras") + "\n")
    mos = ["setStopOnError(false);", 'setTempDirectoryPath("%s");' % work]
    if compiler != "default":
        mos.append('setCompilerPath("%s");' % compiler)
    mos += ["loadLibrary(Modelica);", 'loadFile("%s");' % pkg_mo]
    mos += ['loadFile("%s");' % f for f in extra_files]
    mos.append('buildModel(%s, fileNamePrefix="%s/%s");' % (model, work, short))
    with open(os.path.join(work, "build.mos"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(mos) + "\n")
    kernel = os.path.join(wsm, "bin", "WSMKernelX")
    blog = os.path.join(work, short + "_build.log")
    ninja = os.path.join(work, short + ".ninja")
    keep_ninja = os.path.join(work, "keep_%s.ninja" % short)
    kout = os.path.join(work, "kernel_out.txt")
    kerr = os.path.join(work, "kernel_err.txt")
    t0 = time.perf_counter()
    t_step4 = None
    with open(kout, "wb") as fo, open(kerr, "wb") as fe:
        p = subprocess.Popen([kernel, "build.mos"], cwd=work, stdout=fo, stderr=fe)
        capped = False
        while p.poll() is None:
            if t_step4 is None and os.path.exists(blog):
                try:
                    if "Step 4 of 4" in open(blog, encoding="utf-8", errors="replace").read():
                        t_step4 = time.perf_counter()
                except OSError:
                    pass
            if os.path.exists(ninja):
                try:
                    data = open(ninja, "rb").read()
                    if data and b"default defaultbuild" in data:
                        with open(keep_ninja, "wb") as fk:
                            fk.write(data)
                except OSError:
                    pass
            if time.perf_counter() - t0 > timeout:
                p.kill()
                capped = True
                break
            time.sleep(0.05)
        p.wait()
    t1 = time.perf_counter()
    err = open(kerr, encoding="utf-8", errors="replace").read()
    text = open(kout, encoding="utf-8", errors="replace").read() + (os.linesep + err if err.strip() else "")
    exe = os.path.join(work, short + ".exe")
    ok = os.path.exists(exe) and not capped
    return {
        "ok": ok, "capped": capped, "total_s": t1 - t0, "returncode": p.returncode,
        "translate_s": (t_step4 - t0) if t_step4 else (t1 - t0),
        "compile_s": (t1 - t_step4) if t_step4 else None,
        "messages": kernel_messages(text), "kernel_out": text, "mos": "\n".join(mos),
        "kernel": kernel, "keep_ninja": keep_ninja if os.path.exists(keep_ninja) else None,
        "kernel_stderr": err,
    }


def link_line(ninja_path, short):
    """The link command of <Short>.exe as the kernel's ninja file builds it."""
    if not ninja_path:
        return None
    text = open(ninja_path, encoding="utf-8", errors="replace").read()
    var = dict(re.findall(r"^(\w+) = (.*)$", text, re.M))
    m = re.search(r"^build %s\.exe: (\w+) (.*)$" % re.escape(short), text, re.M)
    if not m:
        return None
    rule, objs = m.group(1), m.group(2)
    rm = re.search(r"^rule %s\n  command = (.*)$" % re.escape(rule), text, re.M)
    cmd = rm.group(1) if rm else "$CXX $linkflags $in $linklibs -o $out"
    vals = dict(var)
    vals["in"] = objs
    vals["out"] = short + ".exe"
    return re.sub(r"\$(\w+)", lambda mm: vals.get(mm.group(1), mm.group(0)), cmd)


# ----------------------------------------------------------------------------------------------- simulate
def rewrite_sim(sim, stop, method, step, tol, result, point_limit):
    text = open(sim, encoding="utf-8").read()
    shutil.copyfile(sim, sim + ".orig")
    m = re.search(r"<simulation [^>]*>", text)
    head = m.group(0)
    new = re.sub(r'\s(stepSize|tolerance|outputSteps|end|method|resultFilePath)="[^"]*"', "", head)
    attrs = 'end="%s" tolerance="%s" outputSteps="0" stepSize="%s" method="%s" resultFilePath="%s" ' % (
        repr(float(stop)), repr(float(tol)), repr(float(step)), method, result)
    new = new.replace("<simulation ", "<simulation " + attrs, 1)
    text = text.replace(head, new, 1)
    text, n = re.subn(r'(<Option name="StopAtMaxNoOutputPoints">\s*<OptionValue name="limit" value=")[^"]*(")',
                      r"\g<1>%d\g<2>" % point_limit, text)
    open(sim, "w", encoding="utf-8").write(text)
    return head, new, n


def sim_libs(sim):
    """(directories, library file names) of the .sim's <ExternalLibraries>."""
    text = open(sim, encoding="utf-8").read()
    block = re.search(r"<ExternalLibraries>(.*?)</ExternalLibraries>", text, re.S)
    dirs, names, lines = [], [], []
    if block:
        for m in re.finditer(r"<Library\b[^>]*>", block.group(1)):
            lines.append(m.group(0).strip())
            pm = re.search(r'\bpath="([^"]*)"', m.group(0))
            nm = re.search(r'\bname="([^"]*)"', m.group(0))
            if pm and pm.group(1) not in dirs:
                dirs.append(pm.group(1))
            if nm:
                names.append(nm.group(1))
    return dirs, names, lines


def sample_time_params(sim):
    """The wrappers' Ts (FixedStepBaseSampleTime read from the library): kind EVAL_PARAM when the kernel evaluated
    Functions.sampleTime() at translation, PARAM when it is computed at initialisation."""
    text = open(sim, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<variable name="([^"]*\.Ts)"[^>]*>', text):
        tag = m.group(0)
        if "FixedStepBaseSampleTime" not in tag:
            continue
        kind = re.search(r'kind="([^"]*)"', tag)
        bound = re.search(r'equationBound="([^"]*)"', tag)
        out.append({"name": m.group(1), "kind": kind.group(1) if kind else None,
                    "equationBound": bound.group(1) if bound else None})
    return out


LOGLINE = re.compile(r"^\[\s*(\w+)\s*;\s*(\w+)\s*;\s*([-+0-9.eE]+)\s*\]\s*(.*)$")


def exe_env(dirs):
    env = dict(os.environ)
    old = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = ":".join(dirs + ([old] if old else []))
    return env


def run_exe(work, short, sim, res, timeout, extra_args=(), stream_events=False, out_name="sim_out.txt"):
    dirs, _, _ = sim_libs(sim)
    env = exe_env(dirs)
    exe = os.path.join(work, short + ".exe")
    cmd = [exe, "-f", sim, "-r", res] + list(extra_args)
    counts, last_t, kept = {}, None, []
    t0 = time.perf_counter()
    capped = False
    err_text = ""
    if not stream_events:
        # stdout and stderr go to two files: when they share one file, the executable's stdout overwrites what it
        # wrote to stderr (measured 2026-10-25, probes.sh P5), so the warnings and the DLL messages would be lost.
        err_name = out_name.replace("_out", "_err")
        with open(os.path.join(work, out_name), "wb") as fo, open(os.path.join(work, err_name), "wb") as fe:
            p = subprocess.Popen(cmd, cwd=work, stdout=fo, stderr=fe, env=env)
            try:
                p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
                capped = True
        t1 = time.perf_counter()
        text = open(os.path.join(work, out_name), encoding="utf-8", errors="replace").read()
        err_text = open(os.path.join(work, err_name), encoding="utf-8", errors="replace").read()
    else:
        import threading
        p = subprocess.Popen(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        timer_hit = {"v": False}

        def killer():
            timer_hit["v"] = True
            try:
                p.kill()
            except OSError:
                pass
        timer = threading.Timer(timeout, killer)
        timer.start()
        for raw in p.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            m = LOGLINE.match(line)
            if m:
                level, area, tt, msg = m.groups()
                try:
                    last_t = float(tt)
                except ValueError:
                    pass
                if msg.startswith("Event iteration triggered by:"):
                    kind = msg.split(":", 1)[1].strip()
                    counts[kind] = counts.get(kind, 0) + 1
                    continue
                if area == "EVENT" and level == "verbose":
                    continue
            kept.append(line)
        p.wait()
        timer.cancel()
        capped = timer_hit["v"]
        t1 = time.perf_counter()
        text = "\n".join(kept)
        with open(os.path.join(work, out_name), "w", encoding="utf-8") as fo:
            fo.write(text + "\n")
    return {"wall_s": t1 - t0, "capped": capped, "returncode": p.returncode, "text": text, "stderr": err_text,
            "counts": counts,
            "last_t": last_t, "cmd": cmd, "dll_dirs": dirs, "ld_library_path": env["LD_LIBRARY_PATH"]}


def parse_final(text):
    def grab(rx, cast=float):
        m = re.search(rx, text)
        return cast(m.group(1)) if m else None
    return {
        "integration_s": grab(r"Integration took ([0-9.eE+-]+) seconds"),
        "initialization_s": grab(r"Initialization took ([0-9.eE+-]+) seconds"),
        "f_evaluations": grab(r"Total number of function evaluations: (\d+)", int),
        "events": grab(r"Total number of events: (\d+)", int),
        "step_events": grab(r"Total number of step events[^:]*: (\d+)", int),
        "stopped": grab(r"\[[^\]]*;\s*([0-9.eE+-]+)\]\s*Simulation stopped", float),
    }


def sim_messages(text):
    """Warnings and errors of the simulation log, and every line that is not a log line (the DLL's stderr)."""
    out = []
    keep_cont = False
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if line[:1] in (" ", "\t"):
            if keep_cont and out:
                out[-1] += "\n" + s
            continue
        lm = re.match(r"^\[\s*(\w+)\s*;", s)
        if lm:
            level = lm.group(1).lower()
            low = s.lower()
            keep_cont = level in ("warning", "error", "fatal") or "assert" in low
            if keep_cont:
                out.append(s)
        else:
            keep_cont = True
            out.append(s)
    return out


def classify(counts):
    te = se = 0
    other = {}
    for kind, n in counts.items():
        k = kind.lower()
        hit = False
        if "time event" in k:
            te += n
            hit = True
        if "state event" in k or "zero crossing" in k:
            se += n
            hit = True
        if not hit:
            other[kind] = n
    return te, se, other


def dynamic_section(exe, dirs, libnames):
    rd = run_text(["readelf", "-d", exe])
    dyn = [l.strip() for l in rd.splitlines() if re.search(r"NEEDED|RUNPATH|RPATH", l)]
    env0 = dict(os.environ)
    env0.pop("LD_LIBRARY_PATH", None)
    stems = [os.path.splitext(n)[0] for n in libnames]

    def pick(text):
        return [l.strip() for l in text.splitlines() if "not found" in l or (stems and any(s in l for s in stems))]
    return {"readelf_d": dyn,
            "has_runpath": any("RUNPATH" in l or "RPATH" in l for l in dyn),
            "ldd_without_LD_LIBRARY_PATH": pick(run_text(["ldd", exe], env=env0)),
            "ldd_with_LD_LIBRARY_PATH": pick(run_text(["ldd", exe], env=exe_env(dirs)))}


# ----------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--pkg", required=True, help="the package folder .../OpenIPSL (holds package.mo)")
    ap.add_argument("--out", required=True, help="record folder (CSV, metrics, raw points, logs/)")
    ap.add_argument("--work", required=True, help="build root, on the distro's ext4")
    ap.add_argument("--compiler", default=NOPIE, help="setCompilerPath(...) value, or 'default' for none")
    ap.add_argument("--wsm-home", default=os.environ.get("WSM_TARGET", "/usr/local/Wolfram/SystemModeler/15.0"))
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--no-count-events", action="store_true")
    ap.add_argument("--progress-log", action="store_true")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    pkg = os.path.abspath(a.pkg)
    pkg_mo = os.path.join(pkg, "package.mo")
    wsm = a.wsm_home
    run = next(r for r in spec["runs"] if r["id"] == a.run)
    model = run["model"]
    test = model.split(".")[-1]
    solver = run["solver"]
    short = test
    tag = "%s__%s" % (test, solver)
    work = os.path.join(os.path.abspath(a.work), tag)
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    os.makedirs(a.out, exist_ok=True)
    logdir = os.path.join(a.out, "logs", tag)
    os.makedirs(logdir, exist_ok=True)
    stop = float(run["stop"])
    tol = float(run.get("tolerance", 1e-6))
    method = {"dassl": "dassl", "euler": "explicit-euler"}[solver]
    step = float(run["step"]) if solver == "euler" else float(run["interval"])
    res = os.path.join(work, short + "_res.mat")
    kver = run_text([os.path.join(wsm, "bin", "WSMKernelX"), "--version"]).strip().splitlines()
    kver = kver[-1] if kver else "?"
    vid = ""
    try:
        vid = open(os.path.join(wsm, ".VersionID"), encoding="utf-8").read().strip()
    except OSError:
        pass
    comp = compiler_info(a.compiler)
    recipe = []
    metrics = {
        "tool": "Wolfram System Modeler",
        "tool_version": "System Modeler 15.0.0 for Linux (standalone kernel WSMKernelX --version %s, installation "
                        ".VersionID %s); no WSMLink (System Modeler for Linux ships no Wolfram kernel)" % (kver, vid),
        "msl_version": None,
        "platform": platform_string(),
        "compiler": "%s; %s" % (comp["name"], comp["version"]),
        "test": model, "solver": solver, "step": float(run["step"]) if solver == "euler" else None,
        "tolerance": tol, "start_time": 0.0, "stop_time": stop, "output_interval": step,
        "translate_s": None, "compile_s": None, "simulate_wall_s": None, "cpu_integration_s": None,
        "steps": None, "f_evaluations": None, "jacobian_evaluations": None, "time_events": None,
        "state_events": None, "result_points": None, "outcome": "failed", "tool_messages": [], "recipe": None,
    }
    note = []
    commit_file = os.path.join(os.path.dirname(pkg), "COMMIT")
    if os.path.exists(commit_file):
        metrics["wsm_library_commit"] = open(commit_file, encoding="utf-8").read().strip()
    elif spec.get("library_commit"):
        metrics["wsm_library_commit"] = spec["library_commit"]
    libdir = os.path.join(pkg, "Resources", "Library", "linux64")
    if os.path.isdir(libdir):
        metrics["wsm_linux64_sha256"] = {f: sha256(os.path.join(libdir, f)) for f in sorted(os.listdir(libdir))
                                         if f.endswith(".so")}
    metrics["wsm_host"] = {"kernel": platform.release(), "cpus": os.cpu_count(),
                           "wsl_distro": os.environ.get("WSL_DISTRO_NAME"), "user": os.environ.get("USER")}
    metrics["wsm_compiler_path"] = comp["path"]
    print("### %s  %s  compiler=%s" % (tag, time.strftime("%Y-%m-%d %H:%M:%S"), a.compiler), flush=True)
    b = build(work, pkg_mo, model, short, a.timeout, wsm, a.compiler, spec.get("extra_files", []))
    for f in ("kernel_out.txt", "kernel_err.txt"):
        shutil.copyfile(os.path.join(work, f), os.path.join(logdir, f))
    metrics["wsm_kernel_stderr"] = [l for l in b["kernel_stderr"].splitlines() if l.strip()][:50]
    for f in (short + "_build.log", short + ".log", "build.mos", "ModelicaPath.txt", "keep_%s.ninja" % short):
        if os.path.exists(os.path.join(work, f)):
            shutil.copyfile(os.path.join(work, f), os.path.join(logdir, f))
    m = re.search(r'Resolved `loadLibrary\("Modelica"\)`: "([^"]+)"', b["kernel_out"])
    if m:
        mv = re.search(r"Modelica (\d+\.\d+\.\d+)", m.group(1))
        metrics["msl_version"] = mv.group(1) if mv else m.group(1)
    metrics["translate_s"] = b["translate_s"]
    metrics["compile_s"] = b["compile_s"]
    msgs = list(b["messages"])
    ev = evaluator_lines(b["kernel_out"])
    metrics["wsm_evaluator_lines"] = ev
    metrics["wsm_evaluator_link_failures"] = sum(1 for l in ev if "can not be used when making a PIE object" in l)
    metrics["wsm_external_evaluations"] = [l for l in ev if l.startswith("External evaluation")]
    metrics["wsm_link_line"] = link_line(b["keep_ninja"], short)
    recipe.append("cd %s && %s build.mos   (ModelicaPath.txt: %s; %s)" % (
        work, b["kernel"], os.path.join(wsm, "L", "Modelica 4.0.0"), os.path.join(wsm, "L", "SystemModelerExtras")))
    recipe.append("build.mos: " + " ".join(b["mos"].splitlines()))
    print("build: ok=%s total=%.1f s translate=%s compile=%s evaluator link failures=%d" % (
        b["ok"], b["total_s"], b["translate_s"], b["compile_s"], metrics["wsm_evaluator_link_failures"]), flush=True)
    raw_points = 0
    if b["ok"]:
        sim = os.path.join(work, short + ".sim")
        limit = int(max(1e7, 50 * stop / step))
        old, new, n = rewrite_sim(sim, stop, method, step, tol, res, limit)
        shutil.copyfile(sim, os.path.join(logdir, short + ".sim"))
        recipe.append("rewrite %s.sim: %s ; StopAtMaxNoOutputPoints limit=%d" % (short, new, limit))
        dirs, libnames, liblines = sim_libs(sim)
        metrics["wsm_sim_external_libraries"] = liblines
        metrics["wsm_sample_time_parameters"] = sample_time_params(sim)
        exe = os.path.join(work, short + ".exe")
        metrics["wsm_executable"] = dynamic_section(exe, dirs, libnames)
        r = run_exe(work, short, sim, res, a.timeout,
                    extra_args=(["-v4", "-ls", "event"] if a.progress_log else []),
                    stream_events=a.progress_log)
        metrics["wsm_ld_library_path"] = r["ld_library_path"]
        recipe.append("cd %s && LD_LIBRARY_PATH=%s %s" % (work, r["ld_library_path"], " ".join(r["cmd"])))
        for f in ("sim_out.txt", "sim_err.txt"):
            if os.path.exists(os.path.join(work, f)):
                shutil.copyfile(os.path.join(work, f), os.path.join(logdir, f))
        fin = parse_final(r["text"])
        metrics["simulate_wall_s"] = r["wall_s"]
        metrics["cpu_integration_s"] = fin["integration_s"]
        metrics["f_evaluations"] = fin["f_evaluations"]
        metrics["wsm_sim_stderr"] = [l for l in r["stderr"].splitlines() if l.strip()]
        msgs += sim_messages(r["stderr"]) + sim_messages(r["text"])
        print("simulate: wall=%.2f s rc=%s capped=%s final=%s" % (r["wall_s"], r["returncode"], r["capped"], fin),
              flush=True)
        events_total = fin["events"]
        counts = r["counts"] if a.progress_log else None
        if r["capped"]:
            reached = r["last_t"] if a.progress_log else None
            metrics["outcome"] = "failed"
            msgs.insert(0, "time cap: the simulation was stopped after %.0f s of wall time%s" % (
                a.timeout, (", at t = %.6g s of %.6g s" % (reached, stop)) if reached is not None else ""))
            metrics["wsm_time_reached"] = reached
            if run.get("skip_on_cap"):
                metrics["outcome"] = "skipped"
        elif r["returncode"] == 0 and os.path.exists(res) and fin["stopped"] is not None:
            metrics["outcome"] = "ok"
        else:
            metrics["outcome"] = "failed"
            msgs.insert(0, "simulation executable exit code %s" % r["returncode"])
        if not a.no_count_events and not a.progress_log and metrics["outcome"] == "ok":
            ev_res = os.path.join(work, short + "_events_res.mat")
            r2 = run_exe(work, short, sim, ev_res, a.timeout, extra_args=["-v4", "-ls", "event"], stream_events=True,
                         out_name="sim_out_eventcount.txt")
            counts = r2["counts"]
            recipe.append("event count: the same executable with -v4 -ls event, output streamed and counted "
                          "(wall %.1f s, not part of the timing)" % r2["wall_s"])
            if os.path.exists(ev_res):
                os.remove(ev_res)
            shutil.copyfile(os.path.join(work, "sim_out_eventcount.txt"), os.path.join(logdir, "sim_out_eventcount.txt"))
            fin2 = parse_final(r2["text"])
            if fin2["events"] != events_total:
                note.append("event-count run reported %s events, the timed run %s" % (fin2["events"], events_total))
        if counts is not None:
            te, se, other = classify(counts)
            metrics["time_events"] = te
            metrics["state_events"] = se
            metrics["wsm_event_kinds"] = counts
            if other:
                note.append("unclassified event kinds: %s" % other)
        metrics["wsm_events_total"] = events_total
        metrics["wsm_step_events"] = fin["step_events"]
        metrics["wsm_initialization_s"] = fin["initialization_s"]
        if os.path.exists(res) and metrics["outcome"] == "ok":
            R = Result(res)
            raw_points = len(R.time)
            metrics["result_points"] = raw_points
            metrics["wsm_result_file"] = res
            metrics["wsm_result_bytes"] = os.path.getsize(res)
            sigs = run["signals"]
            missing = [s for s in sigs if not R.has(s)]
            if missing:
                note.append("signals not in the result: %s" % missing)
            present = [s for s in sigs if R.has(s)]
            vals = R.get_many(present) if present else []
            gstep = float(run["grid"])
            n = int(round(stop / gstep))
            grid = np.linspace(0.0, stop, n + 1)
            cols = [grid] + [resample(R.time, v, grid) for v in vals]
            data = np.column_stack(cols)
            hdr = ",".join(["time"] + present)
            np.savetxt(os.path.join(a.out, tag + ".csv"), data, delimiter=",", header=hdr, comments="", fmt="%.12g")
            metrics["wsm_signals_missing"] = missing
            metrics["wsm_nonfinite"] = int(np.sum(~np.isfinite(data)))
            st = [s for s in R.names if s.endswith(".status")]
            if st:
                sv = R.get_many(st)
                metrics["wsm_dll_status_max_abs"] = {s: float(np.max(np.abs(v))) for s, v in zip(st, sv)}
    else:
        msgs.insert(0, "build failed: no simulation executable" + (" (time cap)" if b["capped"] else ""))
    with open(os.path.join(a.out, tag + "_raw_points.txt"), "w", encoding="utf-8") as fh:
        fh.write("%d\n" % raw_points)
    metrics["tool_messages"] = msgs[:20]
    metrics["wsm_tool_messages_total"] = len(msgs)
    metrics["recipe"] = "\n".join(recipe)
    metrics["wsm_build_total_s"] = b["total_s"]
    if note:
        metrics["wsm_notes"] = note
    with open(os.path.join(a.out, tag + "_metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print("outcome:", metrics["outcome"], " messages:", len(msgs), " notes:", note, flush=True)
    return 0 if metrics["outcome"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
