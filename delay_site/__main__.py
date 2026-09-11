"""`python -m delay_site --data-dir <dir>` writes out/site/."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

from . import render


def main(argv=None):
    parser = argparse.ArgumentParser(prog="delay_site")
    parser.add_argument("--data-dir", default=os.environ.get("LIFT_STATUS_DATA_DIR", "."))
    parser.add_argument("--out", default="out/site")
    args = parser.parse_args(argv)
    try:
        size, report = render.build(args.data_dir, args.out, datetime.now(tz=UTC))
    except ValueError as problem:
        sys.exit(str(problem))
    print(f"wrote {args.out}")
    print(report)
    if size > render.BUDGET_BYTES:
        sys.exit("initial load is over budget")


if __name__ == "__main__":
    main()
