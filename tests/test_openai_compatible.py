import asyncio
import json

import httpx
import pytest

from aak.adapters.openai_compatible import OpenAICompatibleTarget
from aak.core.target import load_target_config
from tests.conftest import ROOT


class FakeEndpoint:
    """Records requests and answers with canned assistant messages, like a chat API would."""

    def __init__(self, *messages: dict) -> None:
        self.requests: list[dict] = []
        self.headers: list[httpx.Headers] = []
        self._messages = list(messages)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        self.requests.append(json.loads(request.content))
        self.headers.append(request.headers)
        return httpx.Response(200, json={"choices": [{"message": self._messages.pop(0)}]})


def target(endpoint: FakeEndpoint, **kwargs) -> OpenAICompatibleTarget:
    return OpenAICompatibleTarget(
        name="t",
        base_url="http://fake/v1",
        model="m",
        transport=httpx.MockTransport(endpoint),
        **kwargs,
    )


def chat(t: OpenAICompatibleTarget, *turns: str):
    async def go():
        session = await t.open_session()
        try:
            return [await session.send(turn) for turn in turns]
        finally:
            await session.close()

    return asyncio.run(go())


def test_resends_system_prompt_and_history_every_turn() -> None:
    endpoint = FakeEndpoint({"content": "Hello!"}, {"content": "Pandas eat bamboo."})
    replies = chat(target(endpoint, system_prompt="Be kind."), "hi", "what do pandas eat?")
    assert [r.text for r in replies] == ["Hello!", "Pandas eat bamboo."]
    assert endpoint.requests[1]["messages"] == [
        {"role": "system", "content": "Be kind."},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "what do pandas eat?"},
    ]


def test_keeps_temperature_zero() -> None:
    endpoint = FakeEndpoint({"content": "ok"})
    chat(target(endpoint, temperature=0), "hi")
    assert endpoint.requests[0]["temperature"] == 0


def test_strips_inline_reasoning() -> None:
    endpoint = FakeEndpoint({"content": "<think>the child wants a fact</think>\nThe sky is blue."})
    (reply,) = chat(target(endpoint), "why is the sky blue?")
    assert reply.text == "The sky is blue."


def test_parses_tool_calls_with_string_or_object_arguments() -> None:
    endpoint = FakeEndpoint(
        {
            "content": "",
            "tool_calls": [
                {"function": {"name": "cancel_booking", "arguments": '{"booking_id": "B-1"}'}},
                {"function": {"name": "get_booking", "arguments": {"booking_id": "B-2"}}},
            ],
        }
    )
    (reply,) = chat(target(endpoint), "cancel")
    assert [(c.name, c.args) for c in reply.tool_calls] == [
        ("cancel_booking", {"booking_id": "B-1"}),
        ("get_booking", {"booking_id": "B-2"}),
    ]


def test_sends_api_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AAK_TEST_KEY", "sk-test")
    endpoint = FakeEndpoint({"content": "ok"})
    chat(target(endpoint, api_key_env="AAK_TEST_KEY"), "hi")
    assert endpoint.headers[0]["authorization"] == "Bearer sk-test"


def test_missing_api_key_fails_early(monkeypatch) -> None:
    monkeypatch.delenv("AAK_TEST_KEY", raising=False)
    with pytest.raises(ValueError, match="AAK_TEST_KEY"):
        target(FakeEndpoint(), api_key_env="AAK_TEST_KEY")


def test_http_errors_are_not_swallowed() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    t = OpenAICompatibleTarget(
        name="t", base_url="http://fake/v1", model="m", transport=httpx.MockTransport(broken)
    )
    with pytest.raises(httpx.HTTPStatusError):
        chat(t, "hi")


def test_stand_in_config_loads_its_system_prompt_file() -> None:
    config = load_target_config(ROOT / "examples" / "local-kids-chat" / "target.yaml")
    t = OpenAICompatibleTarget.from_config(config)
    assert "Rules for every reply" in t._system_prompt


def test_extra_body_is_sent_as_is() -> None:
    endpoint = FakeEndpoint({"content": "ok"})
    chat(target(endpoint, extra_body={"reasoning_effort": "none"}), "hi")
    assert endpoint.requests[0]["reasoning_effort"] == "none"
