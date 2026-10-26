"""collect_messages.py - every distinct tool message of a Linux record (all of each run's messages, from the logs, not
only the first 20 of the metrics files) beside the Windows round-2 record of the same runs: which message appears on
one platform only. Paths are normalised (install folder, build folder) before the comparison; the raw text is kept.

    /usr/bin/python3 -I collect_messages.py --spec runs.json --linux <Linux record> --windows <Windows record>
                     --out <file.md> [--json <file.json>]
"""
import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True  # no __pycache__ in the kit folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wsm_run_linux import kernel_messages, sim_messages  # noqa: E402


def run_messages(rec, tag):
    d = os.path.join(rec, "logs", tag)
    msgs = []
    for f, parse in (("kernel_out.txt", kernel_messages), ("kernel_err.txt", kernel_messages),
                     ("sim_err.txt", sim_messages), ("sim_out.txt", sim_messages)):
        p = os.path.join(d, f)
        if os.path.exists(p):
            msgs += parse(open(p, encoding="utf-8", errors="replace").read())
    return msgs


def norm(m):
    s = m.replace("\\", "/")
    s = re.sub(r"C:/Program Files/Wolfram Research/System Modeler 15.0", "<WSM>", s)
    s = re.sub(r"/usr/local/Wolfram/SystemModeler/15.0", "<WSM>", s)
    s = re.sub(r":(readonly|writable)\]", ":<ro|rw>]", s)
    s = re.sub(r"\n\s*", " ", s)
    return s.strip()


def kind(m):
    if m.startswith("FAILED:"):
        return "evaluator build failure"
    if "Notification: The following variables are selected as states" in m:
        return "state selection"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--linux", required=True)
    ap.add_argument("--windows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json")
    ap.add_argument("--label-linux", default="Linux", help="name of the --linux record in the table")
    ap.add_argument("--label-windows", default="Windows", help="name of the --windows record in the table")
    a = ap.parse_args()
    la, lw = a.label_linux, a.label_windows
    spec = json.load(open(a.spec, encoding="utf-8"))
    table = {}
    for r in spec["runs"]:
        tag = r["id"]
        if not all(os.path.isdir(os.path.join(rec, "logs", tag)) for rec in (a.linux, a.windows)):
            continue  # compare only the runs both records have
        for side, rec in (("linux", a.linux), ("windows", a.windows)):
            for m in run_messages(rec, tag):
                k = norm(m)
                e = table.setdefault(k, {"text": {}, "linux": [], "windows": []})
                e["text"].setdefault(side, m)
                if tag not in e[side]:
                    e[side].append(tag)
    rows = ["| on | runs (%s) | runs (%s) | message (normalised: <WSM> = the install folder, <ro\\|rw> = the kernel's readonly/writable tag) |" % (la, lw),
            "|---|---|---|---|"]
    for k, e in sorted(table.items(), key=lambda kv: (bool(kv[1]["linux"]) and bool(kv[1]["windows"]), kv[0])):
        on = "both" if e["linux"] and e["windows"] else ((la + " only") if e["linux"] else (lw + " only"))
        if kind(k) == "state selection" and on == "both":
            continue
        txt = k if len(k) < 600 else k[:600] + " ..."
        rows.append("| %s | %s | %s | %s |" % (on, ", ".join(e["linux"]) or "-", ", ".join(e["windows"]) or "-",
                                             txt.replace("|", "\\|")))
    same_states = [k for k, e in table.items() if kind(k) == "state selection" and e["linux"] and e["windows"]]
    rows.append("")
    rows.append("State-selection notifications identical in both records: %d (left out of the table)." % len(same_states))
    open(a.out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    if a.json:
        json.dump(table, open(a.json, "w", encoding="utf-8"), indent=1)
    print("\n".join(rows))


if __name__ == "__main__":
    main()
