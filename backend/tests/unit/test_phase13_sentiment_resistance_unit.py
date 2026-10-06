"""Unit tests for Phase 13 sentiment analysis, resistance scoring, and shift tracking."""
from __future__ import annotations

from app.models.conversation import Conversation, Turn
from app.services.resistance import (
    calculate_shift_label,
    compute_resistance_score,
)
from app.services.sentiment import analyze_sentiment


def test_sentiment_lexicon_polarity():
    # English
    sent_pos, inten_pos, score_pos = analyze_sentiment(
        "The placement record is very good and safe."
    )
    assert sent_pos == "positive"
    assert score_pos > 0

    sent_neg, inten_neg, score_neg = analyze_sentiment("The salary is too low and dangerous.")
    assert sent_neg == "negative"
    assert score_neg < 0

    # Hindi
    sent_hi_pos, _, _ = analyze_sentiment("यह बहुत अच्छा और सुरक्षित संस्थान है।")
    assert sent_hi_pos == "positive"

    sent_hi_neg, _, _ = analyze_sentiment("मुझे डर है कि फीस बहुत ज्यादा और महंगी है।")
    assert sent_hi_neg == "negative"

    # Hinglish
    sent_hing_pos, _, _ = analyze_sentiment("Placement record badhiya aur safe hai.")
    assert sent_hing_pos == "positive"

    sent_hing_neg, _, _ = analyze_sentiment("Salary bahut kam hai aur naukri nahi milegi.")
    assert sent_hing_neg == "negative"


def test_sentiment_intensity_markers():
    # Strong resistance markers should spike intensity >= 0.7
    _, inten_en, _ = analyze_sentiment("We will absolutely not allow this training!")
    assert inten_en >= 0.7

    _, inten_hi, _ = analyze_sentiment("हम बिल्कुल नहीं भेजेंगे!")
    assert inten_hi >= 0.7

    _, inten_hing, _ = analyze_sentiment("Beti ko bilkul nahi bhejenge waha!")
    assert inten_hing >= 0.7

    # Mild statement without markers
    _, inten_mild, _ = analyze_sentiment("Fees thodi kam ho sakti hai kya?")
    assert inten_mild < 0.7


def test_resistance_score_bounds_and_clipping():
    class DummyDB:
        def scalars(self, query):
            class DummyResult:
                def all(self):
                    return []
            return DummyResult()

    conv = Conversation(student_id=1, room_id=None)
    db = DummyDB()

    # 1. High-intensity negative safety objection -> high resistance
    rs_high = compute_resistance_score(
        topic="safety",
        sentiment="negative",
        intensity=0.9,
        conversation=conv,
        db=db,
    )
    assert 0.0 <= rs_high <= 1.0
    assert rs_high >= 0.6

    # 2. Positive affirmation -> low resistance
    rs_low = compute_resistance_score(
        topic="income",
        sentiment="positive",
        intensity=0.1,
        conversation=conv,
        db=db,
    )
    assert 0.0 <= rs_low <= 1.0
    assert rs_low <= 0.2

    # 3. Extreme theoretical values remain strictly clipped in [0.0, 1.0]
    rs_clipped_max = compute_resistance_score(
        topic="safety",
        sentiment="negative",
        intensity=1.5,
        conversation=conv,
        db=db,
    )
    assert rs_clipped_max <= 1.0


def test_shift_label_calculation():
    # 1. Softened (started negative, ended positive)
    turns_softened = [
        Turn(speaker="parent", sentiment="negative"),
        Turn(speaker="parent", sentiment="negative"),
        Turn(speaker="assistant", sentiment="neutral"),
        Turn(speaker="parent", sentiment="neutral"),
        Turn(speaker="parent", sentiment="positive"),
        Turn(speaker="parent", sentiment="positive"),
    ]
    assert calculate_shift_label(turns_softened) == "softened"

    # 2. Hardened (started neutral/positive, ended negative)
    turns_hardened = [
        Turn(speaker="learner", sentiment="positive"),
        Turn(speaker="parent", sentiment="positive"),
        Turn(speaker="assistant", sentiment="neutral"),
        Turn(speaker="parent", sentiment="negative"),
        Turn(speaker="parent", sentiment="negative"),
        Turn(speaker="parent", sentiment="negative"),
    ]
    assert calculate_shift_label(turns_hardened) == "hardened"

    # 3. Unchanged
    turns_unchanged = [
        Turn(speaker="parent", sentiment="neutral"),
        Turn(speaker="assistant", sentiment="neutral"),
        Turn(speaker="parent", sentiment="neutral"),
    ]
    assert calculate_shift_label(turns_unchanged) == "unchanged"

    # Short conversation
    assert calculate_shift_label([Turn(speaker="parent", sentiment="negative")]) == "unchanged"
