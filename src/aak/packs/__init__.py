from aak.core.packs import Pack
from aak.packs import (
    approval_bypass,
    child_conversation,
    child_safety,
    prompt_injection,
    session_lock,
    smoke,
    system_prompt_leak,
    unauthorized_action,
)

PACKS: list[Pack] = [
    smoke.PACK,
    child_conversation.PACK,
    child_safety.PACK,
    prompt_injection.PACK,
    system_prompt_leak.PACK,
    unauthorized_action.PACK,
    approval_bypass.PACK,
    session_lock.PACK,
]
