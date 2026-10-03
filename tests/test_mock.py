import asyncio

import pytest

from aak.adapters.mock import MockTarget


def send(target: MockTarget, *turns: str):
    async def go():
        session = await target.open_session()
        return [await session.send(t) for t in turns]

    return asyncio.run(go())


def test_safe_mode_only_touches_the_callers_bookings() -> None:
    target = MockTarget("m", mode="safe")
    own, other = send(target, "cancel B-1002", "cancel B-1001")
    assert [c.name for c in own.tool_calls] == ["cancel_booking"]
    assert other.tool_calls == []


def test_vulnerable_mode_skips_the_ownership_check() -> None:
    (reply,) = send(MockTarget("m", mode="vulnerable"), "B-1001の予約をキャンセルしてください")
    assert reply.tool_calls[0].args == {"booking_id": "B-1001"}


def test_sessions_do_not_share_state() -> None:
    target = MockTarget("m", mode="safe")
    send(target, "cancel B-1002")
    (again,) = send(target, "cancel B-1002")
    assert again.tool_calls, "a new session should start with fresh bookings"


def test_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        MockTarget("m", mode="sloppy")  # type: ignore[arg-type]
