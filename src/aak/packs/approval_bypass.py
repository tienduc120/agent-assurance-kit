from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task

from aak.core.cases import load_cases, to_dataset
from aak.core.packs import Pack
from aak.core.target import Capability
from aak.inspect_bridge import drive_target
from aak.scorers import no_forbidden_actions

CASES = Path(str(files("aak.packs") / "data" / "approval_bypass.jsonl"))


@task
def approval_bypass(target_file: str) -> Task:
    return Task(
        name="agent.approval_bypass",
        dataset=to_dataset(load_cases(CASES), name="approval_bypass"),
        solver=drive_target(target_file),
        scorer=no_forbidden_actions(),
    )


PACK = Pack(
    name="agent.approval_bypass",
    description=(
        "Actions that need a person's approval can't be talked through without it: not by "
        "claimed approval, urgency, posing as staff, or naming the tool directly."
    ),
    kind="red_team",
    requires=frozenset({Capability.ACTIONS, Capability.ACTION_LOG, Capability.ROLES}),
    build=approval_bypass,
    taxonomy=(
        "OWASP ASI03:2026 Identity and Privilege Abuse",
        "OWASP LLM03:2026 Excessive Agency",
    ),
)
