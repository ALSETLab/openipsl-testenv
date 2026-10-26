"""validate_classes.py - validate classes with System Modeler's standalone kernel (Linux), one kernel session per
class: the kernel's checkModelTest, the call behind Model Center's "Validate" (flatten + symbolic processing, the
same "Validation of model ... completed successfully" report), with the unit check made visible.

    /usr/bin/python3 -I validate_classes.py --pkg <.../OpenIPSL> --classes <classes.txt> --work <build root>
                     --out <record dir> [--extra <WSMExperiments.mo> --extra-classes <list>]
                     [--severity warning|default] [--compiler /opt/openipsl-kit/bin/g++-nopie|default]
                     [--windows-json <round-2 wsm_validate.json>] [--name <file stem>]

Why one session per class: the kernel's *Test functions attach every message raised so far in the session to the
test they run (measured 2026-10-25: two failed calls before a checkModelTest made it report "flatten: Fail" with
their errors), so a session that validates several classes mixes their messages.

Why +unit-violation-severity=warning: the standalone kernel's default for unit violations is "silent" (its
mce_getUnitViolationSeverity() returns "silent", the report then says "There were 2 silenced messages due to the
"unitViolation" verbosity."), while WSMLink's WSMValidate on Windows reported them as warnings. With the flag the
negative control WSMExperimentsRound2.UnitCheckNegativeControl gives the same two "Incompatible units" warnings as
WSMValidate. "--severity default" runs without the flag (control).

Why setCompilerPath: validating a model that uses the DLL wrappers makes the kernel evaluate Functions.sampleTime() and
Functions.count() at translation with its external-function evaluator, which it compiles and links; with the
kernel's default "g++" that link fails on Ubuntu (PIE default against the non-PIC libserializer.a, see
provision/30_systemmodeler.sh). The .mos therefore names the kit's g++-nopie, as the contract runs do;
"--compiler default" leaves it out (control: the failures are counted per class in evaluator_link_failures).

Writes <out>/<name>.json, <out>/<name>_table.md and <out>/logs/<name>/<NN>_<class>/{check.mos, kernel_out.txt,
check.out.json}. Windows has no equivalent here: WSMValidate (WSMLink) needs a Wolfram kernel, which System Modeler
for Linux does not ship.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import time

NOISE = ("Resolved `", "External functions with language `\"builtin\"` are deprecated")


def first_line(s):
    return s.strip().splitlines()[0] if s.strip() else s


def run_one(idx, cls, a, wsm, extra):
    safe = re.sub(r"[^A-Za-z0-9_.]", "_", cls)
    work = os.path.join(a.work, "%02d_%s" % (idx, safe))
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    with open(os.path.join(work, "ModelicaPath.txt"), "w", encoding="utf-8") as fh:
        fh.write(os.path.join(wsm, "L", "Modelica 4.0.0") + "\n" + os.path.join(wsm, "L", "SystemModelerExtras") + "\n")
    mos = ["setStopOnError(false);", 'setTempDirectoryPath("%s");' % work]
    if a.compiler != "default":
        mos.append('setCompilerPath("%s");' % a.compiler)
    mos += ["loadLibrary(Modelica);", 'loadFile("%s");' % os.path.join(os.path.abspath(a.pkg), "package.mo")]
    if extra:
        mos.append('loadFile("%s");' % extra)
    mos.append("checkModelTest(%s);" % cls)
    with open(os.path.join(work, "check.mos"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(mos) + "\n")
    cmd = [os.path.join(wsm, "bin", "WSMKernelX")]
    if a.severity != "default":
        cmd.append("+unit-violation-severity=%s" % a.severity)
    cmd.append("check.mos")
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=a.timeout)
        rc, out = p.returncode, p.stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired as e:
        rc, out = "timeout", (e.stdout or b"").decode("utf-8", errors="replace")
    dt = time.perf_counter() - t0
    open(os.path.join(work, "kernel_out.txt"), "w", encoding="utf-8").write(out)
    oj = os.path.join(work, "check.out.json")
    entry = None
    if os.path.exists(oj):
        try:
            data = json.load(open(oj, encoding="utf-8"))
            entry = next((e for e in data if isinstance(e, dict) and e.get("test_type") == "checkModelTest"), None)
        except ValueError:
            entry = None
    m = re.search(r'"(# \\\\g Validation.*?)"\s*$', out, re.S)
    report = m.group(1).replace('\\"', '"') if m else None
    res = {"class": cls, "seconds": dt, "kernel_returncode": rc, "command": " ".join(cmd), "mos": mos,
           "report": report}
    if entry:
        msgs = entry.get("messages") or {}
        res["flatten"] = (entry.get("status") or {}).get("flatten")
        res["errors"] = [mm["message"] for mm in msgs.get("errors") or []]
        res["internal_errors"] = [mm["message"] for mm in msgs.get("internal_errors") or []]
        res["warnings"] = [mm["message"] for mm in msgs.get("warnings") or []]
        res["notifications"] = [mm["message"] for mm in msgs.get("notifications") or []]
        res["valid"] = res["flatten"] == "Pass" and not res["errors"] and not res["internal_errors"]
    else:
        res.update({"flatten": None, "errors": ["no checkModelTest record in check.out.json"], "internal_errors": [],
                    "warnings": [], "notifications": [], "valid": False})
    res["evaluator_link_failures"] = out.count("can not be used when making a PIE object")
    res["external_evaluations"] = len(re.findall(r"^External evaluation of ", out, re.M))
    res["unit_warnings"] = [w for w in res["warnings"] if "Incompatible units" in w or "unit" in w.lower()]
    res["silenced"] = re.findall(r"There were (\d+) silenced messages due to the \\?\"(\w+)\\?\" verbosity", out)
    keep = os.path.join(a.out, "logs", a.name, "%02d_%s" % (idx, safe))
    os.makedirs(keep, exist_ok=True)
    for f in ("check.mos", "kernel_out.txt", "check.out.json"):
        if os.path.exists(os.path.join(work, f)):
            shutil.copyfile(os.path.join(work, f), os.path.join(keep, f))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--classes", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", help="extra .mo loaded after OpenIPSL for the --extra-classes")
    ap.add_argument("--extra-classes", help="file with the classes of --extra")
    ap.add_argument("--severity", default="warning", help="value of +unit-violation-severity, or 'default'")
    ap.add_argument("--windows-json", help="Windows round-2 wsm_validate.json, for the comparison column")
    ap.add_argument("--compiler", default="/opt/openipsl-kit/bin/g++-nopie",
                    help="setCompilerPath(...) value, or 'default' for none")
    ap.add_argument("--name", default="validation")
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--wsm-home", default=os.environ.get("WSM_TARGET", "/usr/local/Wolfram/SystemModeler/15.0"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    classes = [l.strip() for l in open(a.classes, encoding="utf-8") if l.strip()]
    extra_classes = []
    if a.extra_classes:
        extra_classes = [l.strip() for l in open(a.extra_classes, encoding="utf-8") if l.strip()]
    win = {}
    if a.windows_json and os.path.exists(a.windows_json):
        for r in json.load(open(a.windows_json, encoding="utf-8"))["results"]:
            win[r["class"]] = r
    kver = subprocess.run([os.path.join(a.wsm_home, "bin", "WSMKernelX"), "--version"], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout.decode().strip().splitlines()[-1]
    results = []
    t_all = time.time()
    todo = [(c, None) for c in classes] + [(c, os.path.abspath(a.extra)) for c in extra_classes]
    for i, (cls, extra) in enumerate(todo, 1):
        r = run_one(i, cls, a, a.wsm_home, extra)
        results.append(r)
        print("%2d %-75s valid=%s flatten=%s %.1f s  E%d W%d(units %d) N%d  evaluator link failures %d" % (
            i, cls, r["valid"], r["flatten"], r["seconds"], len(r["errors"]), len(r["warnings"]),
            len(r["unit_warnings"]), len(r["notifications"]), r["evaluator_link_failures"]), flush=True)
    doc = {"date": time.strftime("%Y-%m-%d %H:%M:%S"), "kernel_version": kver, "severity": a.severity,
           "compiler": a.compiler,
           "package": os.path.abspath(a.pkg), "total_s": time.time() - t_all, "results": results}
    json.dump(doc, open(os.path.join(a.out, a.name + ".json"), "w", encoding="utf-8"), indent=1)
    rows = ["| # | Class | valid (Linux kernel checkModelTest) | valid (Windows round 2, WSMValidate) | s | evaluator link failures | errors, unit warnings, other warnings, notifications (first line of each; MSL `builtin` deprecation warnings and `Resolved` notifications left out) |",
            "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        w = win.get(r["class"])
        wv = "-" if w is None else str(w["valid"])
        parts = ["Error: " + first_line(e) for e in r["internal_errors"] + r["errors"]]
        parts += ["Warning: " + first_line(x) for x in r["warnings"] if not any(n in x for n in NOISE)]
        parts += ["Notification: " + first_line(x) for x in r["notifications"] if not any(n in x for n in NOISE)]
        if r["silenced"]:
            parts.append("silenced: %s" % ", ".join("%s %s" % s for s in r["silenced"]))
        txt = "<br>".join(p.replace("|", "\\|") for p in parts) or "-"
        rows.append("| %d | %s | %s | %s | %.1f | %d | %s |" % (i, r["class"], r["valid"], wv, r["seconds"],
                                                         r["evaluator_link_failures"], txt))
    nv = sum(1 for r in results if r["valid"])
    agree = sum(1 for r in results if r["class"] in win and win[r["class"]]["valid"] == r["valid"])
    ncmp = sum(1 for r in results if r["class"] in win)
    rows.append("")
    nev = sum(r["evaluator_link_failures"] for r in results)
    rows.append("valid: %d of %d; same verdict as Windows round 2: %d of %d compared; kernel %s, "
                "+unit-violation-severity=%s, compiler %s; evaluator link failures %d; %.0f s in all" % (
                    nv, len(results), agree, ncmp, kver, a.severity, a.compiler, nev, doc["total_s"]))
    open(os.path.join(a.out, a.name + "_table.md"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print(rows[-1])


if __name__ == "__main__":
    main()
