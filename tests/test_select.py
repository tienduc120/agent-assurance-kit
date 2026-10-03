import pytest

from aak.core.packs import select_packs
from aak.core.target import TargetConfig, load_target_config
from aak.packs import PACKS
from tests.conftest import MOCK_SAFE, PIKAPI


def by_name(decisions):
    return {d.pack.name: d for d in decisions}


def test_pikapi_gets_the_packs_that_fit_it() -> None:
    decisions = by_name(select_packs(load_target_config(PIKAPI), PACKS))
    assert decisions["smoke"].runs
    assert decisions["child.conversation"].runs
    assert decisions["child.safety"].runs
    assert decisions["llm.prompt_injection"].runs
    leak = decisions["llm.system_prompt_leak"]
    assert (leak.runs, leak.reason) == (False, "no canaries in target config")
    agent = decisions["agent.unauthorized_action"]
    assert (agent.runs, agent.reason) == (False, "target lacks: action_log, actions, user_data")


def test_every_general_pack_runs_on_the_mock() -> None:
    decisions = by_name(select_packs(load_target_config(MOCK_SAFE), PACKS))
    for name in ["child.conversation", "child.safety"]:
        child = decisions.pop(name)
        assert (child.runs, child.reason) == (False, "target audience is general")
    assert all(d.runs for d in decisions.values())


def test_disabled_pack_is_reported_not_dropped() -> None:
    data = load_target_config(MOCK_SAFE).model_dump()
    data["packs"] = {"disable": ["agent.unauthorized_action"]}
    config = TargetConfig.model_validate(data)
    agent = by_name(select_packs(config, PACKS))["agent.unauthorized_action"]
    assert not agent.runs
    assert agent.reason == "disabled in target config"


def test_unknown_disabled_pack_is_an_error() -> None:
    config = TargetConfig(name="t", adapter="mock", packs={"disable": ["agent.typo"]})
    with pytest.raises(ValueError, match="agent.typo"):
        select_packs(config, PACKS)
