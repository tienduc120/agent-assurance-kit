"""aak run <target.yaml>: run every applicable pack and print the results.
aak judge <log>...: add LLM-judge scores to finished runs, without calling the target again.
aak labels export|compare: human labels, to measure how far the judge and rules can be trusted.
"""

import argparse
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

from aak import labels
from aak.core.target import load_target_config
from aak.packs import PACKS
from aak.report import markdown
from aak.report_doc import full_report, result_from_logs
from aak.run import RunResult, judge_log, run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aak")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="run the packs that apply to a target")
    run_cmd.add_argument("target", help="path to target.yaml")
    run_cmd.add_argument("--packs", help="comma-separated pack names (default: all)")
    run_cmd.add_argument("--limit", type=int, help="max cases per pack, for quick tries")
    run_cmd.add_argument("--epochs", type=int, default=1, help="runs per case")
    run_cmd.add_argument("--judge", help="judge target.yaml; adds rubric scores after the run")
    run_cmd.add_argument("--log-dir", default="logs")
    run_cmd.add_argument("--failures", action="store_true", help="list failing cases")
    run_cmd.add_argument("--report", help="also write a full Markdown report to this path")
    run_cmd.add_argument(
        "--no-excerpts", action="store_true", help="leave conversation text out of the report"
    )

    judge_cmd = sub.add_parser("judge", help="add judge scores to existing run logs")
    judge_cmd.add_argument("logs", nargs="+", help=".eval log files")
    judge_cmd.add_argument("--judge", required=True, help="judge target.yaml")
    judge_cmd.add_argument("--failures", action="store_true", help="list failing cases")

    report_cmd = sub.add_parser("report", help="write a full report from saved run logs")
    report_cmd.add_argument("target", help="the target.yaml the logs came from")
    report_cmd.add_argument("logs", nargs="+", help=".eval log files")
    report_cmd.add_argument("--out", required=True, help="Markdown file to write")
    report_cmd.add_argument("--no-excerpts", action="store_true")

    labels_cmd = sub.add_parser("labels", help="human labels for judge calibration")
    labels_sub = labels_cmd.add_subparsers(dest="action", required=True)
    export_cmd = labels_sub.add_parser("export", help="sample judged replies into a CSV")
    export_cmd.add_argument("logs", nargs="+", help="judged .eval log files")
    export_cmd.add_argument("--out", required=True, help="CSV to write")
    export_cmd.add_argument("-n", type=int, default=50, help="how many replies (default 50)")
    export_cmd.add_argument("--seed", type=int, default=0)
    compare_cmd = labels_sub.add_parser("compare", help="agreement of judge and rules with you")
    compare_cmd.add_argument("csv", help="labelled CSV")
    compare_cmd.add_argument("--disagreements", action="store_true", help="list them")

    args = parser.parse_args(argv)
    # Piped output on Windows defaults to cp1252, which can't print Japanese or Vietnamese.
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    if args.command == "report":
        config = load_target_config(args.target)
        result = result_from_logs(config, [read_eval_log(path) for path in args.logs])
        report = full_report(result, config, excerpts=not args.no_excerpts)
        Path(args.out).write_text(report, encoding="utf-8", newline="\n")
        print(f"Report written to {args.out}")
        return
    if args.command == "labels" and args.action == "export":
        logs = [read_eval_log(path) for path in args.logs]
        count = labels.export_labels(logs, Path(args.out), n=args.n, seed=args.seed)
        print(f"Wrote {count} replies to {args.out}. Fill in your_label with pass or fail.")
        return
    if args.command == "labels":
        agreements, no_verdict = labels.compare_labels(Path(args.csv))
        print(labels.markdown(agreements, no_verdict, disagreements=args.disagreements))
        return

    if args.command == "judge":
        logs = [judge_log(read_eval_log(path), args.judge) for path in args.logs]
        print(markdown(RunResult(decisions=[], logs=logs), show_failures=args.failures))
        return

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
        judge_file=args.judge,
        limit=args.limit,
        epochs=args.epochs,
        display="none",
    )
    print(markdown(result, show_failures=args.failures))
    if args.report:
        config = load_target_config(args.target)
        report = full_report(result, config, excerpts=not args.no_excerpts)
        Path(args.report).write_text(report, encoding="utf-8", newline="\n")
        print(f"\nReport written to {args.report}")
