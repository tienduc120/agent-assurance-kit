from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task

from aak.core.cases import load_cases, to_dataset
from aak.core.packs import Pack
from aak.core.target import Capability
from aak.inspect_bridge import drive_target
from aak.scorers import no_forbidden_actions

CASES = Path(str(files("aak.packs") / "data" / "unauthorized_action.jsonl"))


@task
def unauthorized_action(target_file: str) -> Task:
    return Task(
        name="agent.unauthorized_action",
        dataset=to_dataset(load_cases(CASES), name="unauthorized_action"),
        solver=drive_target(target_file),
        scorer=no_forbidden_actions(),
    )


PACK = Pack(
    name="agent.unauthorized_action",
    description="The target won't act on, or reveal, records the caller doesn't own.",
    kind="red_team",
    requires=frozenset({Capability.ACTIONS, Capability.ACTION_LOG, Capability.USER_DATA}),
    build=unauthorized_action,
)
