import json

import pytest

from aak.cli import main
from aak.judge import load_rubric, parse_verdict
from aak.packs import child_safety
from aak.run import run


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"verdict": "pass", "reason": "kind and safe"}', ("pass", "kind and safe")),
        ('```json\n{"verdict": "FAIL", "reason": "dismissed it"}\n```', ("fail", "dismissed it")),
        ('Sure! {"verdict": "fail", "reason": "no adult"} Hope this helps.', ("fail", "no adult")),
        ("Verdict: FAIL. It ignores the child.", ("fail", "Verdict: FAIL. It ignores the child.")),
    ],
)
def test_parse_verdict(raw, expected) -> None:
    assert parse_verdict(raw) == expected


@pytest.mark.parametrize("raw", ["", "I think it could pass or fail.", '{"verdict": "maybe"}'])
def test_unusable_judge_output_gives_no_verdict(raw) -> None:
    assert parse_verdict(raw) is None


def test_rubrics_load() -> None:
    assert "PASS only if" in load_rubric("child_safety")
    assert "PASS only if" in load_rubric("child_answer")


def write_target(path, replies, audience="children"):
    path.write_text(
        f"name: {path.stem}\nadapter: scripted\naudience: {audience}\n"
        f"options:\n  replies: {json.dumps(replies)}\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def helpful_bot(tmp_path):
    return write_target(tmp_path / "bot.yaml", ["Please tell a grown-up you trust right away."])


def scores(result, name):
    (log,) = result.logs
    return [s.scores[name] for s in log.samples]


def test_judge_can_fail_what_the_rules_pass(tmp_path, helpful_bot) -> None:
    # The cs-007 situation: keyword rules are satisfied, the judge still says no.
    judge = write_target(
        tmp_path / "judge.yaml", ['{"verdict": "fail", "reason": "dismissed the child"}']
    )
    result = run(
        helpful_bot,
        packs=[child_safety.PACK],
        judge_file=judge,
        log_dir=str(tmp_path / "logs"),
        display="none",
    )
    assert all(s.value == "C" for s in scores(result, "points_to_help"))
    judged = scores(result, "llm_judge")
    assert all(s.value == "I" and s.explanation == "dismissed the child" for s in judged)


def test_judge_without_a_verdict_is_reported_not_guessed(tmp_path, helpful_bot) -> None:
    judge = write_target(tmp_path / "judge.yaml", ["I am not sure."])
    result = run(
        helpful_bot,
        packs=[child_safety.PACK],
        judge_file=judge,
        log_dir=str(tmp_path / "logs"),
        display="none",
        limit=2,
    )
    assert all(s.value == "N" for s in scores(result, "llm_judge"))


def test_cli_judges_an_existing_log(tmp_path, helpful_bot, capsys) -> None:
    result = run(
        helpful_bot,
        packs=[child_safety.PACK],
        log_dir=str(tmp_path / "logs"),
        display="none",
        limit=3,
    )
    (log,) = result.logs
    judge = write_target(tmp_path / "judge.yaml", ['{"verdict": "pass", "reason": "ok"}'])
    main(["judge", log.location, "--judge", str(judge)])
    assert "| child.safety | evaluation | llm_judge | 3/3 |" in capsys.readouterr().out
