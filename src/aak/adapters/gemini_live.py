"""Talks to an app built on the Gemini Live API, the way its own browser client does.

Flow: authenticate, open the Live WebSocket, send the app's `setup` message, then send text
turns and read the reply's transcript until `turnComplete`. Tool calls are answered silently
so the model doesn't stall.

Nothing here is tied to one app, key or model:
- Auth is either the app's token service (`token_url_env`, as its browser does) or a Gemini
  API key of your choice (`api_key_env`), whichever the target.yaml names.
- The setup body (system prompt, voice, tools) comes from `setup_file`; `model` overrides the
  model in it. For a private app, keep these in *.local.yaml files, which are gitignored.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml
from websockets.asyncio.client import ClientConnection, connect

from aak.core.target import Reply, TargetConfig, ToolCall

_LIVE = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta"
# Ephemeral tokens only work on the constrained endpoint; API keys on the plain one.
LIVE_URL_TOKEN = f"{_LIVE}.GenerativeService.BidiGenerateContentConstrained"
LIVE_URL_API_KEY = f"{_LIVE}.GenerativeService.BidiGenerateContent"


def _env(name: str | None) -> str | None:
    if name is None:
        return None
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"environment variable {name} is not set")
    return value


class GeminiLiveSession:
    def __init__(
        self,
        ws: ClientConnection,
        text_mode: Literal["client_content", "realtime"],
        turn_timeout_s: float,
    ) -> None:
        self._ws = ws
        self._text_mode = text_mode
        self._timeout = turn_timeout_s

    async def _send(self, message: dict[str, Any]) -> None:
        await self._ws.send(json.dumps(message))

    async def _recv(self) -> dict[str, Any]:
        raw = await asyncio.wait_for(self._ws.recv(), timeout=self._timeout)
        return json.loads(raw)

    async def start(self, setup: dict[str, Any]) -> None:
        await self._send({"setup": setup})
        while "setupComplete" not in await self._recv():
            pass

    async def send(self, text: str) -> Reply:
        if self._text_mode == "client_content":
            turn = {"turns": [{"role": "user", "parts": [{"text": text}]}], "turnComplete": True}
            await self._send({"clientContent": turn})
        else:
            # Apps with manual activity detection only count input between these markers.
            await self._send({"realtimeInput": {"activityStart": {}}})
            await self._send({"realtimeInput": {"text": text}})
            await self._send({"realtimeInput": {"activityEnd": {}}})

        transcript: list[str] = []
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        while True:
            message = await self._recv()
            for call in message.get("toolCall", {}).get("functionCalls", []):
                calls.append(ToolCall(name=call.get("name", "?"), args=call.get("args") or {}))
                # SILENT: the model must not react to, or talk about, the tool result.
                response = {"result": "ok", "scheduling": "SILENT"}
                fn_response = {"id": call.get("id"), "name": call.get("name"), "response": response}
                await self._send({"toolResponse": {"functionResponses": [fn_response]}})

            content = message.get("serverContent", {})
            out = content.get("outputTranscription", {})
            # Chunks marked finished repeat text already streamed.
            if out.get("text") and not out.get("finished"):
                transcript.append(out["text"])
            for part in content.get("modelTurn", {}).get("parts", []):
                if part.get("text"):
                    text_parts.append(part["text"])
            if content.get("turnComplete"):
                break

        # Audio replies come with a transcript; text-only setups put the reply in parts.
        reply = "".join(transcript) if transcript else "".join(text_parts)
        return Reply(text=reply.strip(), tool_calls=calls)

    async def close(self) -> None:
        await self._ws.close()


class GeminiLiveTarget:
    def __init__(
        self,
        name: str,
        setup_file: str,
        token_url_env: str | None = None,
        api_key_env: str | None = None,
        access_key_env: str | None = None,
        model: str | None = None,
        live_url: str | None = None,
        text_mode: Literal["client_content", "realtime"] = "client_content",
        turn_timeout_s: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if (token_url_env is None) == (api_key_env is None):
            raise ValueError("set exactly one of token_url_env or api_key_env")
        self.name = name
        self._token_url = _env(token_url_env)
        self._api_key = _env(api_key_env)
        self._access_key = _env(access_key_env)
        self._setup = yaml.safe_load(Path(setup_file).read_text(encoding="utf-8"))
        if model:
            self._setup["model"] = model if model.startswith("models/") else f"models/{model}"
        self._live_url = live_url or (LIVE_URL_API_KEY if api_key_env else LIVE_URL_TOKEN)
        self._text_mode = text_mode
        self._timeout = turn_timeout_s
        self._transport = transport

    @classmethod
    def from_config(cls, config: TargetConfig) -> GeminiLiveTarget:
        return cls(name=config.name, **config.options)

    async def _fetch_token(self) -> str:
        params = {"key": self._access_key} if self._access_key else None
        async with httpx.AsyncClient(transport=self._transport, timeout=30) as client:
            response = await client.post(self._token_url, params=params)
        if response.status_code == 429:
            raise RuntimeError("token service rate-limited this client (HTTP 429)")
        response.raise_for_status()
        return response.json()["token"]

    async def open_session(self) -> GeminiLiveSession:
        return await self.open_session_with_setup({})

    async def open_session_with_setup(self, patch: dict[str, Any]) -> GeminiLiveSession:
        """Like open_session, with top-level setup fields replaced: what an attacker holding
        the app's token could send. A locked token makes the server ignore the changes."""
        if self._api_key:
            auth = f"key={self._api_key}"
        else:
            auth = f"access_token={await self._fetch_token()}"
        ws = await connect(f"{self._live_url}?{auth}", max_size=None)
        session = GeminiLiveSession(ws, self._text_mode, self._timeout)
        await session.start(self._setup | patch)
        return session
