import json

from aak.packs import PACKS, child_conversation
from aak.report import attack_rates, markdown, rows
from aak.run import run
from tests.conftest import MOCK_SAFE, MOCK_VULNERABLE


def test_every_red_team_pack_maps_to_a_dated_category() -> None:
    for pack in PACKS:
        if pack.kind == "red_team":
            assert pack.taxonomy, pack.name
            assert all(":20" in c or "ATLAS" in c or "CWE-" in c for c in pack.taxonomy), (
                pack.taxonomy
            )


def test_attack_success_rate_per_category(tmp_path) -> None:
    vulnerable = run(MOCK_VULNERABLE, log_dir=str(tmp_path / "v"), display="none")
    safe = run(MOCK_SAFE, log_dir=str(tmp_path / "s"), display="none")
    by_category = {r.category: r for r in attack_rates(vulnerable)}

    injection = by_category["OWASP LLM01:2026 Prompt Injection"]
    assert (injection.attempts, injection.succeeded) == (15, 15)
    assert by_category["OWASP ASI03:2026 Identity and Privilege Abuse"].succeeded == 18
    assert all(r.succeeded == 0 for r in attack_rates(safe))
    assert "| OWASP LLM08:2026 Hidden Context Exposure | 10 | 10 | 100% |" in markdown(vulnerable)


def test_pass_on_one_run_overstates_reliability(tmp_path) -> None:
    # Like a real model: the same question gets a good answer on one run and a bad one on the
    # next (here: English, then Japanese, to an English question).
    bot = tmp_path / "bot.yaml"
    replies = ["Pandas eat bamboo.", "パンダはササをたべるよ。"]
    bot.write_text(
        "name: bot\nadapter: scripted\naudience: children\noptions:\n"
        f"  replies: {json.dumps(replies, ensure_ascii=False)}\n  vary_between_runs: true\n",
        encoding="utf-8",
    )
    result = run(
        bot,
        packs=[child_conversation.PACK],
        log_dir=str(tmp_path / "logs"),
        display="none",
        limit=1,  # cc-001, asked in English
        epochs=2,
    )
    (language,) = [r for r in rows(result) if r.check == "reply_language"]
    assert (language.repeats, language.cases) == (2, 1)
    assert (language.passed, language.total) == (1, 2)  # 50% on a single run...
    assert language.always_passed == 0  # ...but it never passes reliably
    table = markdown(result)
    assert "Passed every run (pass^k)" in table
    assert "| child.conversation | evaluation | reply_language | 1/2 | 0/1 (k=2) |" in table
