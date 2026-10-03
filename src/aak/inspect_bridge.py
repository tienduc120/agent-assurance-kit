"""Runs a target inside Inspect AI.

Inspect's model API is stateless (the full history is resent every turn), but targets are
stateful sessions, so a solver drives the target instead of a model provider. Tasks run
with model="none", which raises if anything tries to call an LLM.
"""

import time

from inspect_ai.model import ChatMessageAssistant, ChatMessageUser, ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import StoreModel
from pydantic import BaseModel, Field

from aak.adapters import build_target
from aak.core.target import Reply, Session, ToolCall, load_target_config


class Turn(BaseModel):
    user: str
    reply: Reply
    latency_ms: float


class Transcript(StoreModel):
    """What the target said and did in one test case; scorers read this."""

    turns: list[Turn] = Field(default_factory=list)

    def tool_calls(self) -> list[ToolCall]:
        return [call for turn in self.turns for call in turn.reply.tool_calls]


async def _converse(state: TaskState, target_name: str, session: Session) -> TaskState:
    turns: list[str] = state.metadata.get("turns") or [state.input_text]
    transcript = state.store_as(Transcript)
    state.messages = []
    try:
        for text in turns:
            state.messages.append(ChatMessageUser(content=text))
            start = time.perf_counter()
            reply = await session.send(text)
            latency_ms = (time.perf_counter() - start) * 1000
            state.messages.append(ChatMessageAssistant(content=reply.text, model=target_name))
            # Reassign, not append: the store only sees attribute writes.
            transcript.turns = [
                *transcript.turns,
                Turn(user=text, reply=reply, latency_ms=latency_ms),
            ]
    finally:
        await session.close()
    state.output = ModelOutput.from_content(model=target_name, content=state.messages[-1].text)
    return state


@solver
def drive_target(target_file: str) -> Solver:
    target = build_target(load_target_config(target_file))

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        return await _converse(state, target.name, await target.open_session())

    return solve


@solver
def drive_target_with_setup(target_file: str) -> Solver:
    """Opens each session with the case's `setup_patch` applied, as a client holding the
    app's token could, then converses as usual."""
    target = build_target(load_target_config(target_file))
    if not hasattr(target, "open_session_with_setup"):
        raise ValueError(f"the adapter for {target.name!r} can't change a session's setup")

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        session = await target.open_session_with_setup(state.metadata["setup_patch"])
        return await _converse(state, target.name, session)

    return solve
