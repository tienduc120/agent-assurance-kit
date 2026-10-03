"""A full Markdown report for one run: scope, method, results, findings, limitations.

Section order follows the J-AISI red-teaming guide: what was tested and how, what was found,
and what the evidence can't show. What was *not* tested is listed explicitly, because an
absent result is easy to misread as a pass.
"""

from datetime import date

from inspect_ai.log import EvalLog

from aak import __version__
from aak.core.packs import select_packs
from aak.core.target import TargetConfig
from aak.judge import JUDGE_SCORER
from aak.packs import PACKS
from aak.report import attack_rates, markdown, rows
from aak.run import RunResult


def result_from_logs(config: TargetConfig, logs: list[EvalLog]) -> RunResult:
    """Rebuild a run from saved logs, e.g. to re-report after judging, without the target."""
    present = {log.eval.task for log in logs}
    decisions = [d for d in select_packs(config, PACKS) if not d.runs or d.pack.name in present]
    return RunResult(decisions, logs)


MAX_FINDINGS_PER_PACK = 20


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _findings(result: RunResult, excerpts: bool) -> list[str]:
    lines: list[str] = []
    kinds = {p.name: p.kind for p in PACKS}
    for log in result.logs:
        failed = []
        for sample in log.samples or []:
            for check, score in (sample.scores or {}).items():
                if score.value != "C":
                    failed.append((sample, check, score.explanation or ""))
        if not failed:
            continue
        repeated = max((s.epoch for s in log.samples or []), default=1) > 1
        lines += ["", f"### {log.eval.task} ({kinds.get(log.eval.task, '?')})", ""]
        for sample, check, why in failed[:MAX_FINDINGS_PER_PACK]:
            run = f"#{sample.epoch}" if repeated else ""
            lines.append(f"- **{sample.id}{run}** · `{check}`: {_clip(why, 200)}")
            turns = sample.store.get("Transcript:turns") or []
            if excerpts and turns:
                lines.append(f"  > User: {_clip(turns[-1]['user'], 160)}  ")
                lines.append(f"  > Reply: {_clip(turns[-1]['reply']['text'], 240)}")
        if len(failed) > MAX_FINDINGS_PER_PACK:
            lines.append(f"- … and {len(failed) - MAX_FINDINGS_PER_PACK} more (see the logs)")
    return lines


def full_report(
    result: RunResult,
    config: TargetConfig,
    *,
    excerpts: bool = True,
    on: date | None = None,
) -> str:
    table = rows(result)
    rates = attack_rates(result)
    judged = any(r.check == JUDGE_SCORER for r in table)
    repeats = max((r.repeats for r in table), default=1)
    evaluation = [r for r in table if r.kind == "evaluation" and r.check != JUDGE_SCORER]
    eval_passed = sum(r.passed for r in evaluation)
    eval_total = sum(r.total for r in evaluation)
    run_packs = [d for d in result.decisions if d.runs]

    lines = [
        f"# Assurance report: {config.name}",
        "",
        "| | |",
        "|---|---|",
        f"| **Target** | `{config.name}` via the `{config.adapter}` adapter |",
        f"| **Audience** | {config.audience} |",
        f"| **Date** | {(on or date.today()).isoformat()} |",
        f"| **Kit** | agent-assurance-kit {__version__} |",
        f"| **Runs per case** | {repeats} |",
        f"| **LLM judge** | {'used (see limitations)' if judged else 'not used'} |",
        "",
        "## Summary",
        "",
    ]
    if eval_total:
        # The rule pass rate reads like a quality score; it isn't one, so say so up front.
        lines.append(
            f"- **Evaluation:** {eval_passed}/{eval_total} rule checks passed "
            f"({eval_passed / eval_total:.0%}). This is an upper bound: rules can't judge "
            "facts, tone, or whether a person in difficulty was taken seriously. Human review "
            "of the transcripts is needed before calling the replies good."
        )
    if rates:
        worst = max(rates, key=lambda r: r.rate)
        lines.append(
            f"- **Red team:** highest attack success rate {worst.rate:.0%} "
            f"({worst.succeeded}/{worst.attempts}) in {worst.category}."
        )
    else:
        lines.append("- **Red team:** no red-team pack applied to this target.")
    if result.not_applicable:
        lines.append(f"- **Not tested:** {len(result.not_applicable)} packs (see Scope).")

    capabilities = sorted(c.value for c in config.enabled_capabilities) or ["none declared"]
    lines += [
        "",
        "## Scope",
        "",
        f"Declared capabilities: {', '.join(capabilities)}.",
        "",
        "| Pack | Kind | Cases |",
        "|---|---|---|",
    ]
    cases = {r.pack: r.cases for r in table}
    for d in run_packs:
        lines.append(f"| {d.pack.name} | {d.pack.kind} | {cases.get(d.pack.name, '-')} |")
    if result.not_applicable:
        lines += ["", "**Not tested.** An absent result is not a pass:", ""]
        for d in result.not_applicable:
            lines.append(f"- `{d.pack.name}` ({d.pack.kind}): {d.reason}")

    lines += [
        "",
        "## Method",
        "",
        f"- Black-box: the kit reached the target only through its `{config.adapter}` adapter,",
        "  as a user would; no target code was read or changed.",
        "- Cases are scripted conversations in Japanese, English and Vietnamese.",
        "- Scoring: deterministic rule checks (text, action log, canaries)"
        + (", plus an LLM judge grading against written rubrics." if judged else "."),
        f"- Each case ran {repeats} time(s); with more than one, the table shows how many cases"
        if repeats > 1
        else "- Each case ran once; repeat runs (`--epochs`) are needed to show reliability.",
    ]
    if repeats > 1:
        lines.append("  passed every run (pass^k).")

    lines += ["", "## Results", "", markdown(result)]
    findings = _findings(result, excerpts)
    lines += ["", "## Findings", ""]
    lines += findings[1:] if findings else ["No check failed."]

    lines += [
        "",
        "## Limitations",
        "",
        "- Rule checks find only what they look for; a reply can pass every rule and still be",
        "  wrong, unkind or unsafe. Read the transcripts before relying on a pass rate.",
        "- Results hold for the tested configuration and date. Re-run after any change to the",
        "  model, prompt, tools or guardrails, including normal-use packs, not only attacks.",
        "- Rates come from small samples; a few cases either way are within run-to-run noise.",
    ]
    if judged:
        lines += [
            "- LLM-judge verdicts are only as good as the judge's measured agreement with human",
            "  labels (`aak labels compare`). Without that, treat them as indicative.",
        ]
    return "\n".join(lines) + "\n"
