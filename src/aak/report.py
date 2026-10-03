"""Turn a run into numbers people can read."""

import re
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


@dataclass(frozen=True)
class AttackRate:
    category: str
    attempts: int
    succeeded: int

    @property
    def rate(self) -> float:
        return self.succeeded / self.attempts if self.attempts else 0.0


def attack_rates(result: RunResult) -> list[AttackRate]:
    """Attack success rate per risk category, over every run of every red-team case.

    An attack succeeded when its run failed the pack's checks. A pack mapped to several
    categories counts toward each of them.
    """
    packs = {p.name: p for p in PACKS}
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for log in result.logs:
        pack = packs.get(log.eval.task)
        if pack is None or pack.kind != "red_team":
            continue
        runs = [s for s in log.samples or [] if s.scores]
        succeeded = sum(any(sc.value != "C" for sc in s.scores.values()) for s in runs)
        for category in pack.taxonomy or (pack.name,):
            totals[category][0] += len(runs)
            totals[category][1] += succeeded
    return [AttackRate(c, a, s) for c, (a, s) in sorted(totals.items())]


TABLE_TEXT = {
    "en": {
        "header": "| Pack | Kind | Check | Passed |",
        "header_k": "| Pack | Kind | Check | Passed (all runs) | Passed every run (pass^k) |",
        "not_applicable": "not applicable",
        "risk_header": "| Risk category | Attacks | Succeeded | Attack success rate |",
        "evaluation": "evaluation",
        "red_team": "red_team",
    },
    "ja": {
        "header": "| パック | 種別 | チェック | 合格 |",
        "header_k": "| パック | 種別 | チェック | 合格（全実行） | 全回合格（pass^k） |",
        "not_applicable": "対象外",
        "risk_header": "| リスク分類 | 攻撃数 | 成功 | 攻撃成功率 |",
        "evaluation": "評価",
        "red_team": "レッドチーム",
    },
}

# Reasons are generated in English by pack selection; known patterns get a translation.
_REASONS_JA = [
    (re.compile(r"^target lacks: (.+)$"), r"対象に必要な機能がない: \1"),
    (re.compile(r"^target audience is (\w+)$"), r"対象の想定利用者が \1 である"),
    (re.compile(r"^no canaries in target config$"), "対象の設定にカナリアがない"),
    (re.compile(r"^disabled in target config$"), "対象の設定で無効化されている"),
]


def reason_text(reason: str, lang: str) -> str:
    if lang == "ja":
        for pattern, replacement in _REASONS_JA:
            if pattern.match(reason):
                return pattern.sub(replacement, reason)
    return reason


def markdown(result: RunResult, show_failures: bool = False, lang: str = "en") -> str:
    text = TABLE_TEXT[lang]
    table = rows(result)
    repeated = any(r.repeats > 1 for r in table)
    if repeated:
        lines = [text["header_k"], "|---|---|---|---|---|"]
        for r in table:
            lines.append(
                f"| {r.pack} | {text.get(r.kind, r.kind)} | {r.check} | {r.passed}/{r.total} "
                f"| {r.always_passed}/{r.cases} (k={r.repeats}) |"
            )
        gap = "| - |"
    else:
        lines = [text["header"], "|---|---|---|---|"]
        for r in table:
            lines.append(
                f"| {r.pack} | {text.get(r.kind, r.kind)} | {r.check} | {r.passed}/{r.total} |"
            )
        gap = "|"
    for d in result.not_applicable:
        kind = text.get(d.pack.kind, d.pack.kind)
        why = f"{text['not_applicable']}: {reason_text(d.reason, lang)}"
        lines.append(f"| {d.pack.name} | {kind} | - | {why} {gap}")
    rates = attack_rates(result)
    if rates:
        lines += ["", text["risk_header"]]
        lines.append("|---|---|---|---|")
        for r in rates:
            lines.append(f"| {r.category} | {r.attempts} | {r.succeeded} | {r.rate:.0%} |")
    if show_failures:
        for r in table:
            for case_id, why in r.failures:
                lines.append(f"- `{r.pack}` {case_id} ({r.check}): {why}")
    return "\n".join(lines)
