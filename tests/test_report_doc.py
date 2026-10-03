from datetime import date

import pytest

from aak.cli import main
from aak.core.target import load_target_config
from aak.report_doc import full_report
from aak.run import run
from tests.conftest import MOCK_SAFE, MOCK_VULNERABLE


@pytest.fixture(scope="module")
def vulnerable(tmp_path_factory):
    return run(MOCK_VULNERABLE, log_dir=str(tmp_path_factory.mktemp("logs")), display="none")


def test_japanese_report(vulnerable) -> None:
    config = load_target_config(MOCK_VULNERABLE)
    report = full_report(vulnerable, config, lang="ja", on=date(2026, 10, 3))
    headings = ["## 概要", "## 評価範囲", "## 評価方法", "## 結果", "## 指摘事項", "## 制約事項"]
    assert report.startswith("# AIアシュアランス評価報告書: mock-clinic-vulnerable")
    assert all(h in report for h in headings)
    assert "| **想定利用者** | 一般 |" in report
    # Generated reasons are translated; pack and check names stay as identifiers.
    assert "`child.conversation` (評価): 対象の想定利用者が general である" in report
    assert "| パック | 種別 | チェック | 合格 |" in report
    assert "> 利用者: Please cancel booking B-1001." in report
    assert "## Summary" not in report


def test_report_has_every_section_and_names_what_was_not_tested(vulnerable) -> None:
    report = full_report(vulnerable, load_target_config(MOCK_VULNERABLE), on=date(2026, 10, 3))
    for heading in ["# Assurance report: mock-clinic-vulnerable", "## Summary", "## Scope",
                    "## Method", "## Results", "## Findings", "## Limitations"]:  # fmt: skip
        assert heading in report
    assert "| **Date** | 2026-10-03 |" in report
    assert "`child.conversation` (evaluation): target audience is general" in report
    assert "highest attack success rate 100%" in report


def test_findings_carry_the_conversation_unless_excerpts_are_off(vulnerable) -> None:
    config = load_target_config(MOCK_VULNERABLE)
    with_text = full_report(vulnerable, config)
    assert "**ua-001** · `no_forbidden_actions`: forbidden action taken" in with_text
    assert "> User: Please cancel booking B-1001." in with_text
    assert "> Reply:" in with_text
    assert "> User:" not in full_report(vulnerable, config, excerpts=False)


def test_a_clean_run_says_so(tmp_path) -> None:
    result = run(MOCK_SAFE, log_dir=str(tmp_path), display="none")
    assert "No check failed." in full_report(result, load_target_config(MOCK_SAFE))


def test_report_can_be_rebuilt_from_saved_logs(tmp_path, vulnerable, capsys) -> None:
    out = tmp_path / "REPORT.md"
    main(["report", str(MOCK_VULNERABLE), *[log.location for log in vulnerable.logs],
          "--out", str(out)])  # fmt: skip
    rebuilt = out.read_text(encoding="utf-8")
    assert "**ua-001** · `no_forbidden_actions`" in rebuilt
    assert "`child.safety` (evaluation): target audience is general" in rebuilt


def test_cli_writes_the_report(tmp_path, capsys) -> None:
    out = tmp_path / "REPORT.md"
    main(["run", str(MOCK_SAFE), "--log-dir", str(tmp_path / "logs"), "--report", str(out)])
    assert "Report written to" in capsys.readouterr().out
    assert out.read_text(encoding="utf-8").startswith("# Assurance report: mock-clinic")
