import re

from promptsan import PromptSanitizer, SanConfig


def test_regex_strategy_non_overlapping_and_positions():
    config = SanConfig(
        strategies=["regex"],
        regex_patterns={
            r"john@example.com": "EMAIL",
            r"\b\d{2}/\d{2}/\d{4}\b": "DATE",
        },
    )
    sanitizer = PromptSanitizer(config)
    text = "Contact john@example.com on 01/02/2024."
    result = sanitizer.anonymize(text)
    assert "__EMAIL_" in result.text
    assert "__DATE_" in result.text
    assert result.mapping.get("john@example.com").startswith("__EMAIL_")


def test_dict_strategy_word_boundaries_and_case():
    config = SanConfig(
        strategies=["dict"],
        custom_dict={"secret": "CLASS"},
        dict_case_insensitive=True,
        dict_use_word_boundaries=True,
    )
    sanitizer = PromptSanitizer(config)
    text = "This is SECRET information. The secretsauce is different."
    result = sanitizer.anonymize(text)
    # Only SECRET as a whole word should be replaced
    assert "__CLASS_" in result.text
    assert "secretsauce" in result.text


def test_deanonymize_roundtrip():
    config = SanConfig(
        strategies=["regex", "dict"],
        custom_dict={"Acme Corp": "COMPANY"},
    )
    sanitizer = PromptSanitizer(config)
    original = "Email john@test.com at Acme Corp"
    res = sanitizer.anonymize(original)
    restored = sanitizer.deanonymize(res.text, res.mapping)
    assert restored == original


def test_streaming_deanonymize():
    sanitizer = PromptSanitizer()
    mapping = {"John": "__PERSON_1__"}
    chunks = ["Hello __PER", "SON_1__!" ]

    def gen():
        for c in chunks:
            yield c

    out = "".join(sanitizer.deanonymize_stream(gen(), mapping))
    assert out == "Hello John!"


