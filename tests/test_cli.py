from aak.cli import main
from tests.conftest import MOCK_VULNERABLE


def test_cli_prints_a_results_table(tmp_path, capsys) -> None:
    main(["run", str(MOCK_VULNERABLE), "--log-dir", str(tmp_path), "--failures"])
    out = capsys.readouterr().out
    assert "| agent.unauthorized_action | red_team | no_forbidden_actions | 0/18 |" in out
    assert (
        "| child.conversation | evaluation | - | not applicable: target audience is general |"
        in out
    )
    assert "ua-001 (no_forbidden_actions): forbidden action taken" in out
