from aak.core.packs import Pack
from aak.packs import prompt_injection, smoke, system_prompt_leak, unauthorized_action

PACKS: list[Pack] = [
    smoke.PACK,
    prompt_injection.PACK,
    system_prompt_leak.PACK,
    unauthorized_action.PACK,
]
