"""Pick the packs that apply to a target, run them, and keep the reasons for the rest."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from inspect_ai import eval as inspect_eval
from inspect_ai.log import EvalLog

from aak.core.packs import Pack, PackDecision, select_packs
from aak.core.target import load_target_config
from aak.packs import PACKS


@dataclass(frozen=True)
class RunResult:
    decisions: list[PackDecision]
    logs: list[EvalLog]

    @property
    def not_applicable(self) -> list[PackDecision]:
        return [d for d in self.decisions if not d.runs]


def run(
    target_file: str | Path,
    *,
    packs: Sequence[Pack] = PACKS,
    log_dir: str = "logs",
    **eval_args: Any,
) -> RunResult:
    config = load_target_config(target_file)
    decisions = select_packs(config, packs)
    tasks = [d.pack.build(str(target_file)) for d in decisions if d.runs]
    logs = inspect_eval(tasks, model="none", log_dir=log_dir, **eval_args) if tasks else []
    return RunResult(decisions, logs)
