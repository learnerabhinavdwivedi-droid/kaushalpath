"""Numeric hallucination validator for conversation responses.

Extracts all numbers from generated text and verifies that each numeric claim
corresponds directly to an allowable grounded fact.
"""
from __future__ import annotations

import re
from typing import Any

# Map Devanagari numerals to standard digits
DEV_DIGIT_MAP = str.maketrans("०१२३४५६७८९", "0123456789")


def _normalize_text_digits(text: str) -> str:
    return text.translate(DEV_DIGIT_MAP)


def extract_numbers_from_text(text: str) -> list[float]:
    """Extract all numbers from text, normalizing commas and currency symbols."""
    normalized = _normalize_text_digits(text)
    # Find all numeric sequences (e.g. 18,000, 72.5, 2026)
    pattern = re.compile(r"(?:₹|\b)(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?%?\b")
    numbers: list[float] = []

    for match in pattern.finditer(normalized):
        raw_int = match.group(1).replace(",", "")
        decimal_part = match.group(2)
        if decimal_part:
            val = float(f"{raw_int}.{decimal_part}")
        else:
            val = float(raw_int)
        numbers.append(val)

    return numbers


def extract_allowable_numbers(facts: list[dict[str, Any]]) -> set[float]:
    """Extract all valid numbers from grounded facts with rounding variations."""
    allowable: set[float] = set()

    for fact in facts:
        val = fact.get("value")
        if isinstance(val, (int, float)):
            num = float(val)
            allowable.add(num)
            allowable.add(float(round(num)))
            allowable.add(float(int(num)))
        elif isinstance(val, str):
            for num in extract_numbers_from_text(val):
                allowable.add(num)
                allowable.add(float(round(num)))
                allowable.add(float(int(num)))

        year = fact.get("source_year")
        if year and isinstance(year, int):
            allowable.add(float(year))

    return allowable


def validate_reply(text: str, facts: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """Validate that every number in text is grounded in facts.

    Tolerates small integers (<= 5) commonly used in bullet points or steps.
    Returns:
        (True, None) if valid.
        (False, reason_str) if ungrounded number detected.
    """
    allowable = extract_allowable_numbers(facts)
    extracted = extract_numbers_from_text(text)

    for num in extracted:
        # Tolerate small integers (1 to 5) used in enumerations/bullet lists
        if num in {1.0, 2.0, 3.0, 4.0, 5.0}:
            continue

        # Check if number matches any allowable number within floating tolerance
        matched = any(abs(num - allowed) < 0.05 for allowed in allowable)
        if not matched:
            return False, f"Ungrounded number detected: {num}"

    return True, None
