"""Intent and Topic classification using rules and multilingual embedding nearest-neighbour."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.ml.retrieval.embedder import get_embedder

_CUR_DIR = Path(__file__).resolve().parent
_EXEMPLARS_PATH = _CUR_DIR / "intent_exemplars.json"

# Rule patterns for intent classification
_INTENT_PATTERNS = [
    (
        "escalate",
        re.compile(
            r"\b(counsellor|counselor|human|expert|call|phone|talk\s+to|baat\s+kar|baat\s+karni|officer|madad|contact)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "greet",
        re.compile(
            r"^(hi|hello|hey|namaste|pranam|namaskar|good\s+morning|good\s+afternoon|good\s+evening)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "object",
        re.compile(
            r"\b(too\s+low|too\s+high|cannot\s+afford|worried|fear|fearful|unsafe|darr|chinta|mushkil|impossible|na\s+mile|nahi\s+milega|log\s+kya\s+kahenge|izzat\s+nahi|kam\s+lagta|nahi\s+ho\s+sakta|berojgar)\b",
            re.IGNORECASE,
        ),
    ),
]

# Rule patterns for topic classification
_TOPIC_PATTERNS = [
    (
        "income",
        re.compile(
            r"\b(salary|salaries|wage|wages|earn|earning|earnings|income|pay|kamai|tankha|tanha|paise|paisa|package|ctc|मासिक\s+वेतन|वेतन|कमाई|आमदनी|पैसे)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "security",
        re.compile(
            r"\b(placement|placements|placed|permanent|job\s+security|unemployed|recruit|recruitment|naukri|pakki|berojgari|प्लेसमेंट|रोजगार|नौकरी)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "cost",
        re.compile(
            r"\b(fee|fees|cost|costs|expensive|stipend|scholarship|afford|free|kharcha|kharch|mehenga|admission\s+charge|शुल्क|फीस|खर्चा|छात्रवृत्ति)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "safety",
        re.compile(
            r"\b(safe|safety|secure|girl|girls|female|women|daughter|beti|ladki|ladkiyan|suraksha|harassment|cctv|workshop\s+safety|सुरक्षा|सुरक्षित|महिला|लड़की|लड़कियों|बेटी)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "distance",
        re.compile(
            r"\b(distance|far|away|hostel|commute|travel|relocate|kilometer|km|bus|transport|door|dur|aana\s+jana|शहर|हॉस्टल|दूरी|दूर|परिवहन|यात्रा)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "social",
        re.compile(
            r"\b(respect|social|prestige|status|reputation|dignity|society|samaj|samaaj|izzat|relatives|degree\s+vs|degree|प्रतिष्ठा|इज्जत|मान-सम्मान|समाज)\b",
            re.IGNORECASE,
        ),
    ),
]


class IntentClassifier:
    def __init__(self, exemplars_path: Path = _EXEMPLARS_PATH) -> None:
        self.exemplars_path = exemplars_path
        self.exemplars: list[dict[str, Any]] = []
        self._exemplar_texts: list[str] = []
        self._embeddings: Any | None = None
        self._load_exemplars()

    def _load_exemplars(self) -> None:
        if self.exemplars_path.exists():
            with open(self.exemplars_path, encoding="utf-8") as f:
                self.exemplars = json.load(f)
            self._exemplar_texts = [e["text"] for e in self.exemplars]

    def _get_embeddings(self) -> Any | None:
        if self._embeddings is not None:
            return self._embeddings
        embedder = get_embedder()
        if embedder.available() and self._exemplar_texts:
            try:
                import numpy as np

                vectors = embedder.encode(self._exemplar_texts, normalize_embeddings=True)
                self._embeddings = np.array(vectors)
                return self._embeddings
            except Exception:
                return None
        return None

    def classify(self, text: str) -> tuple[str, str, float]:
        """Classify utterance into (intent, topic, confidence).

        Intents: "inquire", "object", "escalate", "greet", "general"
        Topics: "income", "security", "social", "safety", "distance", "cost", "other"
        """
        clean_text = text.strip()
        if not clean_text:
            return "general", "other", 0.0

        rule_intent: str | None = None
        for intent, pattern in _INTENT_PATTERNS:
            if pattern.search(clean_text):
                rule_intent = intent
                break

        rule_topic: str | None = None
        for topic, pattern in _TOPIC_PATTERNS:
            if pattern.search(clean_text):
                rule_topic = topic
                break

        # If rule matched both with high specificity, return high confidence
        if rule_intent and rule_topic:
            return rule_intent, rule_topic, 0.95

        # Check semantic similarity using embedder if available
        nn_intent: str | None = None
        nn_topic: str | None = None
        nn_score = 0.0

        embeddings = self._get_embeddings()
        if embeddings is not None:
            embedder = get_embedder()
            try:
                import numpy as np

                query_vec = np.array(embedder.encode(clean_text, normalize_embeddings=True))
                # Cosine similarity because embeddings are normalized
                scores = np.dot(embeddings, query_vec)
                best_idx = int(np.argmax(scores))
                nn_score = float(scores[best_idx])
                best_match = self.exemplars[best_idx]
                nn_intent = best_match.get("intent")
                nn_topic = best_match.get("topic")
            except Exception:
                pass

        final_intent = rule_intent or (nn_intent if nn_score >= 0.50 else "inquire")
        final_topic = rule_topic or (nn_topic if nn_score >= 0.50 else "other")
        conf = max(0.85 if (rule_intent or rule_topic) else 0.5, nn_score)

        return final_intent, final_topic, round(conf, 2)


_classifier: IntentClassifier | None = None


def get_intent_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_utterance(text: str) -> tuple[str, str, float]:
    """Convenience functional interface."""
    return get_intent_classifier().classify(text)
