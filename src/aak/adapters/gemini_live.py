"""Talks to an app built on the Gemini Live API, the way its own browser client does.

Flow: get a short-lived token from the app's backend, open the Live WebSocket, send the
app's `setup` message, then send text turns and read the reply's transcript until
`turnComplete`. Tool calls are answered silently so the model doesn't stall.

The setup body is app-specific (system prompt, voice, tools), so it comes from a file. For a
private app, keep that file next to target.yaml as *.local.yaml, which is gitignored.
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

LIVE_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained"
)


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
        token_url_env: str,
        setup_file: str,
        access_key_env: str | None = None,
        live_url: str = LIVE_URL,
        text_mode: Literal["client_content", "realtime"] = "client_content",
        turn_timeout_s: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.name = name
        self._token_url = _env(token_url_env)
        self._access_key = _env(access_key_env)
        self._setup = yaml.safe_load(Path(setup_file).read_text(encoding="utf-8"))
        self._live_url = live_url
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
        token = await self._fetch_token()
        ws = await connect(f"{self._live_url}?access_token={token}", max_size=None)
        session = GeminiLiveSession(ws, self._text_mode, self._timeout)
        await session.start(self._setup)
        return session
