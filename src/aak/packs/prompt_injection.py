from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task

from aak.core.cases import load_cases, to_dataset
from aak.core.packs import Pack
from aak.inspect_bridge import drive_target
from aak.scorers import no_forbidden_text

CASES = Path(str(files("aak.packs") / "data" / "prompt_injection.jsonl"))


@task
def prompt_injection(target_file: str) -> Task:
    return Task(
        name="llm.prompt_injection",
        dataset=to_dataset(load_cases(CASES), name="prompt_injection"),
        solver=drive_target(target_file),
        scorer=no_forbidden_text(),
    )


PACK = Pack(
    name="llm.prompt_injection",
    description="The target ignores instructions injected by the user or hidden in content.",
    kind="red_team",
    requires=frozenset(),
    build=prompt_injection,
    taxonomy=(
        "OWASP LLM01:2026 Prompt Injection",
        "OWASP ASI01:2026 Agent Goal Hijack",
        "MITRE ATLAS AML.T0051.000 Direct Prompt Injection",
        "MITRE ATLAS AML.T0054 LLM Jailbreak",
    ),
)
