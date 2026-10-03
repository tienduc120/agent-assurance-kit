"""Human labels: how far can the judge, and the rules, be trusted?

export: a random sample of judged replies to a CSV, without the judge's verdicts, so the
labeller isn't anchored by them. compare: agreement of judge and rules with the human labels.
"""

import csv
import random
from dataclasses import dataclass
from pathlib import Path

from inspect_ai.log import EvalLog, EvalSample, read_eval_log

from aak.judge import JUDGE_SCORER

JUDGE = JUDGE_SCORER
COLUMNS = ["log", "case_id", "epoch", "pack", "conversation", "reply", "your_label", "note"]


def _conversation(sample: EvalSample) -> tuple[str, str]:
    turns = sample.store.get("Transcript:turns") or []
    lines = []
    for turn in turns[:-1]:
        lines += [f"User: {turn['user']}", f"Assistant: {turn['reply']['text']}"]
    lines.append(f"User: {turns[-1]['user']}")
    return "\n".join(lines), turns[-1]["reply"]["text"]


def export_labels(logs: list[EvalLog], out: Path, n: int = 50, seed: int = 0) -> int:
    candidates = [
        (log, s) for log in logs for s in (log.samples or []) if s.scores and JUDGE in s.scores
    ]
    picked = random.Random(seed).sample(candidates, min(n, len(candidates)))
    out.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel shows Japanese and Vietnamese correctly, not mojibake.
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for log, sample in picked:
            conversation, reply = _conversation(sample)
            writer.writerow(
                {
                    "log": log.location,
                    "case_id": sample.id,
                    "epoch": sample.epoch,
                    "pack": log.eval.task,
                    "conversation": conversation,
                    "reply": reply,
                    "your_label": "",
                    "note": "",
                }
            )
    return len(picked)


@dataclass(frozen=True)
class Agreement:
    """One grader (judge or rules) against the human labels. 'fail' is the positive class."""

    grader: str
    n: int
    agree: int
    kappa: float
    caught: int  # human fails the grader also failed
    human_fails: int
    false_alarms: int  # grader fails the human passed
    disagreements: list[tuple[str, str, str, str]]  # (case, human, grader, reason)


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if n == 0:
        return float("nan")
    observed = sum(a == b for a, b in pairs) / n
    labels = {"pass", "fail"}
    expected = sum(
        (sum(a == lab for a, _ in pairs) / n) * (sum(b == lab for _, b in pairs) / n)
        for lab in labels
    )
    # Everyone gave the same single label: agreement is perfect but kappa is undefined.
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def _agreement(grader: str, rows: list[tuple[str, str, str, str]]) -> Agreement:
    pairs = [(human, verdict) for _, human, verdict, _ in rows]
    return Agreement(
        grader=grader,
        n=len(rows),
        agree=sum(h == v for h, v in pairs),
        kappa=cohen_kappa(pairs),
        caught=sum(h == v == "fail" for h, v in pairs),
        human_fails=sum(h == "fail" for h, _ in pairs),
        false_alarms=sum(h == "pass" and v == "fail" for h, v in pairs),
        disagreements=[r for r in rows if r[1] != r[2]],
    )


def compare_labels(path: Path) -> tuple[list[Agreement], int]:
    """Agreement of the judge and of the rules with the labels; also how many rows the judge
    left without a verdict (those are excluded, not guessed)."""
    logs: dict[str, EvalLog] = {}
    judge_rows, rule_rows, no_verdict = [], [], 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            human = row["your_label"].strip().lower()
            if human not in ("pass", "fail"):
                continue
            log = logs.setdefault(row["log"], read_eval_log(row["log"]))
            sample = next(
                s for s in log.samples or []
                if str(s.id) == row["case_id"] and str(s.epoch) == row["epoch"]
            )  # fmt: skip
            case = row["case_id"]
            judge = sample.scores[JUDGE]
            if judge.value in ("C", "I"):
                verdict = "pass" if judge.value == "C" else "fail"
                judge_rows.append((case, human, verdict, judge.explanation or ""))
            else:
                no_verdict += 1
            failed = [k for k, sc in sample.scores.items() if k != JUDGE and sc.value != "C"]
            rule_verdict = "fail" if failed else "pass"
            rule_rows.append((case, human, rule_verdict, ", ".join(failed)))
    return [_agreement("judge", judge_rows), _agreement("rules", rule_rows)], no_verdict


def markdown(agreements: list[Agreement], no_verdict: int, disagreements: bool = False) -> str:
    lines = [
        "| Grader | Labels | Agree | Cohen's kappa | Real problems caught | False alarms |",
        "|---|---|---|---|---|---|",
    ]
    for a in agreements:
        lines.append(
            f"| {a.grader} | {a.n} | {a.agree}/{a.n} | {a.kappa:.2f} "
            f"| {a.caught}/{a.human_fails} | {a.false_alarms} |"
        )
    if no_verdict:
        lines.append(f"\nJudge gave no verdict on {no_verdict} labelled replies (excluded).")
    if disagreements:
        for a in agreements:
            for case, human, verdict, reason in a.disagreements:
                lines.append(f"- {a.grader} {case}: you {human}, {a.grader} {verdict}: {reason}")
    return "\n".join(lines)
