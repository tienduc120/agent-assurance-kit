"""Turn a run into numbers people can read."""

from collections import defaultdict
from dataclasses import dataclass

from inspect_ai.log import EvalLog

from aak.packs import PACKS
from aak.run import RunResult


@dataclass(frozen=True)
class Row:
    pack: str
    kind: str
    check: str
    passed: int  # passing runs, over every case and repeat
    total: int
    cases: int
    always_passed: int  # cases that passed on every repeat: pass^k with k = repeats
    repeats: int
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
    repeats = max((s.epoch for s in samples), default=1)
    out = []
    for check in checks:
        by_case: dict[str, list[bool]] = defaultdict(list)
        failures = []
        for s in samples:
            if not s.scores or check not in s.scores:
                continue
            score = s.scores[check]
            by_case[str(s.id)].append(score.value == "C")
            if score.value != "C":
                case = f"{s.id}#{s.epoch}" if repeats > 1 else str(s.id)
                failures.append((case, score.explanation or ""))
        runs = [ok for results in by_case.values() for ok in results]
        out.append(
            Row(
                pack=log.eval.task,
                kind=kind,
                check=check,
                passed=sum(runs),
                total=len(runs),
                cases=len(by_case),
                always_passed=sum(all(results) for results in by_case.values()),
                repeats=repeats,
                failures=failures,
            )
        )
    return out


def markdown(result: RunResult, show_failures: bool = False) -> str:
    table = rows(result)
    repeated = any(r.repeats > 1 for r in table)
    if repeated:
        lines = [
            "| Pack | Kind | Check | Passed (all runs) | Passed every run (pass^k) |",
            "|---|---|---|---|---|",
        ]
        for r in table:
            lines.append(
                f"| {r.pack} | {r.kind} | {r.check} | {r.passed}/{r.total} "
                f"| {r.always_passed}/{r.cases} (k={r.repeats}) |"
            )
        gap = "| - |"
    else:
        lines = ["| Pack | Kind | Check | Passed |", "|---|---|---|---|"]
        for r in table:
            lines.append(f"| {r.pack} | {r.kind} | {r.check} | {r.passed}/{r.total} |")
        gap = "|"
    for d in result.not_applicable:
        lines.append(f"| {d.pack.name} | {d.pack.kind} | - | not applicable: {d.reason} {gap}")
    if show_failures:
        for r in table:
            for case_id, why in r.failures:
                lines.append(f"- `{r.pack}` {case_id} ({r.check}): {why}")
    return "\n".join(lines)
