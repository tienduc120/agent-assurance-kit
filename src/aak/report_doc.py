"""A full Markdown report for one run, in English or Japanese.

Section order follows the J-AISI red-teaming guide: what was tested and how, what was found,
and what the evidence can't show. What was *not* tested is listed explicitly, because an
absent result is easy to misread as a pass. Pack, check and category names stay as they are
in every language: they are identifiers.
"""

from datetime import date

from inspect_ai.log import EvalLog

from aak import __version__
from aak.core.packs import select_packs
from aak.core.target import TargetConfig
from aak.judge import JUDGE_SCORER
from aak.packs import PACKS
from aak.report import TABLE_TEXT, attack_rates, markdown, reason_text, rows
from aak.run import RunResult

MAX_FINDINGS_PER_PACK = 20

TEXT = {
    "en": {
        "title": "# Assurance report: {name}",
        "target": "| **Target** | `{name}` via the `{adapter}` adapter |",
        "audience": "| **Audience** | {audience} |",
        "date": "| **Date** | {date} |",
        "kit": "| **Kit** | agent-assurance-kit {version} |",
        "runs": "| **Runs per case** | {k} |",
        "judge_row": "| **LLM judge** | {judge} |",
        "judge_used": "used (see limitations)",
        "judge_unused": "not used",
        "summary": "## Summary",
        "eval_summary": (
            "- **Evaluation:** {p}/{t} rule checks passed ({pct}). This is an upper bound: "
            "rules can't judge facts, tone, or whether a person in difficulty was taken "
            "seriously. Human review of the transcripts is needed before calling the replies "
            "good."
        ),
        "red_summary": (
            "- **Red team:** highest attack success rate {rate} ({s}/{a}) in {category}."
        ),
        "red_none": "- **Red team:** no red-team pack applied to this target.",
        "not_tested_summary": "- **Not tested:** {n} packs (see Scope).",
        "scope": "## Scope",
        "capabilities": "Declared capabilities: {caps}.",
        "none_declared": "none declared",
        "scope_header": "| Pack | Kind | Cases |",
        "not_tested": "**Not tested.** An absent result is not a pass:",
        "method": "## Method",
        "method_lines": [
            "- Black-box: the kit reached the target only through its `{adapter}` adapter, as a",
            "  user would; no target code was read or changed.",
            "- Cases are scripted conversations in Japanese, English and Vietnamese.",
        ],
        "scoring": "- Scoring: deterministic rule checks (text, action log, canaries).",
        "scoring_judged": (
            "- Scoring: deterministic rule checks (text, action log, canaries), plus an LLM "
            "judge grading against written rubrics."
        ),
        "repeats_k": (
            "- Each case ran {k} times; the table shows how many cases passed every run (pass^k)."
        ),
        "repeats_1": (
            "- Each case ran once; repeat runs (`--epochs`) are needed to show reliability."
        ),
        "results": "## Results",
        "findings": "## Findings",
        "no_failures": "No check failed.",
        "user": "User",
        "reply": "Reply",
        "more": "- … and {n} more (see the logs)",
        "limitations": "## Limitations",
        "limitation_lines": [
            "- Rule checks find only what they look for; a reply can pass every rule and still be",
            "  wrong, unkind or unsafe. Read the transcripts before relying on a pass rate.",
            "- Results hold for the tested configuration and date. Re-run after any change to the",
            "  model, prompt, tools or guardrails, including normal-use packs, not only attacks.",
            "- Rates come from small samples; a few cases either way are within run-to-run noise.",
        ],
        "judge_limitation": [
            "- LLM-judge verdicts are only as good as the judge's measured agreement with human",
            "  labels (`aak labels compare`). Without that, treat them as indicative.",
        ],
        "audiences": {"children": "children", "general": "general"},
    },
    "ja": {
        "title": "# AIアシュアランス評価報告書: {name}",
        "target": "| **評価対象** | `{name}`（`{adapter}` アダプタ経由） |",
        "audience": "| **想定利用者** | {audience} |",
        "date": "| **実施日** | {date} |",
        "kit": "| **評価ツール** | agent-assurance-kit {version} |",
        "runs": "| **各ケースの実行回数** | {k} |",
        "judge_row": "| **LLM判定** | {judge} |",
        "judge_used": "使用（制約事項を参照）",
        "judge_unused": "不使用",
        "summary": "## 概要",
        "eval_summary": (
            "- **評価:** ルールチェック {p}/{t} 件に合格（{pct}）。これは上限値であり、"
            "ルールでは事実の正誤、語調、困っている相手を真剣に受け止めたかどうかは判定できない。"
            "応答の良否を判断する前に、会話記録の人によるレビューが必要である。"
        ),
        "red_summary": (
            "- **レッドチーム:** 攻撃成功率の最大値は {rate}（{s}/{a}）、分類: {category}。"
        ),
        "red_none": "- **レッドチーム:** この対象に適用されるレッドチームのパックはない。",
        "not_tested_summary": "- **未実施:** {n} パック（「評価範囲」を参照）。",
        "scope": "## 評価範囲",
        "capabilities": "宣言された機能: {caps}。",
        "none_declared": "宣言なし",
        "scope_header": "| パック | 種別 | ケース数 |",
        "not_tested": "**未実施の項目。** 結果がないことは合格を意味しない:",
        "method": "## 評価方法",
        # One output line per bullet: Markdown renders a line break as a space, which is
        # wrong between Japanese characters.
        "method_lines": [
            "- ブラックボックス評価: 対象には `{adapter}` アダプタを通じて利用者と同じ立場でのみ"
            "アクセスし、対象のコードの閲覧・変更は行っていない。",
            "- テストケースは日本語・英語・ベトナム語のスクリプト化された会話である。",
        ],
        "scoring": "- 採点: 決定的なルールチェック（テキスト、アクションログ、カナリア）。",
        "scoring_judged": (
            "- 採点: 決定的なルールチェック（テキスト、アクションログ、カナリア）、"
            "および記述されたルーブリックに基づくLLM判定。"
        ),
        "repeats_k": "- 各ケースを {k} 回実行し、全回で合格したケース数（pass^k）を表に示す。",
        "repeats_1": (
            "- 各ケースは1回のみ実行した。信頼性を示すには反復実行（`--epochs`）が必要である。"
        ),
        "results": "## 結果",
        "findings": "## 指摘事項",
        "no_failures": "不合格となったチェックはない。",
        "user": "利用者",
        "reply": "応答",
        "more": "- … ほか {n} 件（ログを参照）",
        "limitations": "## 制約事項",
        "limitation_lines": [
            "- ルールチェックは定めた観点しか検出しない。全ルールに合格しても、誤った、不親切な、"
            "または危険な応答である可能性がある。合格率に依拠する前に会話記録を確認すること。",
            "- 結果は評価した構成と実施日に限り有効である。モデル、プロンプト、ツール、"
            "ガードレールを変更した場合は、攻撃系に加えて通常利用のパックも再実行すること。",
            "- 比率は小さな標本に基づく。数件程度の差は実行ごとのばらつきの範囲内である。",
        ],
        "judge_limitation": [
            "- LLM判定の信頼性は、人手ラベルとの一致度（`aak labels compare`）で測定された"
            "範囲に限られる。測定がない場合は参考値として扱うこと。",
        ],
        "audiences": {"children": "子ども", "general": "一般"},
    },
}


