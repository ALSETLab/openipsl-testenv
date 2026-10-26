"""summarize.py - the runs table of a Linux System Modeler record (outcome, timings, counters), with the Windows
round-2 times of the same runs beside it, and how each executable found its library.

    /usr/bin/python3 -I summarize.py --spec runs.json --linux <Linux record> [--windows <Windows record>] --out <file.md>
"""
import argparse
import json
import os


def f(x, nd=2):
    if x is None:
        return "-"
    if isinstance(x, float):
        return ("%." + str(nd) + "f") % x
    return str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--linux", required=True)
    ap.add_argument("--windows")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    rows = ["| Run | outcome | translate (s) | compile (s) | simulate wall (s) | integration (s) | f-evals | time events | "
            "state events | result points | result file (MB) | messages | Windows r2: simulate wall / integration (s) | "
            "Ts kind | evaluator link failures |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    lib = ["| Run | .sim ExternalLibraries path | DT_NEEDED (library) | RUNPATH/RPATH | ldd without LD_LIBRARY_PATH | "
           "ldd with LD_LIBRARY_PATH | LD_LIBRARY_PATH set by the runner |", "|---|---|---|---|---|---|---|"]
    for r in spec["runs"]:
        tag = r["id"]
        p = os.path.join(a.linux, tag + "_metrics.json")
        if not os.path.exists(p):
            continue
        m = json.load(open(p, encoding="utf-8"))
        w = {}
        if a.windows and os.path.exists(os.path.join(a.windows, tag + "_metrics.json")):
            w = json.load(open(os.path.join(a.windows, tag + "_metrics.json"), encoding="utf-8"))
        ts = ", ".join("%s %s" % (x["name"], x["kind"]) for x in m.get("wsm_sample_time_parameters") or []) or "-"
        mb = (m.get("wsm_result_bytes") or 0) / 1e6
        rows.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s / %s | %s | %s |" % (
            tag, m["outcome"], f(m["translate_s"]), f(m["compile_s"]), f(m["simulate_wall_s"]),
            f(m["cpu_integration_s"], 3), f(m["f_evaluations"]), f(m["time_events"]), f(m["state_events"]),
            f(m["result_points"]), ("%.0f" % mb) if mb else "-", m.get("wsm_tool_messages_total"),
            f(w.get("simulate_wall_s")), f(w.get("cpu_integration_s"), 3), ts, m.get("wsm_evaluator_link_failures")))
        ex = m.get("wsm_executable")
        if ex and not m.get("wsm_sim_external_libraries"):
            lib.append("| %s | none (no external library) | - | %s | - | - | - |" % (
                tag, "; ".join(x for x in ex["readelf_d"] if "RUNPATH" in x or "RPATH" in x) or "none"))
        elif ex:
            paths = "; ".join(x.split('path="')[1].split('"')[0] for x in m.get("wsm_sim_external_libraries") or []
                              if 'path="' in x)
            needed = "; ".join(x.split("[")[1].rstrip("]") for x in ex["readelf_d"]
                               if "NEEDED" in x and ("SCRX9" in x or "GFM" in x)) or "-"
            rp = "; ".join(x for x in ex["readelf_d"] if "RUNPATH" in x or "RPATH" in x) or "none"
            lib.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                tag, paths or "-", needed, rp, "; ".join(ex["ldd_without_LD_LIBRARY_PATH"]) or "-",
                "; ".join(x.split(" (0x")[0] for x in ex["ldd_with_LD_LIBRARY_PATH"]) or "-",
                m.get("wsm_ld_library_path") or "-"))
    text = "\n".join(rows) + "\n\n" + "\n".join(lib) + "\n"
    open(a.out, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
