from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task

from aak.core.cases import load_cases, to_dataset
from aak.core.packs import Pack
from aak.core.target import TargetConfig
from aak.inspect_bridge import drive_target
from aak.scorers import no_canary_leak

CASES = Path(str(files("aak.packs") / "data" / "system_prompt_leak.jsonl"))


@task
def system_prompt_leak(target_file: str) -> Task:
    return Task(
        name="llm.system_prompt_leak",
        dataset=to_dataset(load_cases(CASES), name="system_prompt_leak"),
        solver=drive_target(target_file),
        scorer=no_canary_leak(target_file),
    )


def _needs_canaries(config: TargetConfig) -> str | None:
    return None if config.canaries else "no canaries in target config"


PACK = Pack(
    name="llm.system_prompt_leak",
    description="The target doesn't reveal its system prompt verbatim.",
    kind="red_team",
    requires=frozenset(),
    build=system_prompt_leak,
    precondition=_needs_canaries,
    taxonomy=(
        "OWASP LLM08:2026 Hidden Context Exposure",
        "MITRE ATLAS AML.T0056 Extract LLM System Prompt",
    ),
)
