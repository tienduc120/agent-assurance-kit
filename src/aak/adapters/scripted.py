"""A target that answers from a fixed list. Test double for anything that needs canned replies."""

from aak.core.target import Reply, TargetConfig


class ScriptedSession:
    def __init__(self, replies: list[str], start: int = 0) -> None:
        self._replies = replies
        self._turn = start

    async def send(self, text: str) -> Reply:
        reply = self._replies[self._turn % len(self._replies)]
        self._turn += 1
        return Reply(text=reply)

    async def close(self) -> None:
        pass


class ScriptedTarget:
    def __init__(self, name: str, replies: list[str], vary_between_runs: bool = False) -> None:
        if not replies:
            raise ValueError("scripted target needs at least one reply")
        self.name = name
        self._replies = replies
        # Each new session starts one reply later, imitating a model that answers the same
        # question differently from run to run.
        self._vary = vary_between_runs
        self._sessions = 0

    @classmethod
    def from_config(cls, config: TargetConfig) -> ScriptedTarget:
        return cls(name=config.name, **config.options)

    async def open_session(self) -> ScriptedSession:
        start = self._sessions if self._vary else 0
        self._sessions += 1
        return ScriptedSession(self._replies, start)
