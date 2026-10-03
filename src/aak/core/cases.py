"""Test cases: one JSON object per line, validated before any run."""

from pathlib import Path
from typing import Literal

from inspect_ai.dataset import MemoryDataset, Sample
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aak.core.target import ToolCall
from aak.text import Lang


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    lang: Literal["ja", "en", "vi", "other"]  # language the user writes in
    turns: list[str] = Field(min_length=1)
    # Languages the final reply may use; defaults to `lang`. Required when lang is "other".
    reply_lang: list[Lang] = Field(default_factory=list)
    forbidden_actions: list[ToolCall] = Field(default_factory=list)
    # Never put a forbidden string verbatim in the turns, or a reply that just quotes the
    # attack while refusing would count as a failure.
    forbidden_text: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _other_needs_reply_lang(self) -> Case:
        if self.lang == "other" and not self.reply_lang:
            raise ValueError("lang 'other' needs reply_lang")
        return self

    @property
    def allowed_reply_langs(self) -> list[Lang]:
        return self.reply_lang or [self.lang]


def load_cases(path: Path) -> list[Case]:
    cases = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            cases.append(Case.model_validate_json(line))
        except ValidationError as e:
            raise ValueError(f"{path.name}:{line_no}: {e}") from e
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path.name}: duplicate case ids")
    return cases


def to_dataset(cases: list[Case], name: str) -> MemoryDataset:
    samples = [
        Sample(
            id=c.id,
            input=c.turns[0],
            metadata={
                "turns": c.turns,
                "forbidden_actions": [a.model_dump() for a in c.forbidden_actions],
                "forbidden_text": c.forbidden_text,
                "lang": c.lang,
                "reply_lang": c.allowed_reply_langs,
                "tags": c.tags,
            },
        )
        for c in cases
    ]
    return MemoryDataset(samples, name=name)
