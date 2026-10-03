"""LLM judge: a second model grades replies against a written rubric.

The judge is configured like any target (a target.yaml, usually openai-compatible), so a
stronger judge is a config change. Judging runs as a pass over finished logs: old transcripts
can be re-judged with a better rubric without calling the target again.
"""

import json
import re
from importlib.resources import files

from inspect_ai.scorer import CORRECT, INCORRECT, NOANSWER, Score, Scorer, accuracy, scorer, stderr
from inspect_ai.scorer import Target as Expected
from inspect_ai.solver import TaskState

from aak.adapters import build_target
from aak.core.target import load_target_config
from aak.inspect_bridge import Transcript

JUDGE_SCORER = "llm_judge"  # the name scores are stored under in logs

_OUTPUT_FORMAT = """
Answer with JSON only, no other text:
{"verdict": "pass" or "fail", "reason": "<one short sentence; quote the problem if it fails>"}
"""

_JSON = re.compile(r"\{.*\}", re.DOTALL)
_WORD = re.compile(r"\b(pass|fail)\b", re.IGNORECASE)


def load_rubric(name: str) -> str:
    return (files("aak.rubrics") / f"{name}.md").read_text(encoding="utf-8")


def conversation_text(state: TaskState) -> str:
    # Spell out which reply is judged: given one undivided transcript, a small judge graded
    # the last reply against the first question.
    *earlier, last = state.store_as(Transcript).turns
    context = "\n".join(f"User: {t.user}\nAssistant: {t.reply.text}" for t in earlier)
    return (
        f"Earlier conversation (context only):\n{context or '(none)'}\n\n"
        f"The user's last message:\n{last.user}\n\n"
        f"The reply to judge:\n{last.reply.text}"
    )


def parse_verdict(raw: str) -> tuple[str, str] | None:
    """("pass" | "fail", reason), or None if the judge gave no usable verdict."""
    match = _JSON.search(raw)
    if match:
        try:
            data = json.loads(match.group(0))
            verdict = str(data.get("verdict", "")).strip().lower()
            if verdict in ("pass", "fail"):
                return verdict, str(data.get("reason", "")).strip()
        except json.JSONDecodeError:
            pass
    # Small judges sometimes break the JSON; a lone pass/fail word is still a verdict.
    words = {w.lower() for w in _WORD.findall(raw)}
    if len(words) == 1:
        return words.pop(), raw.strip()[:200]
    return None


@scorer(metrics=[accuracy(), stderr()])
def llm_judge(rubric: str, judge_file: str) -> Scorer:
    judge = build_target(load_target_config(judge_file))
    instructions = load_rubric(rubric) + _OUTPUT_FORMAT

    async def score(state: TaskState, target: Expected) -> Score:
        prompt = conversation_text(state)
        raw = ""
        for _ in range(2):  # one retry: small judges occasionally ignore the format
            session = await judge.open_session()
            try:
                raw = (await session.send(f"{instructions}\n\n{prompt}")).text
            finally:
                await session.close()
            parsed = parse_verdict(raw)
            if parsed:
                verdict, reason = parsed
                value = CORRECT if verdict == "pass" else INCORRECT
                return Score(value=value, explanation=reason, metadata={"judge_raw": raw})
        return Score(value=NOANSWER, explanation="judge gave no verdict", metadata={"raw": raw})

    return score
