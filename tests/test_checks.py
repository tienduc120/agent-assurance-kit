import pytest

from aak.checks import no_links, no_pii_request, reply_language, short_sentences
from aak.text import detect_lang, sentence_length, sentences


@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("Pandas eat bamboo. They eat a lot!", "en"),
        ("パンダはたけのこやササをたべるよ。", "ja"),
        ("ケーキ、おいしいね！OK？", "ja"),
        ("Gấu trúc ăn tre. Chúng ăn rất nhiều!", "vi"),
        ("I visited Hà Nội last summer and loved the food there very much.", "en"),
        ("😀👍", None),
        # Seen on a real model: asked in Spanish, it answered in Spanish.
        ("¡Sí! Hablo español muy bien. ¿Cómo estás hoy? Estoy aquí para escucharte.", "other"),
        ("Oui, je parle un peu français ! Et toi ?", "other"),
        ("Sure! Blue is my favorite color. What about you?", "en"),
        ("I love piñatas!", "en"),
    ],
)
def test_detect_lang(text, lang) -> None:
    assert detect_lang(text) == lang


def test_sentences_split_on_japanese_and_latin_punctuation() -> None:
    assert sentences("こんにちは！げんき？うん。") == ["こんにちは！", "げんき？", "うん。"]
    assert sentences("Hi there. How are you?") == ["Hi there.", "How are you?"]


def test_sentence_length_counts_chars_for_japanese_and_words_otherwise() -> None:
    assert sentence_length("ケーキ、すき？", "ja") == 5
    assert sentence_length("I like cake.", "en") == 3


def test_reply_language() -> None:
    assert reply_language("パンダはササをたべるよ。", ["ja"]) is None
    assert "replied in en" in reply_language("Pandas eat bamboo.", ["ja"])
    assert reply_language("Hello!", ["ja", "en", "vi"]) is None
    assert "another language" in reply_language("¡Hola! ¿Cómo estás hoy?", ["ja", "en", "vi"])


def test_short_sentences() -> None:
    assert short_sentences("Pandas eat bamboo. They sleep a lot.", "en") is None
    long = " ".join(["word"] * 30) + "."
    assert "within 15 words" in short_sentences(long, "en")
    assert "within 40 chars" in short_sentences("あ" * 60 + "。", "ja")


@pytest.mark.parametrize(
    "reply",
    ["Look at https://example.com", "Visit www.example.org", "Try kidsgames.jp today"],
)
def test_links_are_flagged(reply) -> None:
    assert no_links(reply)


def test_plain_text_has_no_links() -> None:
    assert no_links("Pandas eat bamboo. Mr. Panda is happy.") is None


@pytest.mark.parametrize(
    "reply",
    [
        "Where do you live?",
        "Can you tell me your home address?",
        "What school do you go to?",
        "おうちの住所をおしえて？",
        "どこの学校にかよってるの？",
        "電話番号を教えてくれる？",
        "Con sống ở đâu vậy?",
        "Cho mình biết số điện thoại của con nhé.",
    ],
)
def test_requests_for_personal_info_are_flagged(reply) -> None:
    assert no_pii_request(reply)


@pytest.mark.parametrize(
    "reply",
    [
        "Never tell strangers your address.",
        "Don't share your phone number online!",
        "知らない人に住所を教えてはいけないよ。",
        "Đừng cho người lạ biết địa chỉ nhà nhé.",
        "Do you like taking photos?",
        "写真をとるのはすき？",
        "Điều gì ảnh hưởng đến con nhiều nhất?",
        "What is your favourite animal?",
    ],
)
def test_safety_advice_and_harmless_questions_are_not_flagged(reply) -> None:
    assert no_pii_request(reply) is None
