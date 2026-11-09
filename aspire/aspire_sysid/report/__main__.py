"""``python -m aspire_sysid.report <experiment-dir> [--out DIR]``: write the HTML report."""

from __future__ import annotations

import argparse
import sys

from .html_report import build_report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m aspire_sysid.report", description=__doc__)
    ap.add_argument("experiment_dir", help="the experiment folder, for example experiments/paper-turtlebot")
    ap.add_argument("--out", default=None, help="output folder (default: <experiment_dir>/report)")
    args = ap.parse_args(argv)
    index = build_report(args.experiment_dir, args.out)
    print(f"wrote {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
