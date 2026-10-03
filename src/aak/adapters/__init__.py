"""Adapters turn a target.yaml into something the kit can talk to."""

from collections.abc import Callable

from aak.adapters.gemini_live import GeminiLiveTarget
from aak.adapters.mock import MockTarget
from aak.adapters.openai_compatible import OpenAICompatibleTarget
from aak.adapters.scripted import ScriptedTarget
from aak.core.target import Target, TargetConfig

_ADAPTERS: dict[str, Callable[[TargetConfig], Target]] = {
    "gemini-live": GeminiLiveTarget.from_config,
    "mock": MockTarget.from_config,
    "openai-compatible": OpenAICompatibleTarget.from_config,
    "scripted": ScriptedTarget.from_config,
}


def build_target(config: TargetConfig) -> Target:
    try:
        factory = _ADAPTERS[config.adapter]
    except KeyError:
        known = ", ".join(sorted(_ADAPTERS))
        raise ValueError(f"unknown adapter {config.adapter!r} (known: {known})") from None
    return factory(config)
