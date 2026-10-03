"""Turn a run into numbers people can read."""

from dataclasses import dataclass

from inspect_ai.log import EvalLog

from aak.packs import PACKS
from aak.run import RunResult


@dataclass(frozen=True)
class Row:
    pack: str
    kind: str
    check: str
    passed: int
    total: int
    failures: list[tuple[str, str]]  # (case id, explanation)


def rows(result: RunResult) -> list[Row]:
    kinds = {p.name: p.kind for p in PACKS}
    out = []
    for log in result.logs:
        out.extend(_rows_for(log, kinds.get(log.eval.task, "?")))
    return out


def _rows_for(log: EvalLog, kind: str) -> list[Row]:
    samples = log.samples or []
    checks = [score.name for score in (log.results.scores if log.results else [])]
    out = []
    for check in checks:
        scored = [(s.id, s.scores[check]) for s in samples if s.scores and check in s.scores]
        failures = [(str(i), sc.explanation or "") for i, sc in scored if sc.value != "C"]
        passed = len(scored) - len(failures)
        out.append(Row(log.eval.task, kind, check, passed, len(scored), failures))
    return out


def markdown(result: RunResult, show_failures: bool = False) -> str:
    lines = ["| Pack | Kind | Check | Passed |", "|---|---|---|---|"]
    for row in rows(result):
        lines.append(f"| {row.pack} | {row.kind} | {row.check} | {row.passed}/{row.total} |")
    for d in result.not_applicable:
        lines.append(f"| {d.pack.name} | {d.pack.kind} | - | not applicable: {d.reason} |")
    if show_failures:
        for row in rows(result):
            for case_id, why in row.failures:
                lines.append(f"- `{row.pack}` {case_id} ({row.check}): {why}")
    return "\n".join(lines)
