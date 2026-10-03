"""The Gemini Live adapter against a local fake server: no Google account, no cost."""

import asyncio
import json

import httpx
import pytest
from websockets.asyncio.server import ServerConnection, serve

from aak.adapters.gemini_live import GeminiLiveTarget

SETUP = {"model": "models/fake-live", "generationConfig": {"responseModalities": ["AUDIO"]}}


class FakeLive:
    """Plays the Gemini Live server: setupComplete, a tool call, then a transcribed reply."""

    def __init__(self, text_reply: bool = False) -> None:
        self.received: list[dict] = []
        self.paths: list[str] = []
        self._text_reply = text_reply

    async def handler(self, ws: ServerConnection) -> None:
        self.paths.append(ws.request.path)
        async for raw in ws:
            msg = json.loads(raw)
            self.received.append(msg)
            if "setup" in msg:
                await ws.send(json.dumps({"setupComplete": {}}))
            elif "clientContent" in msg or "activityEnd" in msg.get("realtimeInput", {}):
                await self._reply(ws)

    async def _reply(self, ws: ServerConnection) -> None:
        call = {"id": "c1", "name": "set_mood", "args": {"mood": "happy"}}
        await ws.send(json.dumps({"toolCall": {"functionCalls": [call]}}))
        if self._text_reply:
            parts = [{"text": "Hi from "}, {"text": "text mode."}]
            await ws.send(json.dumps({"serverContent": {"modelTurn": {"parts": parts}}}))
        else:
            audio = {"modelTurn": {"parts": [{"inlineData": {"data": "AAAA"}}]}}
            await ws.send(json.dumps({"serverContent": audio}))
            for chunk in ["Hello ", "there!"]:
                await ws.send(
                    json.dumps({"serverContent": {"outputTranscription": {"text": chunk}}})
                )
            done = {"outputTranscription": {"text": "Hello there!", "finished": True}}
            await ws.send(json.dumps({"serverContent": done}))
        await ws.send(json.dumps({"serverContent": {"turnComplete": True}}))


TOKEN_AUTH = {"token_url_env": "AAK_TOKEN_URL", "access_key_env": "AAK_ACCESS_KEY"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("AAK_TOKEN_URL", "https://app.example/api/token")
    monkeypatch.setenv("AAK_ACCESS_KEY", "trusted-key")
    monkeypatch.setenv("AAK_GEMINI_KEY", "fake-api-key")
    setup_file = tmp_path / "setup.local.yaml"
    setup_file.write_text(json.dumps(SETUP), encoding="utf-8")
    return setup_file


def token_endpoint(requests: list[httpx.Request], status: int = 200) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json={"token": "tok-123", "trusted": True})

    return httpx.MockTransport(handle)


def converse(fake: FakeLive, setup_file, transport, *turns: str, auth=TOKEN_AUTH, **kwargs):
    async def go():
        async with serve(fake.handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            target = GeminiLiveTarget(
                name="t",
                **auth,
                setup_file=str(setup_file),
                live_url=f"ws://127.0.0.1:{port}",
                transport=transport,
                **kwargs,
            )
            session = await target.open_session()
            try:
                return [await session.send(t) for t in turns]
            finally:
                await session.close()

    return asyncio.run(go())


def test_full_turn_with_token_setup_tool_call_and_transcript(env) -> None:
    fake, requests = FakeLive(), []
    (reply,) = converse(fake, env, token_endpoint(requests), "Why is the sky blue?")

    assert reply.text == "Hello there!"  # the finished chunk is not appended twice
    assert [(c.name, c.args) for c in reply.tool_calls] == [("set_mood", {"mood": "happy"})]
    assert requests[0].url.params["key"] == "trusted-key"
    assert fake.paths[0].endswith("access_token=tok-123")
    assert fake.received[0] == {"setup": SETUP}
    assert fake.received[1]["clientContent"]["turns"][0]["parts"][0]["text"] == (
        "Why is the sky blue?"
    )
    (response,) = fake.received[2]["toolResponse"]["functionResponses"]
    assert response["id"] == "c1"
    assert response["response"]["scheduling"] == "SILENT"


def test_realtime_mode_wraps_text_in_activity_markers(env) -> None:
    fake = FakeLive()
    converse(fake, env, token_endpoint([]), "hi", text_mode="realtime")
    sent = [m["realtimeInput"] for m in fake.received if "realtimeInput" in m]
    assert sent == [{"activityStart": {}}, {"text": "hi"}, {"activityEnd": {}}]


def test_text_only_setups_read_the_reply_from_model_parts(env) -> None:
    (reply,) = converse(FakeLive(text_reply=True), env, token_endpoint([]), "hi")
    assert reply.text == "Hi from text mode."


def test_rate_limited_token_service_is_reported(env) -> None:
    with pytest.raises(RuntimeError, match="429"):
        converse(FakeLive(), env, token_endpoint([], status=429), "hi")


def test_missing_environment_variable_fails_early(env, monkeypatch) -> None:
    monkeypatch.delenv("AAK_TOKEN_URL")
    with pytest.raises(ValueError, match="AAK_TOKEN_URL"):
        GeminiLiveTarget(name="t", token_url_env="AAK_TOKEN_URL", setup_file=str(env))


def test_own_api_key_and_model_skip_the_apps_token_service(env) -> None:
    # Decoupled from the app's backend: any key, any model, chosen in target.yaml.
    fake, requests = FakeLive(), []
    converse(
        fake,
        env,
        token_endpoint(requests),
        "hi",
        auth={"api_key_env": "AAK_GEMINI_KEY"},
        model="other-live-model",
    )
    assert requests == []
    assert fake.paths[0].endswith("key=fake-api-key")
    assert fake.received[0]["setup"]["model"] == "models/other-live-model"


@pytest.mark.parametrize(
    "auth", [{}, {"token_url_env": "AAK_TOKEN_URL", "api_key_env": "AAK_GEMINI_KEY"}]
)
def test_exactly_one_way_to_authenticate(env, auth) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        GeminiLiveTarget(name="t", setup_file=str(env), **auth)
