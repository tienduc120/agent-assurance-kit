"""Pick the packs that apply to a target, run them, and keep the reasons for the rest."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from inspect_ai import eval as inspect_eval
from inspect_ai import score as inspect_score
from inspect_ai.log import EvalLog, write_eval_log

from aak.core.packs import Pack, PackDecision, select_packs
from aak.core.target import load_target_config
from aak.judge import llm_judge
from aak.packs import PACKS


@dataclass(frozen=True)
class RunResult:
    decisions: list[PackDecision]
    logs: list[EvalLog]

    @property
    def not_applicable(self) -> list[PackDecision]:
        return [d for d in self.decisions if not d.runs]


def judge_log(log: EvalLog, judge_file: str | Path, packs: Sequence[Pack] = PACKS) -> EvalLog:
    """Add judge scores to a finished log, if its pack has a rubric. Saves the log in place."""
    pack = next((p for p in packs if p.name == log.eval.task), None)
    if pack is None or pack.judge_rubric is None or log.status != "success":
        return log
    judged = inspect_score(
        log, llm_judge(pack.judge_rubric, str(judge_file)), action="append", display="none"
    )
    write_eval_log(judged)
    return judged


def run(
    target_file: str | Path,
    *,
    packs: Sequence[Pack] = PACKS,
    log_dir: str = "logs",
    judge_file: str | Path | None = None,
    **eval_args: Any,
) -> RunResult:
    config = load_target_config(target_file)
    decisions = select_packs(config, packs)
    tasks = [d.pack.build(str(target_file)) for d in decisions if d.runs]
    logs = inspect_eval(tasks, model="none", log_dir=log_dir, **eval_args) if tasks else []
    # A separate pass, so a local target and a local judge never share the GPU at once.
    if judge_file:
        logs = [judge_log(log, judge_file, packs) for log in logs]
    return RunResult(decisions, logs)
