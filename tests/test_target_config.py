import pytest
from pydantic import ValidationError

from aak.core.target import Capability, TargetConfig, load_target_config
from tests.conftest import MOCK_SAFE, PIKAPI


def test_loads_declared_capabilities() -> None:
    config = load_target_config(MOCK_SAFE)
    assert Capability.ACTIONS in config.enabled_capabilities
    assert Capability.VOICE not in config.enabled_capabilities


def test_engagement_config_is_valid() -> None:
    config = load_target_config(PIKAPI)
    assert config.enabled_capabilities == {Capability.VOICE, Capability.WEB_SEARCH}


def test_undeclared_capability_counts_as_false() -> None:
    config = TargetConfig(name="t", adapter="mock", capabilities={"actions": True})
    assert config.enabled_capabilities == {Capability.ACTIONS}


def test_rejects_unknown_capability() -> None:
    with pytest.raises(ValidationError):
        TargetConfig(name="t", adapter="mock", capabilities={"teleport": True})


def test_local_overlay_adds_private_values(tmp_path) -> None:
    (tmp_path / "target.yaml").write_text(
        "name: t\nadapter: mock\noptions: {mode: safe}\ncapabilities: {actions: true}\n"
    )
    (tmp_path / "target.local.yaml").write_text(
        "options: {caller: tanaka}\ncanaries: [secret phrase]\n"
    )
    config = load_target_config(tmp_path / "target.yaml")
    assert config.canaries == ["secret phrase"]
    assert config.options == {"mode": "safe", "caller": "tanaka"}
    assert config.enabled_capabilities == {Capability.ACTIONS}


def test_rejects_unknown_keys() -> None:
    with pytest.raises(ValidationError):
        TargetConfig.model_validate({"name": "t", "adapter": "mock", "capabilites": {}})
