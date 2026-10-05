from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class _Rule:
    label: str
    pattern: re.Pattern[str]
    accept: Callable[[str], bool] = bool


def _luhn_valid(candidate: str) -> bool:
    digits = [int(c) for c in candidate if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


_RULES: tuple[_Rule, ...] = (
    _Rule("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    _Rule("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,4})?\b")),
    _Rule("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b"), _luhn_valid),
    _Rule("PHONE", re.compile(r"(?<!\w)\+?\d[\d ()/-]{7,}\d(?!\w)")),
)


def _apply(rule: _Rule, text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(0)
        return f"[{rule.label}]" if rule.accept(value) else value

    return rule.pattern.sub(replace, text)


def redact(text: str) -> str:
    for rule in _RULES:
        text = _apply(rule, text)
    return text


def mask_name(full_name: str) -> str:
    return " ".join(part[0] + "*" * (len(part) - 1) for part in full_name.split())
