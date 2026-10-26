"""compare_mat.py - are two System Modeler results bit-identical? Every variable the two .mat files share (time,
states, algebraics, parameters), compared bit for bit at every stored point.

    /usr/bin/python3 -I compare_mat.py <a_res.mat> <b_res.mat> [--json <out.json>] [--label-a A --label-b B]

Used for the runs with the kit's g++-nopie wrapper against the same runs with the kernel's default g++ (whose
external-function evaluator fails to link, so the wrappers' Ts is computed at initialisation instead of being
evaluated at translation).
"""
import argparse
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True  # no __pycache__ in the kit folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wsm_run_linux import Result  # noqa: E402


def column_map(R):
    out = {}
    for i, n in enumerate(R.names):
        mat, col = int(R.info[i, 0]), int(R.info[i, 1])
        out[n] = (mat, abs(col) - 1, 1.0 if col > 0 else -1.0)
    return out


def values(R, d2, spec):
    mat, col, sign = spec
    if mat == 1:
        d1 = np.asarray(R.d1, dtype=float)
        v = d1[0, col] if d1.ndim == 2 and d1.shape[0] else d1[col]
        return np.array([sign * float(v)])
    if mat == 0:
        return d2[:, 0]
    return sign * d2[:, col]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--json")
    ap.add_argument("--label-a", default="a")
    ap.add_argument("--label-b", default="b")
    a = ap.parse_args()
    A, B = Result(a.a), Result(a.b)
    da, db = np.asarray(A.d2, dtype=float), np.asarray(B.d2, dtype=float)
    ma, mb = column_map(A), column_map(B)
    common = [n for n in A.names if n in mb]
    only_a = [n for n in A.names if n not in mb]
    only_b = [n for n in B.names if n not in ma]
    res = {"a": a.a, "b": a.b, "label_a": a.label_a, "label_b": a.label_b,
           "points_a": int(da.shape[0]), "points_b": int(db.shape[0]), "variables_a": len(A.names),
           "variables_b": len(B.names), "common": len(common), "only_a": only_a, "only_b": only_b,
           "file_bytes_a": os.path.getsize(a.a), "file_bytes_b": os.path.getsize(a.b)}
    same_time = da.shape[0] == db.shape[0] and np.array_equal(da[:, 0].view(np.uint64), db[:, 0].view(np.uint64))
    res["time_bitwise_equal"] = bool(same_time)
    differ, maxabs, storage_moved = [], 0.0, []
    maxrel = [(0.0, None)]
    maxrel_sig = [(0.0, None)]
    SIGNIFICANT = 1e-3
    for n in common:
        va, vb = values(A, da, ma[n]), values(B, db, mb[n])
        if (ma[n][0] == 1) != (mb[n][0] == 1):
            storage_moved.append(n)
            va = np.broadcast_to(va, (max(len(va), len(vb)),)) if len(va) == 1 else va
            vb = np.broadcast_to(vb, (max(len(va), len(vb)),)) if len(vb) == 1 else vb
        if va.shape != vb.shape:
            differ.append({"name": n, "reason": "shape %s vs %s" % (va.shape, vb.shape)})
            continue
        if not np.array_equal(np.ascontiguousarray(va).view(np.uint64), np.ascontiguousarray(vb).view(np.uint64)):
            d = float(np.nanmax(np.abs(va - vb))) if va.size else 0.0
            scale = float(np.nanmax(np.abs(va))) if va.size else 0.0
            rel = d / scale if scale > 0 else None
            if not n.startswith("$SimulationLog"):
                maxabs = max(maxabs, d)
                if rel is not None:
                    maxrel[0] = max(maxrel[0], (rel, n))
                    if scale > SIGNIFICANT:
                        maxrel_sig[0] = max(maxrel_sig[0], (rel, n))
            differ.append({"name": n, "max_abs": d, "max_abs_value": scale, "rel": rel})
    res["storage_moved_between_data_1_and_data_2"] = storage_moved
    differ.sort(key=lambda x: -(x.get("rel") or 0.0))
    res["data_2_dtype"] = str(np.asarray(A.d2[:1]).dtype)
    res["differing"] = differ[:300]
    res["n_differing"] = len(differ)
    res["n_differing_simulation_log"] = sum(1 for x in differ if x["name"].startswith("$SimulationLog"))
    res["max_abs_difference"] = maxabs
    res["max_rel_difference"] = {"rel": maxrel[0][0], "name": maxrel[0][1]}
    res["max_rel_difference_significant"] = {"rel": maxrel_sig[0][0], "name": maxrel_sig[0][1],
                                             "note": "variables whose max |value| exceeds %g (leaves out round-off "
                                                     "noise signals such as ground currents of 1e-11 A)" % SIGNIFICANT}
    res["bit_identical_common_variables"] = bool(same_time and not differ)
    res["bit_identical_except_simulation_log"] = bool(same_time and len(differ) == res["n_differing_simulation_log"])
    print("%s vs %s: points %d / %d, variables %d / %d, common %d, time bitwise equal %s, differing %d (%d of them "
          "$SimulationLog.*; others: max abs %.3g, max relative to the variable's max abs value %.3g in %s, "
          "among variables with max abs value > 1e-3: %.3g in %s), "
          "only in %s: %s, only in %s: %s, storage moved: %s" % (
              a.label_a, a.label_b, res["points_a"], res["points_b"], res["variables_a"], res["variables_b"],
              res["common"], same_time, len(differ), res["n_differing_simulation_log"], maxabs, maxrel[0][0],
              maxrel[0][1], maxrel_sig[0][0], maxrel_sig[0][1], a.label_a, only_a[:10], a.label_b, only_b[:10],
              storage_moved[:10]))
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
