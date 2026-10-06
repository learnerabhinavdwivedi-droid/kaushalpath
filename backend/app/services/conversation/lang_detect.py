"""Language detection for conversational counselling (Devanagari, Hinglish, English)."""
from __future__ import annotations

import re

# Devanagari Unicode block (\u0900 - \u097F)
DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")

# Distinctive transliterated Hindi/Hinglish vocabulary tokens (Latin script)
HINGLISH_TOKENS = {
    "kya", "kyu", "kyun", "kaise", "kitna", "kitni", "kitne", "hai", "hain",
    "hoga", "hogi", "honge", "milega", "milegi", "milte", "paise", "kamai",
    "tankha", "tanha", "naukri", "nokri", "lagti", "laga", "meri", "mera",
    "mere", "beti", "beta", "padhai", "padai", "kharcha", "kharch", "fees",
    "door", "dur", "suraksha", "ladki", "ladkiyan", "ladko", "ladke", "izzat",
    "samaj", "samaaj", "bhavishya", "sarkari", "yojana", "kaam", "chahiye",
    "nahi", "nahin", "naa", "batao", "bataiye", "puchna", "toh", "to", "ye",
    "yeh", "woh", "wo", "accha", "achha", "achhi", "sahi", "karega", "karegi",
    "parivar", "ghar", "karna", "karni", "bhejna", "bheje", "chinta", "dar",
    "darr", "vishwas", "bharosa", "paisa", "raksha", "sikhega", "sikhegi",
    "baat", "sahayata", "madad", "sir", "madam", "suno", "bolo",
}

# Tokens that only appear in Hinglish and are very strong indicators
STRONG_HINGLISH_TOKENS = {
    "kya", "kyun", "kaise", "kitna", "kitni", "kitne", "hai", "hain", "hoga",
    "hogi", "milega", "milegi", "naukri", "kamai", "tanha", "tankha", "beti",
    "beta", "padhai", "kharcha", "suraksha", "ladki", "ladkiyan", "izzat",
    "samaj", "samaaj", "chahiye", "nahin", "nahi", "batao", "bataiye", "achha",
    "accha", "karega", "karegi", "parivar", "chinta", "bharosa", "madad",
}


def detect_language(text: str) -> str:
    """Detect language of a conversational utterance.

    Returns:
        - "hi": Devanagari script detected.
        - "hinglish": Latin script containing Hindi lexical tokens.
        - "en": English or fallback.
    """
    if not text or not text.strip():
        return "en"

    # 1. Devanagari check
    if DEVANAGARI_REGEX.search(text):
        return "hi"

    # 2. Hinglish token check (Latin text)
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return "en"

    strong_matches = sum(1 for w in words if w in STRONG_HINGLISH_TOKENS)
    general_matches = sum(1 for w in words if w in HINGLISH_TOKENS)

    if strong_matches >= 1 or general_matches >= 2:
        return "hinglish"

    return "en"
