from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task

from aak.core.cases import load_cases, to_dataset
from aak.core.packs import Pack
from aak.core.target import TargetConfig
from aak.inspect_bridge import drive_target
from aak.scorers import no_links, no_pii_request, replied, reply_language, short_sentences

CASES = Path(str(files("aak.packs") / "data" / "child_conversation.jsonl"))


@task
def child_conversation(target_file: str) -> Task:
    return Task(
        name="child.conversation",
        dataset=to_dataset(load_cases(CASES), name="child_conversation"),
        solver=drive_target(target_file),
        scorer=[replied(), reply_language(), short_sentences(), no_links(), no_pii_request()],
    )


def _for_children(config: TargetConfig) -> str | None:
    return None if config.audience == "children" else f"target audience is {config.audience}"


PACK = Pack(
    name="child.conversation",
    description=(
        "Everyday questions from young children: replies in the child's language, in short "
        "sentences, with no links and no requests for personal information."
    ),
    requires=frozenset(),
    build=child_conversation,
    precondition=_for_children,
)
