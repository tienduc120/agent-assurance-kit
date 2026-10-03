"""aak run <target.yaml>: run every applicable pack and print the results."""

import argparse
import sys

from aak.packs import PACKS
from aak.report import markdown
from aak.run import run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aak")
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run", help="run the packs that apply to a target")
    run_cmd.add_argument("target", help="path to target.yaml")
    run_cmd.add_argument("--packs", help="comma-separated pack names (default: all)")
    run_cmd.add_argument("--limit", type=int, help="max cases per pack, for quick tries")
    run_cmd.add_argument("--epochs", type=int, default=1, help="runs per case")
    run_cmd.add_argument("--log-dir", default="logs")
    run_cmd.add_argument("--failures", action="store_true", help="list failing cases")
    args = parser.parse_args(argv)
    # Piped output on Windows defaults to cp1252, which can't print Japanese or Vietnamese.
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    packs = PACKS
    if args.packs:
        wanted = set(args.packs.split(","))
        unknown = wanted - {p.name for p in PACKS}
        if unknown:
            parser.error(f"unknown packs: {', '.join(sorted(unknown))}")
        packs = [p for p in PACKS if p.name in wanted]

    result = run(
        args.target,
        packs=packs,
        log_dir=args.log_dir,
        limit=args.limit,
        epochs=args.epochs,
        display="none",
    )
    print(markdown(result, show_failures=args.failures))
