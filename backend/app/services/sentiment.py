"""Lexicon-based sentiment analysis and intensity detection for Hindi, Hinglish, and English."""
from __future__ import annotations

import re

# Positive lexical tokens
_POS_EN = {
    "good", "great", "excellent", "best", "helpful", "impressive", "safe", "secure",
    "promising", "interested", "happy", "satisfied", "agree", "yes", "thanks", "thank",
    "respectable", "opportunity", "growth", "high", "stable", "permanent", "proper",
    "clear", "forward", "welcome", "glad", "relief", "support",
}
_POS_HI = {
    "अच्छा", "अच्छी", "अच्छे", "शानदार", "बढ़िया", "सुरक्षित", "संतोषजनक", "खुश",
    "सहमत", "हाँ", "धन्यवाद", "पसंद", "भरोसा", "उम्मीद", "सही", "स्थायी", "प्रगति",
    "सफल", "उज्ज्वल", "राहत", "सम्मान", "बेहतर",
}
_POS_HINGLISH = {
    "achha", "achhi", "achhe", "accha", "acchi", "acche", "badhiya", "sahi", "safe",
    "theek", "thik", "khush", "bharosa", "shandar", "agree", "pasand", "shukriya",
    "dhanyawad", "support", "growth", "behtar", "pragati",
}

# Negative lexical tokens (concerns / resistance)
_NEG_EN = {
    "bad", "poor", "terrible", "low", "waste", "unemployed", "unemployment", "unsafe",
    "dangerous", "worried", "worry", "fear", "afraid", "doubt", "cannot", "cant",
    "wont", "reject", "refuse", "risk", "risky", "expensive", "loss", "impossible",
    "unacceptable", "scared", "hesitant", "concern", "problem", "issue", "mock", "shame",
}
_NEG_HI = {
    "खराब", "बुरा", "बुरी", "कम", "बेरोजगार", "बेरोजगारी", "असुरक्षित", "खतरनाक",
    "चिंता", "डर", "संदेह", "नुकसान", "मुश्किल", "असंभव", "महंगा", "महंगी", "बर्बाद",
    "नहीं", "अस्वीकार", "समस्या", "परेशानी", "झिझक", "अपमान", "लज्जा", "धोखा",
}
_NEG_HINGLISH = {
    "kharab", "bura", "buri", "kam", "berojgar", "berojgari", "unsafe", "khatarnak",
    "chinta", "dar", "darr", "shak", "mushkil", "nahi", "nahin", "naa", "mehenga",
    "mehangi", "barbad", "dhoka", "bekar", "problem", "pareshani", "loss", "ghata",
    "fayda nahi", "izzat nahi",
}

# Intensity markers (strong resistance or strong emotion)
_INTENSITY_PHRASES = [
    re.compile(
        r"\b(bilkul\s+nah[i|n]|kabhi\s+nah[i|n]|kisi\s+bhi\s+k[e|i]emat\s+p[a|e]r\s+nah[i|n])\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(absolutely\s+not|never|under\s+no\s+circumstances|no\s+way|strictly\s+no|completely\s+unacceptable)\b",
        re.IGNORECASE,
    ),
    re.compile(r"(बिल्कुल\s+नहीं|कभी\s+नहीं|किसी\s+भी\s+कीमत\s+पर\s+नहीं|कतई\s+नहीं|असंभव)"),
]

_INTENSITY_WORDS = {
    "never", "absolutely", "impossible", "completely", "strictly", "totally", "extremely",
    "बिल्कुल", "कतई", "असंभव",
}


def analyze_sentiment(text: str, lang: str | None = None) -> tuple[str, float, float]:
    """Analyze utterance sentiment and emotional intensity.

    Returns:
        (sentiment, intensity, score)
        - sentiment: "negative" | "neutral" | "positive"
        - intensity: float in [0.0, 1.0]
        - score: float in [-1.0, 1.0]
    """
    clean_text = text.strip()
    if not clean_text:
        return "neutral", 0.0, 0.0

    lower_text = clean_text.lower()
    # Unicode-aware word split preserving Devanagari combined glyphs and diacritics
    words = set(w for w in re.split(r"[^\w\u0900-\u097F]+", lower_text) if w)

    # 1. Check intensity markers
    has_marker_phrase = any(pattern.search(clean_text) for pattern in _INTENSITY_PHRASES)
    has_marker_word = bool(words & _INTENSITY_WORDS)
    has_exclamation = "!" in clean_text

    # 2. Count positive and negative tokens
    pos_matches = len(words & (_POS_EN | _POS_HI | _POS_HINGLISH))
    neg_matches = len(words & (_NEG_EN | _NEG_HI | _NEG_HINGLISH))

    # Multi-word negative expressions
    for phrase in [
        "too low", "too high", "too far", "cannot afford", "can't afford",
        "afford nahi", "not safe", "safe nahi", "कम है", "चिंता है", "डर है"
    ]:
        if phrase in lower_text or phrase in clean_text:
            neg_matches += 1

    # Strong negative marker phrases directly indicate strong resistance
    if has_marker_phrase:
        neg_matches += 2

    # 3. Derive polarity and score
    if neg_matches > pos_matches:
        sentiment = "negative"
        score = -min(1.0, 0.4 + (neg_matches * 0.2))
    elif pos_matches > neg_matches:
        sentiment = "positive"
        score = min(1.0, 0.4 + (pos_matches * 0.2))
    else:
        sentiment = "neutral"
        score = 0.0

    # 4. Derive intensity in [0.0, 1.0]
    if sentiment == "neutral":
        intensity = 0.2 if (has_marker_word or has_exclamation) else 0.0
    else:
        base_intensity = 0.3
        if has_marker_phrase:
            base_intensity += 0.45
        elif has_marker_word:
            base_intensity += 0.3
        if has_exclamation:
            base_intensity += 0.1
        if (neg_matches + pos_matches) >= 3:
            base_intensity += 0.1
        intensity = min(1.0, round(base_intensity, 2))

    return sentiment, intensity, round(score, 2)
