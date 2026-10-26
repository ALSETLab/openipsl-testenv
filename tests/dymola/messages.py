"""Collect the unique tool messages of all runs (logs/<run>/all_messages.txt, written by post.py) with the runs that
printed each one, and print them as a Markdown table (README section "Every tool message").

Linux port of the Windows round-2 messages.py: the temporary object name in a GNU ld message (/tmp/ccXXXXXX.o, new
in every build) is written as /tmp/cc*.o and the code offset (.text+0x...) as (.text+0x*), so that the same
message of different runs is one row.

Usage: python -I -B messages.py <record folder>
"""
import glob
import os
import re
import sys


def main():
    out = sys.argv[1]
    seen = {}
    for p in sorted(glob.glob(os.path.join(out, 'logs', '*', 'all_messages.txt'))):
        run = os.path.basename(os.path.dirname(p))
        with open(p, encoding='utf-8') as f:
            for line in f:
                line = re.sub(r'/tmp/cc[A-Za-z0-9]+\.o', '/tmp/cc*.o', line.strip())
                line = re.sub(r'\(\.text\+0x[0-9a-f]+\)', '(.text+0x*)', line)
                if line:
                    seen.setdefault(line, []).append(run)
    print('| # | Message (verbatim, lines joined by ` \\| `) | Runs |')
    print('|---|---|---|')
    for i, (m, runs) in enumerate(seen.items(), 1):
        runs_u = sorted(set(runs))
        print('| M%d | `%s` | %s (%d) |' % (i, m.replace('|', '\\|'), ', '.join(runs_u), len(runs_u)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
