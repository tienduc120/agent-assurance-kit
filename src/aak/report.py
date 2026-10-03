"""Turn a run into numbers people can read."""

from dataclasses import dataclass

from inspect_ai.log import EvalLog

from aak.run import RunResult


@dataclass(frozen=True)
class Row:
    pack: str
    check: str
    passed: int
    total: int
    failures: list[tuple[str, str]]  # (case id, explanation)


def rows(result: RunResult) -> list[Row]:
    out = []
    for log in result.logs:
        out.extend(_rows_for(log))
    return out


def _rows_for(log: EvalLog) -> list[Row]:
    samples = log.samples or []
    checks = [score.name for score in (log.results.scores if log.results else [])]
    out = []
    for check in checks:
        scored = [(s.id, s.scores[check]) for s in samples if s.scores and check in s.scores]
        failures = [(str(i), sc.explanation or "") for i, sc in scored if sc.value != "C"]
        out.append(Row(log.eval.task, check, len(scored) - len(failures), len(scored), failures))
    return out


def markdown(result: RunResult, show_failures: bool = False) -> str:
    lines = ["| Pack | Check | Passed |", "|---|---|---|"]
    for row in rows(result):
        lines.append(f"| {row.pack} | {row.check} | {row.passed}/{row.total} |")
    for d in result.not_applicable:
        lines.append(f"| {d.pack.name} | - | not applicable: {d.reason} |")
    if show_failures:
        for row in rows(result):
            for case_id, why in row.failures:
                lines.append(f"- `{row.pack}` {case_id} ({row.check}): {why}")
    return "\n".join(lines)
