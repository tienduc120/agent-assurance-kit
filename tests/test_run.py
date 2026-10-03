"""End to end through Inspect AI, against the free mock target."""

import pytest

from aak.core.target import load_target_config
from aak.packs import unauthorized_action
from aak.run import run
from tests.conftest import MOCK_SAFE, MOCK_VULNERABLE, PIKAPI

ATTACK_PACKS = ["llm.prompt_injection", "llm.system_prompt_leak", "agent.unauthorized_action"]


def log_for(result, task_name: str):
    (log,) = [log for log in result.logs if log.eval.task == task_name]
    assert log.status == "success", log.error
    return log


def accuracy(result, task_name: str) -> float:
    return log_for(result, task_name).results.scores[0].metrics["accuracy"].value


@pytest.fixture(scope="module")
def safe(tmp_path_factory):
    return run(MOCK_SAFE, log_dir=str(tmp_path_factory.mktemp("safe")), display="none")


@pytest.fixture(scope="module")
def vulnerable(tmp_path_factory):
    return run(MOCK_VULNERABLE, log_dir=str(tmp_path_factory.mktemp("vuln")), display="none")


@pytest.mark.parametrize("task_name", ["smoke", *ATTACK_PACKS])
def test_safe_mock_passes_every_case(safe, task_name) -> None:
    assert [d.pack.name for d in safe.not_applicable] == ["child.conversation"]
    assert accuracy(safe, task_name) == 1.0


@pytest.mark.parametrize("task_name", ATTACK_PACKS)
def test_vulnerable_mock_is_caught_on_every_case(vulnerable, task_name) -> None:
    assert accuracy(vulnerable, task_name) == 0.0


def test_leak_explanations_never_quote_the_canary(vulnerable) -> None:
    canaries = load_target_config(MOCK_VULNERABLE).canaries
    log = log_for(vulnerable, "llm.system_prompt_leak")
    for sample in log.samples:
        explanation = sample.scores["no_canary_leak"].explanation
        assert "leaked canary #" in explanation
        assert not any(c in explanation for c in canaries)


def test_pikapi_agent_pack_is_reported_not_applicable(tmp_path) -> None:
    result = run(PIKAPI, packs=[unauthorized_action.PACK], log_dir=str(tmp_path), display="none")
    assert result.logs == []
    (skipped,) = result.not_applicable
    assert skipped.reason == "target lacks: action_log, actions, user_data"
