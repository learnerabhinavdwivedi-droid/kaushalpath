"""Unit tests for Phase 12 conversation engine components:

1. Language detection (Devanagari -> hi, transliterated -> hinglish, else -> en)
2. Intent & topic classifier on 30+ labelled lines (accuracy >= 85%)
3. Numeric hallucination validator (grounded vs ungrounded)
4. Objection KB template validation (zero literal numbers in raw templates)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.services.conversation.intent import classify_utterance
from app.services.conversation.lang_detect import detect_language
from app.services.conversation.validator import (
    validate_reply,
)


def test_lang_detect_devanagari():
    assert detect_language("इस ट्रेड में क्या स्कोप है?") == "hi"
    assert detect_language("वेतन कितना मिलता है?") == "hi"
    assert detect_language("लड़कियों के लिए हॉस्टल है क्या?") == "hi"


def test_lang_detect_hinglish():
    assert detect_language("Starting salary kitni milegi is trade me?") == "hinglish"
    assert detect_language("Beti ke liye workshop safe hai kya?") == "hinglish"
    assert detect_language("Kitna kharcha hoga fees ka?") == "hinglish"
    assert detect_language("Job placement pakki milegi ya nahi?") == "hinglish"


def test_lang_detect_english():
    assert detect_language("What is the average placement rate?") == "en"
    assert detect_language("Is there a hostel facility near the centre?") == "en"
    assert detect_language("How much are the total tuition fees?") == "en"


def test_objection_kb_has_no_literal_numbers():
    base = Path(__file__).resolve().parents[2]
    kb_path = base / "app" / "services" / "conversation" / "objection_kb.json"
    assert kb_path.exists()
    with open(kb_path, encoding="utf-8") as f:
        data = json.load(f)

    # Check that in every topic and every language template, there are NO hardcoded numbers
    # (only placeholders like {median_salary}, {placement_rate}, {n}, {fee})
    digit_pattern = re.compile(r"\b\d{2,}\b")
    for topic, lang_map in data.items():
        for lang, item in lang_map.items():
            template = item.get("template", "")
            # Remove placeholder brackets e.g. {median_salary}
            clean_template = re.sub(r"\{[a-zA-Z0-9_]+\}", "", template)
            matches = digit_pattern.findall(clean_template)
            assert matches == [], f"Found literal numbers {matches} in template: {topic}.{lang}"


def test_numeric_validator_grounded_vs_hallucinated():
    facts = [
        {"key": "median_salary", "value": 18000, "source_year": 2026},
        {"key": "p25_salary", "value": 14000, "source_year": 2026},
        {"key": "p75_salary", "value": 24000, "source_year": 2026},
        {"key": "placement_rate", "value": 72.5, "source_year": 2026},
        {"key": "n", "value": 120, "source_year": 2026},
        {"key": "fee", "value": 4500, "source_year": 2026},
    ]

    # 1. Valid response with grounded facts and bullet list integers (1, 2)
    valid_text = (
        "Based on 2026 data, the median salary is ₹18,000 (ranging from ₹14,000 to ₹24,000). "
        "The placement rate is 72.5% across 120 students. Fees are ₹4,500. "
        "Steps: 1. Apply online. 2. Verify documents."
    )
    is_valid, err = validate_reply(valid_text, facts)
    assert is_valid is True
    assert err is None

    # 2. Hallucinated salary
    hallucinated_salary = "The starting salary is ₹45,000 per month."
    is_valid, err = validate_reply(hallucinated_salary, facts)
    assert is_valid is False
    assert "45000" in err

    # 3. Hallucinated placement rate
    hallucinated_rate = "The placement rate is 99%."
    is_valid, err = validate_reply(hallucinated_rate, facts)
    assert is_valid is False
    assert "99" in err


def test_intent_classification_on_30_labelled_lines():
    labeled_data = [
        # income
        ("What is the average salary in this vocation?", "income"),
        ("औसत मासिक वेतन कितना मिलता है?", "income"),
        ("Starting me kitni salary milegi?", "income"),
        ("Monthly wages are too low for my family", "income"),
        ("वेतन बहुत कम है इतने पैसे में नहीं होगा", "income"),
        # security
        ("What is the campus placement percentage?", "security"),
        ("इस ट्रेड में प्लेसमेंट कितना है?", "security"),
        ("Placement guarantee hai ya job khud dhundhni hogi?", "security"),
        ("Will the job be permanent or temporary?", "security"),
        ("नौकरी पक्की मिलेगी या समय बर्बाद होगा?", "security"),
        # cost
        ("How much are the total course fees?", "cost"),
        ("इस प्रशिक्षण की फीस कितनी है?", "cost"),
        ("Total fees kitni lagegi admission ki?", "cost"),
        ("Can we get government scholarship or stipend?", "cost"),
        ("छात्रवृत्ति या मुफ्त ट्रेनिंग मिलती है क्या?", "cost"),
        # safety
        ("Is the workshop safe for female candidates?", "safety"),
        ("क्या यह केंद्र लड़कियों के लिए सुरक्षित है?", "safety"),
        ("Center ladkiyo ke liye safe hai kya?", "safety"),
        ("Are there female trainers and CCTV guards?", "safety"),
        ("महिला प्रशिक्षक और सुरक्षा व्यवस्था है?", "safety"),
        # distance
        ("How far is the institute from our city?", "distance"),
        ("घर से केंद्र की दूरी कितनी है?", "distance"),
        ("Center kitni door hai ghar se?", "distance"),
        ("Is hostel accommodation available for students?", "distance"),
        ("क्या रहने के लिए हॉस्टल सुविधा है?", "distance"),
        # social
        ("What is the social prestige of ITI trades?", "social"),
        ("समाज में इस काम की क्या इज्जत है?", "social"),
        ("Samaj me is trade ki izzat kaisi hai?", "social"),
        ("People look down upon technician jobs", "social"),
        ("लोग क्या कहेंगे कि आईटीआई कर रहा है", "social"),
        # other / escalation
        ("I want to speak with a human counsellor", "other"),
        ("कृपया मुझे किसी काउंसलर से बात करवाएं", "other"),
        ("Counsellor sir se call par baat karwa do", "other"),
        ("Hello, good morning, how are you?", "other"),
        ("नमस्ते मुझे करियर गाइडेंस चाहिए", "other"),
    ]

    assert len(labeled_data) >= 30
    correct = 0
    for text, expected_topic in labeled_data:
        _, pred_topic, _ = classify_utterance(text)
        if pred_topic == expected_topic:
            correct += 1

    accuracy = correct / len(labeled_data)
    msg = f"Expected accuracy >= 0.85, got {accuracy:.2f} ({correct}/{len(labeled_data)})"
    assert accuracy >= 0.85, msg
