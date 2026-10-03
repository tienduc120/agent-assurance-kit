from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample

from aak.core.packs import Pack
from aak.inspect_bridge import drive_target
from aak.scorers import replied


@task
def smoke(target_file: str) -> Task:
    samples = [
        Sample(id="greet-en", input="Hello!"),
        Sample(id="greet-ja", input="こんにちは"),
        Sample(id="two-turns", input="Hi", metadata={"turns": ["Hi", "What can you do?"]}),
    ]
    return Task(
        name="smoke",
        dataset=MemoryDataset(samples, name="smoke"),
        solver=drive_target(target_file),
        scorer=replied(),
    )


PACK = Pack(
    name="smoke",
    description="The target answers every turn.",
    requires=frozenset(),
    build=smoke,
)
