"""compare_windows.py - the Linux System Modeler record against the Windows round-2 System Modeler record of the same
runs: max |difference| per signal on the contract grid (whole run, before the first disturbance, after it, last
0.5 s), relative to the Windows signal's range, and the counters of the metrics files side by side.

    /usr/bin/python3 -I compare_windows.py --spec runs.json --linux <Linux record dir> --windows <Windows record dir>
                     --out <dir> [--name compare_windows]

Writes <out>/<name>.json and <out>/<name>.md. Both CSVs come from the same resampling code (wsm_run.py on Windows,
wsm_run_linux.py here, identical resample()), so a difference is a difference of the stored results.
"""
import argparse
import json
import os

import numpy as np


def load_csv(path):
    with open(path, encoding="utf-8") as fh:
        hdr = fh.readline().strip().split(",")
    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    return hdr, data


def fmt(x):
    if x is None:
        return "-"
    if x == 0:
        return "0"
    return "%.2g" % x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--linux", required=True)
    ap.add_argument("--windows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="compare_windows")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    allres = []
    md = ["| Run | outcome L / W | f-evals L / W | time events L / W | state events L / W | result points L / W | "
          "max abs diff before the first disturbance (signal) | max abs diff after it (signal, at t) | after, relative to range | "
          "last 0.5 s |", "|---|---|---|---|---|---|---|---|---|---|"]
    per_signal_md = []
    for r in spec["runs"]:
        tag = r["id"]
        ml = os.path.join(a.linux, tag + "_metrics.json")
        mw = os.path.join(a.windows, tag + "_metrics.json")
        L = json.load(open(ml, encoding="utf-8")) if os.path.exists(ml) else {}
        W = json.load(open(mw, encoding="utf-8")) if os.path.exists(mw) else {}
        row = {"run": tag}
        for k in ("outcome", "f_evaluations", "time_events", "state_events", "result_points", "simulate_wall_s",
                  "cpu_integration_s", "translate_s", "compile_s"):
            row[k] = [L.get(k), W.get(k)]
        cl = os.path.join(a.linux, tag + ".csv")
        cw = os.path.join(a.windows, tag + ".csv")
        if os.path.exists(cl) and os.path.exists(cw):
            hl, dl = load_csv(cl)
            hw, dw = load_csv(cw)
            row["same_header"] = hl == hw
            row["same_grid"] = dl.shape == dw.shape and bool(np.array_equal(dl[:, 0], dw[:, 0]))
            t = dl[:, 0]
            t1 = r.get("first_disturbance")
            before = t < (t1 - 1e-9) if t1 is not None else np.ones_like(t, dtype=bool)
            after = ~before
            last = t >= t[-1] - 0.5 - 1e-9
            sig = {}
            for j, name in enumerate(hl[1:], 1):
                if name not in hw:
                    continue
                k = hw.index(name)
                d = np.abs(dl[:, j] - dw[:, k])
                rng = float(np.max(dw[:, k]) - np.min(dw[:, k]))
                s = {"all": float(d.max()), "before": float(d[before].max()) if before.any() else None,
                     "after": float(d[after].max()) if after.any() else None,
                     "after_t": float(t[after][np.argmax(d[after])]) if after.any() else None,
                     "last_0p5s": float(d[last].max()), "range_windows": rng}
                s["after_rel"] = (s["after"] / rng) if (s["after"] is not None and rng > 0) else None
                sig[name] = s
            row["signals"] = sig

            def worst(key):
                c = [(v[key], n) for n, v in sig.items() if v[key] is not None]
                return max(c) if c else (None, None)
            wb, nb = worst("before")
            wa, na = worst("after")
            wr, nr = worst("after_rel")
            wl, nl = worst("last_0p5s")
            row["worst"] = {"before": [wb, nb], "after": [wa, na, sig[na]["after_t"] if na else None],
                            "after_rel": [wr, nr], "last_0p5s": [wl, nl]}
            md.append("| %s | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s | %s (%s) | %s (%s, %s s) | %s (%s) | %s (%s) |" % (
                tag, L.get("outcome"), W.get("outcome"), L.get("f_evaluations"), W.get("f_evaluations"),
                L.get("time_events"), W.get("time_events"), L.get("state_events"), W.get("state_events"),
                L.get("result_points"), W.get("result_points"), fmt(wb), nb, fmt(wa), na,
                ("%.6g" % sig[na]["after_t"]) if na else "-", fmt(wr), nr, fmt(wl), nl))
            per_signal_md.append("\n### %s\n\n| signal | all | before | after | at t (s) | after / range | last 0.5 s | range (Windows) |\n|---|---|---|---|---|---|---|---|" % tag)
            for n, v in sig.items():
                per_signal_md.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    n, fmt(v["all"]), fmt(v["before"]), fmt(v["after"]),
                    ("%.6g" % v["after_t"]) if v["after_t"] is not None else "-", fmt(v["after_rel"]),
                    fmt(v["last_0p5s"]), "%.6g" % v["range_windows"]))
        else:
            md.append("| %s | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s | no CSV | no CSV | - | - |" % (
                tag, L.get("outcome"), W.get("outcome"), L.get("f_evaluations"), W.get("f_evaluations"),
                L.get("time_events"), W.get("time_events"), L.get("state_events"), W.get("state_events"),
                L.get("result_points"), W.get("result_points")))
        allres.append(row)
    json.dump(allres, open(os.path.join(a.out, a.name + ".json"), "w", encoding="utf-8"), indent=1)
    text = "\n".join(md) + "\n\n## Per signal\n" + "\n".join(per_signal_md) + "\n"
    open(os.path.join(a.out, a.name + ".md"), "w", encoding="utf-8").write(text)
    print("\n".join(md))


if __name__ == "__main__":
    main()