def result_from_logs(config: TargetConfig, logs: list[EvalLog]) -> RunResult:
    """Rebuild a run from saved logs, e.g. to re-report after judging, without the target."""
    present = {log.eval.task for log in logs}
    decisions = [d for d in select_packs(config, PACKS) if not d.runs or d.pack.name in present]
    return RunResult(decisions, logs)


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _findings(result: RunResult, excerpts: bool, lang: str) -> list[str]:
    t, kinds = TEXT[lang], TABLE_TEXT[lang]
    pack_kind = {p.name: p.kind for p in PACKS}
    lines: list[str] = []
    for log in result.logs:
        failed = [
            (sample, check, score.explanation or "")
            for sample in log.samples or []
            for check, score in (sample.scores or {}).items()
            if score.value != "C"
        ]
        if not failed:
            continue
        repeated = max((s.epoch for s in log.samples or []), default=1) > 1
        kind = pack_kind.get(log.eval.task, "?")
        lines += ["", f"### {log.eval.task} ({kinds.get(kind, kind)})", ""]
        for sample, check, why in failed[:MAX_FINDINGS_PER_PACK]:
            run = f"#{sample.epoch}" if repeated else ""
            lines.append(f"- **{sample.id}{run}** · `{check}`: {_clip(why, 200)}")
            turns = sample.store.get("Transcript:turns") or []
            if excerpts and turns:
                lines.append(f"  > {t['user']}: {_clip(turns[-1]['user'], 160)}  ")
                lines.append(f"  > {t['reply']}: {_clip(turns[-1]['reply']['text'], 240)}")
        if len(failed) > MAX_FINDINGS_PER_PACK:
            lines.append(t["more"].format(n=len(failed) - MAX_FINDINGS_PER_PACK))
    return lines


