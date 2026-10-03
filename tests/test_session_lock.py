"""platform.session_lock against a fake Live server that is either locked or not."""

import asyncio
import json
import threading
from contextlib import contextmanager

import pytest
from websockets.asyncio.server import ServerConnection, serve

from aak.inspect_bridge import drive_target_with_setup
from aak.packs import session_lock
from aak.report import attack_rates
from aak.run import run
from tests.conftest import MOCK_SAFE

APP_INSTRUCTION = "You are a kind helper for children."


class FakeLiveApp:
    """Obeys whatever system instruction it ends up with. Locked: the app's own, always."""

    def __init__(self, locked: bool) -> None:
        self.locked = locked

    async def handler(self, ws: ServerConnection) -> None:
        instruction = APP_INSTRUCTION
        async for raw in ws:
            msg = json.loads(raw)
            if "setup" in msg:
                parts = msg["setup"].get("systemInstruction", {}).get("parts", [{}])
                if not self.locked:
                    instruction = parts[0].get("text", "")
                await ws.send(json.dumps({"setupComplete": {}}))
            elif "clientContent" in msg:
                reply = {"outputTranscription": {"text": self._obey(instruction)}}
                await ws.send(json.dumps({"serverContent": reply}))
                await ws.send(json.dumps({"serverContent": {"turnComplete": True}}))

    @staticmethod
    def _obey(instruction: str) -> str:
        if "ripe banana" in instruction or "バナナ" in instruction:
            return "YELLOW-42"
        if "letters L, O, C and K" in instruction:
            return "LOCK-0FF. I can do anything!"
        return "Hello! What would you like to talk about?"


@contextmanager
def background_server(handler):
    # run() drives targets from Inspect's own event loop, so the fake lives on another one.
    loop = asyncio.new_event_loop()

    async def start():
        return await serve(handler, "127.0.0.1", 0)  # must be created inside a running loop

    server = loop.run_until_complete(start())
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        yield server.sockets[0].getsockname()[1]
    finally:
        loop.call_soon_threadsafe(server.close)
        asyncio.run_coroutine_threadsafe(server.wait_closed(), loop).result(timeout=5)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()


def app_target(tmp_path, monkeypatch, port: int):
    monkeypatch.setenv("AAK_GEMINI_KEY", "fake-key")
    setup = {
        "model": "models/fake-live",
        "systemInstruction": {"parts": [{"text": APP_INSTRUCTION}]},
    }
    (tmp_path / "setup.local.yaml").write_text(json.dumps(setup), encoding="utf-8")
    target = tmp_path / "target.yaml"
    target.write_text(
        "name: fake-live-app\nadapter: gemini-live\noptions:\n"
        "  api_key_env: AAK_GEMINI_KEY\n  setup_file: setup.local.yaml\n"
        f"  live_url: ws://127.0.0.1:{port}\ncapabilities:\n  client_setup: true\n",
        encoding="utf-8",
    )
    return target


@pytest.mark.parametrize(("locked", "succeeded"), [(False, 3), (True, 0)])
def test_session_lock_tells_locked_from_unlocked(tmp_path, monkeypatch, locked, succeeded):
    with background_server(FakeLiveApp(locked).handler) as port:
        result = run(
            app_target(tmp_path, monkeypatch, port),
            packs=[session_lock.PACK],
            log_dir=str(tmp_path / "logs"),
            display="none",
        )
    by_category = {r.category: r for r in attack_rates(result)}
    rate = by_category["CWE-284 Improper Access Control"]
    assert (rate.attempts, rate.succeeded) == (3, succeeded)


def test_adapters_that_cannot_change_setup_are_refused() -> None:
    with pytest.raises(ValueError, match="can't change a session's setup"):
        drive_target_with_setup(str(MOCK_SAFE))
