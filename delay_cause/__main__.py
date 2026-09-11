"""`python -m delay_cause --data-dir <dir> <command>`.

`report` is the artefact worth reading when a pattern changes: every notice on
the corpus beside what the reader took from it. `unread` is the other half - the
clauses no rule matched and the notices that state nothing - which is where a
new Irish Rail wording shows up first.
"""

from __future__ import annotations

import argparse
import collections
import os
import sys

from . import corpus, golden, model
from .text import readable


def _notices(data_dir):
    found = corpus.distinct(data_dir)
    if not found:
        sys.exit(f"no raw message logs under {data_dir}/raw")
    return found


def _report(args):
    notices = _notices(args.data_dir)
    counts, families = collections.Counter(), collections.Counter()
    for notice in notices:
        reading = model.read(notice.head, notice.text)
        print(f"\n{notice.first_seen}  {readable(notice.head)}")
        print(f"  {readable(notice.text)}")
        for cause in reading.causes:
            counts[cause.category] += 1
            families[cause.family] += 1
            earlier = ", earlier" if cause.earlier else ""
            marker = cause.marker or "no marker"
            print(
                f"    {cause.category:15} {cause.role:9} [{marker}{earlier}] "
                f"{cause.matched!r} in {cause.phrase!r}"
            )
        for clause in reading.unread:
            print(f"    {'unread':15} {clause!r}")
        if not reading.stated:
            print(f"    {'-':15} states no cause")
    print(f"\n{len(notices)} distinct notices")
    for category, count in counts.most_common():
        print(f"  {count:4}  {category:15} {model.LABEL[category]}")
    for family, count in families.most_common():
        print(f"  {count:4}  family {family}")


def _unread(args):
    notices = _notices(args.data_dir)
    clauses, silent = collections.Counter(), []
    for notice in notices:
        reading = model.read(notice.head, notice.text)
        for clause in reading.unread:
            clauses[clause] += 1
        if not reading.stated:
            silent.append(notice)
    print(f"{sum(clauses.values())} clause(s) a marker introduced and no rule read")
    for clause, count in clauses.most_common():
        print(f"  {count:3}  {clause!r}")
    print(f"\n{len(silent)} notice(s) stating no cause")
    for notice in silent:
        print(f"  {readable(notice.head)[:60]!r} :: {readable(notice.text)[:90]!r}")


def _golden(args):
    notices = _notices(args.data_dir)
    stored = golden.load()
    current = golden.build([(n.head, n.text) for n in notices])
    moved = golden.differences(stored, current)
    gained = golden.new_notices(stored, current)
    golden.PATH.write_text(golden.dumps(golden.merge(stored, current)), encoding="utf-8")
    print(f"wrote {golden.PATH}")
    print(f"  {len(gained)} notice(s) the file had not pinned")
    print(f"  {len(moved)} reading(s) moved")
    for line in moved:
        print(f"    {line}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="delay_cause")
    parser.add_argument("--data-dir", default=os.environ.get("LIFT_STATUS_DATA_DIR", "."))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("report", help="every notice beside what the reader took from it")
    commands.add_parser("unread", help="clauses no rule read, and notices stating nothing")
    commands.add_parser("golden", help="regenerate tests/fixtures/delay-cause-golden.json")
    args = parser.parse_args(argv)
    {"report": _report, "unread": _unread, "golden": _golden}[args.command](args)


if __name__ == "__main__":
    main()
