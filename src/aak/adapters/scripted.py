"""A target that answers from a fixed list. Test double for anything that needs canned replies."""

from aak.core.target import Reply, TargetConfig


class ScriptedSession:
    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self._turn = 0

    async def send(self, text: str) -> Reply:
        reply = self._replies[self._turn % len(self._replies)]
        self._turn += 1
        return Reply(text=reply)

    async def close(self) -> None:
        pass


class ScriptedTarget:
    def __init__(self, name: str, replies: list[str]) -> None:
        if not replies:
            raise ValueError("scripted target needs at least one reply")
        self.name = name
        self._replies = replies

    @classmethod
    def from_config(cls, config: TargetConfig) -> ScriptedTarget:
        return cls(name=config.name, **config.options)

    async def open_session(self) -> ScriptedSession:
        return ScriptedSession(self._replies)
