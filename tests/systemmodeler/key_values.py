"""key_values.py - the documented numbers of the Windows round-2 System Modeler README, read from a record's CSVs, so
that the Linux and the Windows record can be put side by side (SCRX9: EFD at the listed instants and the pre-fault
drift; converter tests: P = out[11] (MW), Q = out[12] (Mvar), f = out[10] (Hz) at the end; GFL_FaultPSCAD: the D.3 windows of Q).

    /usr/bin/python3 -I key_values.py --record <dir> [--record <dir2> ...] --labels L,W --out <file.md>
"""
import argparse
import os

import numpy as np


def load(path):
    with open(path, encoding="utf-8") as fh:
        hdr = fh.readline().strip().split(",")
    d = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    return {h: d[:, i] for i, h in enumerate(hdr)}


def at(c, name, t):
    return float(c[name][int(np.argmin(np.abs(c["time"] - t)))])


def mean(c, name, t0, t1):
    m = (c["time"] >= t0 - 1e-9) & (c["time"] <= t1 + 1e-9)
    return float(np.mean(c[name][m]))


def values(rec):
    out = {}
    for tag in ("SCRX9__dassl", "SCRX9__euler"):
        p = os.path.join(rec, tag + ".csv")
        if not os.path.exists(p):
            continue
        c = load(p)
        e0 = c["gENROU.EFD"][0]
        pre = c["time"] < 2.0025 - 1e-9
        out[tag + " EFD(0)"] = c["sCRX9.EFD"][0]
        out[tag + " max abs(EFD-EFD0), t<2.0025"] = float(np.max(np.abs(c["sCRX9.EFD"][pre] - e0)))
        out[tag + " max abs(w), t<2.0025"] = float(np.max(np.abs(c["gENROU.w"][pre])))
        for t in (1.995, 2.005, 2.1, 2.155, 5.0, 10.0):
            out[tag + " EFD(%g)" % t] = at(c, "sCRX9.EFD", t)
    for tag in ("GFL_Fault__euler", "GFL_POCFault__euler", "GFL_FrequencyStep__euler", "GFL_VoltageStep__euler",
                "GFL_PowerRamp__euler", "GFL_FaultPSCAD__euler", "GFM_EMTPFault__euler", "GFM_EMTPFull__euler",
                "GFL_PowerRamp__dassl"):
        p = os.path.join(rec, tag + ".csv")
        if not os.path.exists(p):
            continue
        c = load(p)
        out[tag + " P(end) MW"] = float(c["gFM_GFL_IBR.out[11]"][-1])
        out[tag + " Q(end) Mvar"] = float(c["gFM_GFL_IBR.out[12]"][-1])
        out[tag + " f(end) Hz"] = float(c["gFM_GFL_IBR.out[10]"][-1])
        if tag == "GFL_FaultPSCAD__euler":
            out[tag + " mean Q 1.5-2 s"] = mean(c, "gFM_GFL_IBR.out[12]", 1.5, 2.0)
            out[tag + " mean Q 4.5-5 s"] = mean(c, "gFM_GFL_IBR.out[12]", 4.5, 5.0)
            out[tag + " mean P 4.5-5 s"] = mean(c, "gFM_GFL_IBR.out[11]", 4.5, 5.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="append", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    labels = a.labels.split(",")
    vals = [values(r) for r in a.record]
    keys = list(vals[0].keys())
    rows = ["| value | " + " | ".join(labels) + " | " + " - ".join(labels[:2]) + " |",
            "|---|" + "---|" * (len(labels) + 1)]
    for k in keys:
        v = [x.get(k) for x in vals]
        d = (v[0] - v[1]) if len(v) > 1 and v[0] is not None and v[1] is not None else None
        rows.append("| %s | %s | %s |" % (k, " | ".join("%.10g" % x if x is not None else "-" for x in v),
                                         "%.3g" % d if d is not None else "-"))
    open(a.out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
