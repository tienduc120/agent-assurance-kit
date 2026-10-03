from importlib.resources import files
from pathlib import Path

import pytest

from aak.core.cases import load_cases
from aak.scorers import normalize

DATA = Path(str(files("aak.packs") / "data"))
CASE_FILES = sorted(DATA.glob("*.jsonl"))


@pytest.mark.parametrize("path", CASE_FILES, ids=lambda p: p.stem)
def test_packaged_cases_load(path: Path) -> None:
    assert load_cases(path)


def test_cases_cover_three_languages() -> None:
    langs = {c.lang for path in CASE_FILES for c in load_cases(path)}
    assert langs == {"en", "ja", "vi"}


@pytest.mark.parametrize("path", CASE_FILES, ids=lambda p: p.stem)
def test_forbidden_text_never_appears_in_the_attack(path: Path) -> None:
    # Otherwise a target that quotes the attack while refusing would be scored as failing.
    for case in load_cases(path):
        turns = normalize(" ".join(case.turns))
        for text in case.forbidden_text:
            assert normalize(text) not in turns, f"{case.id}: {text!r} is in its own turns"


def test_normalize_folds_full_width_and_case() -> None:
    assert normalize("ＺＥＢＲＡ－４１") == normalize("zebra-41")


def test_bad_line_names_its_line_number(tmp_path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text('{"id": "a", "lang": "en", "turns": ["hi"]}\n{"id": "b", "lang": "xx"}\n')
    with pytest.raises(ValueError, match="cases.jsonl:2"):
        load_cases(path)


def test_duplicate_ids_are_rejected(tmp_path) -> None:
    path = tmp_path / "cases.jsonl"
    line = '{"id": "a", "lang": "en", "turns": ["hi"]}\n'
    path.write_text(line * 2)
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)
