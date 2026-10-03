from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task

from aak.core.cases import load_cases, to_dataset
from aak.core.packs import Pack
from aak.inspect_bridge import drive_target
from aak.packs.child_conversation import for_children
from aak.scorers import no_links, no_pii_request, points_to_help, replied, reply_language

CASES = Path(str(files("aak.packs") / "data" / "child_safety.jsonl"))


@task
def child_safety(target_file: str) -> Task:
    return Task(
        name="child.safety",
        dataset=to_dataset(load_cases(CASES), name="child_safety"),
        solver=drive_target(target_file),
        scorer=[replied(), reply_language(), points_to_help(), no_links(), no_pii_request()],
    )


PACK = Pack(
    name="child.safety",
    description=(
        "Risky situations a child may raise (danger, harm, strangers, emergencies, secrets, "
        "money): the reply points the child to a trusted adult or emergency help."
    ),
    kind="evaluation",
    requires=frozenset(),
    build=child_safety,
    precondition=for_children,
    judge_rubric="child_safety",
)
