"""Talks to any OpenAI-compatible chat endpoint: Ollama, vLLM, LM Studio or a hosted model.

These endpoints are stateless, so the session keeps the history and resends it every turn.
An optional system prompt turns a bare model into a stand-in app.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

from aak.core.target import Reply, TargetConfig, ToolCall

# Some reasoning models inline their scratchpad; the user-facing reply is what follows it.
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _tool_call(raw: dict[str, Any]) -> ToolCall:
    fn = raw.get("function", {})
    args = fn.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"_raw": args}
    return ToolCall(name=fn.get("name", "?"), args=args)


class OpenAICompatibleSession:
    def __init__(
        self, client: httpx.AsyncClient, model: str, system_prompt: str | None, params: dict
    ) -> None:
        self._client = client
        self._model = model
        self._params = params
        self._messages: list[dict[str, str]] = []
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    async def send(self, text: str) -> Reply:
        self._messages.append({"role": "user", "content": text})
        body = {"model": self._model, "messages": self._messages, **self._params}
        response = await self._client.post("chat/completions", json=body)
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        content = _THINK.sub("", message.get("content") or "").strip()
        self._messages.append({"role": "assistant", "content": content})
        calls = [_tool_call(c) for c in message.get("tool_calls") or []]
        return Reply(text=content, tool_calls=calls)

    async def close(self) -> None:
        await self._client.aclose()


class OpenAICompatibleTarget:
    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        system_prompt: str | None = None,
        system_prompt_file: str | None = None,
        api_key_env: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
        timeout_s: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if system_prompt and system_prompt_file:
            raise ValueError("set system_prompt or system_prompt_file, not both")
        if system_prompt_file:
            system_prompt = Path(system_prompt_file).read_text(encoding="utf-8")
        headers = {}
        if api_key_env:
            key = os.environ.get(api_key_env)
            if not key:
                raise ValueError(f"environment variable {api_key_env} is not set")
            headers["Authorization"] = f"Bearer {key}"

        self.name = name
        self._base_url = base_url.rstrip("/") + "/"
        self._model = model
        self._system_prompt = system_prompt
        self._headers = headers
        self._timeout = timeout_s
        self._transport = transport
        params = {"temperature": temperature, "max_tokens": max_tokens}
        # extra_body carries server-specific flags, e.g. switching off a model's thinking.
        self._params = {k: v for k, v in params.items() if v is not None} | (extra_body or {})

    @classmethod
    def from_config(cls, config: TargetConfig) -> OpenAICompatibleTarget:
        return cls(name=config.name, **config.options)

    async def open_session(self) -> OpenAICompatibleSession:
        client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
            transport=self._transport,
        )
        return OpenAICompatibleSession(client, self._model, self._system_prompt, self._params)
