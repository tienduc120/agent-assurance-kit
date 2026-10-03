"""Test packs and the rule that decides which ones apply to a target."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from inspect_ai import Task

from aak.core.target import Capability, TargetConfig


@dataclass(frozen=True)
class Pack:
    name: str
    description: str
    requires: frozenset[Capability]
    build: Callable[[str], Task]  # target.yaml path -> Inspect task
    # Anything else the pack needs from the config; returns why it can't run, or None.
    precondition: Callable[[TargetConfig], str | None] | None = None


@dataclass(frozen=True)
class PackDecision:
    pack: Pack
    runs: bool
    reason: str = ""  # why it doesn't run; reported, never dropped


def select_packs(config: TargetConfig, packs: Iterable[Pack]) -> list[PackDecision]:
    packs = list(packs)
    unknown = set(config.packs.disable) - {p.name for p in packs}
    if unknown:
        raise ValueError(f"target {config.name!r} disables unknown packs: {sorted(unknown)}")

    decisions = []
    for pack in packs:
        missing = pack.requires - config.enabled_capabilities
        unmet = pack.precondition(config) if pack.precondition else None
        if pack.name in config.packs.disable:
            decisions.append(PackDecision(pack, False, "disabled in target config"))
        elif missing:
            reason = "target lacks: " + ", ".join(sorted(missing))
            decisions.append(PackDecision(pack, False, reason))
        elif unmet:
            decisions.append(PackDecision(pack, False, unmet))
        else:
            decisions.append(PackDecision(pack, True))
    return decisions
