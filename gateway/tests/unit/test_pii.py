import pytest

from gateway.security.pii import mask_name, redact


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("mail me at maria.schneider@example.com", "mail me at [EMAIL]"),
        ("IBAN DE89 3704 0044 0532 0130 00 please", "IBAN [IBAN] please"),
        ("card 4111 1111 1111 1111 was stolen", "card [CARD] was stolen"),
        ("call +49 30 1234567 tomorrow", "call [PHONE] tomorrow"),
    ],
)
def test_redacts_personal_data(text: str, expected: str) -> None:
    assert redact(text) == expected


def test_keeps_text_without_personal_data() -> None:
    text = "The kitchen pipe burst on Monday and flooded 2 rooms."
    assert redact(text) == text


def test_does_not_treat_invalid_card_number_as_card() -> None:
    assert "[CARD]" not in redact("order 1234 5678 9012 3456")


def test_masks_every_name_part() -> None:
    assert mask_name("Maria Schneider") == "M**** S********"
