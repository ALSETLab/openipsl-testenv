"""Summary of the raw (stored-point) part of a comparison file written by compare_windows.py: per run the stored
points of both files, whether the stored time vectors are equal, and the largest difference of a contract signal
over the stored points, absolute and relative to the largest |value| of that signal (from the CSV part).

Usage: python -I -B raw_summary.py <comparison .json>
"""
import json
import sys


def main():
    r = json.load(open(sys.argv[1], encoding='utf-8'))
    print('| run | stored points A / B | time vectors | worst signal | max abs | rel | t of max | signals bit-identical |')
    print('|---|---|---|---|---|---|---|---|')
    for run, v in r['runs'].items():
        rw, c = v.get('raw', {}), v.get('csv', {})
        scale = {n: s['scale_max_abs_windows'] for n, s in c.get('signals', {}).items()}
        if 'signals' in rw:
            worst = max(rw['signals'].items(), key=lambda kv: kv[1]['max_abs'] / (scale.get(kv[0]) or 1.0))
            n, s = worst
            rel = s['max_abs'] / scale[n] if scale.get(n) else float('nan')
            same = sum(1 for x in rw['signals'].values() if x['identical'])
            tv = 'equal' if rw['time_max_abs_diff'] == 0 else 'max |dt| %.3g s' % rw['time_max_abs_diff']
            print('| %s | %d / %d | %s | %s | %.3g | %.3g | %.6g | %d of %d |' % (
                run, rw['points_linux'], rw['points_windows'], tv, n, s['max_abs'], rel, s['t_of_max'], same,
                len(rw['signals'])))
        elif 'points_linux' in rw:
            m = rw.get('max_abs_at_common_instants_post_event', {})
            n = max(m, key=lambda k: (m[k] or 0) / (scale.get(k) or 1.0)) if m else None
            rel = (m[n] / scale[n]) if n and scale.get(n) else float('nan')
            print('| %s | %d / %d | differ from point %s (t = %.10g s); %d common instants | %s | %.3g | %.3g | '
                  '(post-event value at each common instant) | - |' % (
                      run, rw['points_linux'], rw['points_windows'], rw.get('first_index_time_differs'),
                      (rw.get('times_around_first_difference_linux') or [float('nan')] * 3)[2],
                      rw.get('common_instants', 0), n, m.get(n, float('nan')) if n else float('nan'), rel))
        else:
            print('| %s | %s | | | | | | |' % (run, rw.get('note')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
