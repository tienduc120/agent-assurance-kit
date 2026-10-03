import csv
import json

import pytest

from aak.cli import main
from aak.labels import cohen_kappa, compare_labels, export_labels
from aak.packs import child_safety
from aak.run import run

JUDGE_REASON = "dismissed the child"


def test_cohen_kappa_worked_example() -> None:
    # Observed 3/4; expected (3/4·2/4 + 1/4·2/4) = 1/2; kappa = (0.75 - 0.5) / 0.5.
    pairs = [("pass", "pass"), ("pass", "pass"), ("fail", "fail"), ("pass", "fail")]
    assert cohen_kappa(pairs) == pytest.approx(0.5)


def test_cohen_kappa_edges() -> None:
    assert cohen_kappa([("pass", "pass"), ("fail", "fail")]) == pytest.approx(1.0)
    assert cohen_kappa([("pass", "fail"), ("fail", "pass")]) == pytest.approx(-1.0)
    assert cohen_kappa([("pass", "pass")] * 3) == 1.0  # one label only: undefined, agree


def write_target(path, replies, audience="children"):
    path.write_text(
        f"name: {path.stem}\nadapter: scripted\naudience: {audience}\n"
        f"options:\n  replies: {json.dumps(replies)}\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def judged_log(tmp_path):
    bot = write_target(tmp_path / "bot.yaml", ["Please tell a grown-up you trust right away."])
    judge = write_target(
        tmp_path / "judge.yaml", [json.dumps({"verdict": "fail", "reason": JUDGE_REASON})]
    )
    result = run(
        bot,
        packs=[child_safety.PACK],
        judge_file=judge,
        log_dir=str(tmp_path / "logs"),
        display="none",
        limit=6,
    )
    (log,) = result.logs
    return log


def test_export_hides_the_judges_verdict(tmp_path, judged_log) -> None:
    out = tmp_path / "labels.csv"
    assert export_labels([judged_log], out, n=4) == 4
    text = out.read_text(encoding="utf-8-sig")
    assert JUDGE_REASON not in text
    rows = list(csv.DictReader(text.splitlines()))
    assert all(r["your_label"] == "" for r in rows)
    assert all("User:" in r["conversation"] and r["reply"] for r in rows)


def test_compare_measures_judge_and_rules_against_you(tmp_path, judged_log, capsys) -> None:
    out = tmp_path / "labels.csv"
    export_labels([judged_log], out, n=4)
    with out.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    # Label each reply the way the rules scored it (the English-only bot fails the language
    # rule on Japanese and Vietnamese cases), so the expected numbers follow from the log.
    samples = {str(s.id): s for s in judged_log.samples}
    for row in rows:
        scores = samples[row["case_id"]].scores
        rule_failed = any(k != "llm_judge" and v.value != "C" for k, v in scores.items())
        row["your_label"] = "fail" if rule_failed else "pass"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    fails = sum(r["your_label"] == "fail" for r in rows)

    (judge, rules), no_verdict = compare_labels(out)
    assert no_verdict == 0
    assert (rules.agree, rules.kappa) == (4, 1.0)
    # The judge failed everything: it catches every real problem and false-alarms the rest.
    assert (judge.agree, judge.caught, judge.false_alarms) == (fails, fails, 4 - fails)

    main(["labels", "compare", str(out)])
    assert f"| judge | 4 | {fails}/4 |" in capsys.readouterr().out
