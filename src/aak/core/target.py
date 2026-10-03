"""What the kit knows about a target: its config, its capabilities, and how to talk to it."""

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Capability(StrEnum):
    """Things a target may be able to do. Packs require them; targets declare them."""

    VOICE = "voice"  # takes spoken input
    WEB_SEARCH = "web_search"  # pulls in outside content at runtime
    ACTIONS = "actions"  # can change state: book, cancel, send, pay
    ACTION_LOG = "action_log"  # the kit can see which actions were taken
    USER_DATA = "user_data"  # holds data about more than one user
    ROLES = "roles"  # treats some users (staff, owner) differently


class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class Reply(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    tool_calls: list[ToolCall] = Field(default_factory=list)


class Session(Protocol):
    """One conversation. Targets keep state per session, so each test case gets its own."""

    async def send(self, text: str) -> Reply: ...

    async def close(self) -> None: ...


class Target(Protocol):
    name: str

    async def open_session(self) -> Session: ...


class PackSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    disable: list[str] = Field(default_factory=list)


class TargetConfig(BaseModel):
    """Contents of a target.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    adapter: str
    # Domain packs (e.g. child safety) only apply to targets built for that audience.
    audience: Literal["general", "children"] = "general"
    options: dict[str, Any] = Field(default_factory=dict)
    # Undeclared counts as false, so packs needing it are reported as not applicable.
    capabilities: dict[Capability, bool] = Field(default_factory=dict)
    # Distinctive phrases from the target's system prompt; a reply containing one is a leak.
    canaries: list[str] = Field(default_factory=list)
    packs: PackSettings = Field(default_factory=PackSettings)

    @property
    def enabled_capabilities(self) -> frozenset[Capability]:
        return frozenset(c for c, on in self.capabilities.items() if on)


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_target_config(path: str | Path, use_local: bool = True) -> TargetConfig:
    """Load target.yaml, overlaid with target.local.yaml if present.

    The local file is gitignored: it holds what a public repo must not, such as canaries
    taken from a private system prompt. Tests pass use_local=False so they see only what CI
    sees.
    """
    path = Path(path)
    data = _read_yaml(path)
    local = path.with_name(f"{path.stem}.local.yaml")
    if use_local and local.exists():
        for key, value in _read_yaml(local).items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
    # Paths in options are relative to the target.yaml, not to wherever the kit runs.
    options = data.get("options") or {}
    for key, value in options.items():
        if key.endswith("_file") and isinstance(value, str):
            options[key] = str((path.parent / value).resolve())
    return TargetConfig.model_validate(data)