def full_report(
    result: RunResult,
    config: TargetConfig,
    *,
    excerpts: bool = True,
    on: date | None = None,
    lang: str = "en",
) -> str:
    t, kinds = TEXT[lang], TABLE_TEXT[lang]
    table = rows(result)
    rates = attack_rates(result)
    judged = any(r.check == JUDGE_SCORER for r in table)
    repeats = max((r.repeats for r in table), default=1)
    evaluation = [r for r in table if r.kind == "evaluation" and r.check != JUDGE_SCORER]
    eval_passed = sum(r.passed for r in evaluation)
    eval_total = sum(r.total for r in evaluation)

    lines = [
        t["title"].format(name=config.name),
        "",
        "| | |",
        "|---|---|",
        t["target"].format(name=config.name, adapter=config.adapter),
        t["audience"].format(audience=t["audiences"].get(config.audience, config.audience)),
        t["date"].format(date=(on or date.today()).isoformat()),
        t["kit"].format(version=__version__),
        t["runs"].format(k=repeats),
        t["judge_row"].format(judge=t["judge_used"] if judged else t["judge_unused"]),
        "",
        t["summary"],
        "",
    ]
    if eval_total:
        # The rule pass rate reads like a quality score; it isn't one, so say so up front.
        pct = f"{eval_passed / eval_total:.0%}"
        lines.append(t["eval_summary"].format(p=eval_passed, t=eval_total, pct=pct))
    if rates:
        worst = max(rates, key=lambda r: r.rate)
        lines.append(
            t["red_summary"].format(
                rate=f"{worst.rate:.0%}",
                s=worst.succeeded,
                a=worst.attempts,
                category=worst.category,
            )  # fmt: skip
        )
    else:
        lines.append(t["red_none"])
    if result.not_applicable:
        lines.append(t["not_tested_summary"].format(n=len(result.not_applicable)))

    capabilities = sorted(c.value for c in config.enabled_capabilities) or [t["none_declared"]]
    lines += [
        "",
        t["scope"],
        "",
        t["capabilities"].format(caps=", ".join(capabilities)),
        "",
        t["scope_header"],
        "|---|---|---|",
    ]
    cases = {r.pack: r.cases for r in table}
    for d in (d for d in result.decisions if d.runs):
        kind = kinds.get(d.pack.kind, d.pack.kind)
        lines.append(f"| {d.pack.name} | {kind} | {cases.get(d.pack.name, '-')} |")
    if result.not_applicable:
        lines += ["", t["not_tested"], ""]
        for d in result.not_applicable:
            kind = kinds.get(d.pack.kind, d.pack.kind)
            lines.append(f"- `{d.pack.name}` ({kind}): {reason_text(d.reason, lang)}")

    lines += ["", t["method"], ""]
    lines += [line.format(adapter=config.adapter) for line in t["method_lines"]]
    lines.append(t["scoring_judged"] if judged else t["scoring"])
    lines.append(t["repeats_k"].format(k=repeats) if repeats > 1 else t["repeats_1"])

    lines += ["", t["results"], "", markdown(result, lang=lang)]
    findings = _findings(result, excerpts, lang)
    lines += ["", t["findings"], ""]
    lines += findings[1:] if findings else [t["no_failures"]]

    lines += ["", t["limitations"], ""] + t["limitation_lines"]
    if judged:
        lines += t["judge_limitation"]
    return "\n".join(lines) + "\n"
