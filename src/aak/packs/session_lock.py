from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task

from aak.core.cases import load_cases, to_dataset
from aak.core.packs import Pack
from aak.core.target import Capability
from aak.inspect_bridge import drive_target_with_setup
from aak.scorers import no_forbidden_text

CASES = Path(str(files("aak.packs") / "data" / "session_lock.jsonl"))


@task
def session_lock(target_file: str) -> Task:
    return Task(
        name="platform.session_lock",
        dataset=to_dataset(load_cases(CASES), name="session_lock"),
        solver=drive_target_with_setup(target_file),
        scorer=no_forbidden_text(),
    )


PACK = Pack(
    name="platform.session_lock",
    description=(
        "A client holding the app's session token can't replace the app's instructions: the "
        "server keeps the session locked to the app's setup."
    ),
    kind="red_team",
    requires=frozenset({Capability.CLIENT_SETUP}),
    build=session_lock,
    taxonomy=(
        "OWASP LLM06:2026 Unbounded Consumption",
        "CWE-284 Improper Access Control",
    ),
)
