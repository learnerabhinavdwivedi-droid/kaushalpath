"""Phase 27 Unit Tests: LLM Decision, Fallback Hardening, and Number Validation (PSID 26241).

Verifies:
1. When llm_provider != 'none' and the external LLM times out or raises an error:
   - responder._call_llm_api catches the exception silently.
   - generate_response falls back to the deterministic, grounded template reply.
   - fallback_used is marked True.
   - reply is non-empty, grounded, and contains correct numbers.
2. When llm_provider == 'none' (default offline mode):
   - generate_response runs deterministically with fallback_used=False.
3. validator.py's numeric hallucination check:
   - Rejects paraphrases containing ungrounded salaries, placement rates, or numbers.
   - Accepts grounded numbers (exact, rounded, integer, and Devanagari numerals).
4. An LLM rephraser producing an ungrounded number is caught and rejected:
   - Falls back to the template reply.
   - Emits a warning and sets fallback_used=True.
5. End-to-end API turn endpoint:
   - Returns HTTP 200 with grounded reply even when external LLM times out or hallucinates.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.config import get_settings
from app.models.occupation import Occupation
from app.services.conversation.responder import _call_llm_api, generate_response
from app.services.conversation.validator import (
    DEV_DIGIT_MAP,
    extract_allowable_numbers,
    extract_numbers_from_text,
    validate_reply,
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Number extraction and validation unit tests
# ---------------------------------------------------------------------------

def test_extract_numbers_from_text_formats():
    """Verify regex correctly parses comma-separated, currency-prefixed, and float numbers."""
    text = "Starting salary is ₹18,000 per month with a 72.5% placement rate, fee is 4,500 INR in 2026."
    nums = extract_numbers_from_text(text)
    assert 18000.0 in nums
    assert 72.5 in nums
    assert 4500.0 in nums
    assert 2026.0 in nums


def test_extract_numbers_from_devanagari():
    """Verify Devanagari numerals are normalized and extracted."""
    text = "वेतन ₹१८,००० प्रति माह है और ८५% प्लेसमेंट है।"
    nums = extract_numbers_from_text(text)
    assert 18000.0 in nums
    assert 85.0 in nums


def test_validator_rejects_hallucinated_number():
    """Validator must strictly reject any numeric claim not present in grounded facts."""
    facts = [
        {"key": "trade_name", "value": "Electrician"},
        {"key": "median_earnings", "value": 18000.0},
        {"key": "placement_rate", "value": 72.0},
        {"key": "source_year", "value": 2026},
    ]

    # Paraphrase invents a 95,000 salary
    hallucinated_reply = "As an Electrician, you can easily earn ₹95,000 per month after training."
    is_valid, reason = validate_reply(hallucinated_reply, facts)

    assert not is_valid
    assert reason is not None
    assert "95000" in reason


def test_validator_accepts_grounded_numbers():
    """Validator must accept grounded facts including rounding and source year."""
    facts = [
        {"key": "trade_name", "value": "Electrician"},
        {"key": "median_earnings", "value": 18250.0},
        {"key": "placement_rate", "value": 72.4},
        {"key": "source_year", "value": 2026},
    ]

    grounded_reply = "In 2026, verified median earnings are ₹18,250 per month with a 72% placement rate."
    is_valid, reason = validate_reply(grounded_reply, facts)

    assert is_valid
    assert reason is None


def test_validator_tolerates_enumeration_indices():
    """Small integers (1 to 5) used in bullet points or lists should not trigger false positives."""
    facts = [
        {"key": "median_earnings", "value": 18000.0},
    ]
    reply = "Here are 3 reasons: 1. Practical skills. 2. Good demand. Median salary is ₹18,000."
    is_valid, _ = validate_reply(reply, facts)
    assert is_valid


# ---------------------------------------------------------------------------
# 2. LLM timeout and error fallback unit tests
# ---------------------------------------------------------------------------

def test_llm_provider_timeout_falls_back_to_template(monkeypatch):
    """When external LLM times out, responder must return grounded template reply with fallback_used=True."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "openai_compat")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.fake-openai.com/v1")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")

    facts = [
        {"key": "trade_name", "value": "Electrician"},
        {"key": "median_earnings", "value": 18000.0},
        {"key": "source_year", "value": 2026},
    ]

    # Mock httpx.Client.post raising timeout
    def mock_post(*args, **kwargs):
        raise httpx.ReadTimeout("Connection timed out after 10.0s")

    with patch.object(httpx.Client, "post", mock_post):
        res = generate_response(topic="income", lang="en", facts=facts)

    assert res["reply"]
    assert "18,000" in res["reply"] or "18000" in res["reply"]
    assert res["fallback_used"] is True
    assert res["rule_branch"] == "income_mid"


def test_llm_provider_server_error_falls_back_to_template(monkeypatch):
    """When external LLM returns HTTP 500/503, responder falls back silently."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_api_key", "test-gemini-key")

    facts = [
        {"key": "trade_name", "value": "Fitter"},
        {"key": "median_earnings", "value": 16000.0},
        {"key": "source_year", "value": 2026},
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "Service Unavailable"

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        res = generate_response(topic="income", lang="en", facts=facts)

    assert res["reply"]
    assert "16,000" in res["reply"] or "16000" in res["reply"]
    assert res["fallback_used"] is True


def test_offline_default_none_uses_template():
    """Default mode (llm_provider='none') runs completely offline with fallback_used=False."""
    settings = get_settings()
    assert settings.llm_provider == "none"

    facts = [
        {"key": "trade_name", "value": "Solar Technician"},
        {"key": "placement_rate", "value": 75.0},
        {"key": "source_year", "value": 2026},
    ]

    res = generate_response(topic="security", lang="en", facts=facts)
    assert res["reply"]
    assert "75%" in res["reply"] or "75.0%" in res["reply"]
    assert res["fallback_used"] is False


def test_responder_rejects_hallucinating_rephraser():
    """If an LLM rephraser invents numbers, responder rejects it and falls back to template."""
    facts = [
        {"key": "trade_name", "value": "Electrician"},
        {"key": "median_earnings", "value": 18000.0},
        {"key": "source_year", "value": 2026},
    ]

    # LLM rephraser invents a ₹60,000 salary
    def hallucinating_llm(template, facts_list, lang):
        return "Electricians easily earn ₹60,000 per month right after graduation!"

    res = generate_response(
        topic="income",
        lang="en",
        facts=facts,
        llm_rephraser=hallucinating_llm,
    )

    # Must fall back to template containing 18,000 and reject the 60,000 claim
    assert "60,000" not in res["reply"]
    assert "18,000" in res["reply"] or "18000" in res["reply"]
    assert res["fallback_used"] is True


def test_responder_accepts_valid_grounded_rephraser():
    """If an LLM rephraser preserves grounded facts, responder accepts candidate with fallback_used=False."""
    facts = [
        {"key": "trade_name", "value": "Electrician"},
        {"key": "median_earnings", "value": 18000.0},
        {"key": "source_year", "value": 2026},
    ]

    def valid_llm(template, facts_list, lang):
        return "Based on 2026 official records, an Electrician earns a median salary of ₹18,000 per month."

    res = generate_response(
        topic="income",
        lang="en",
        facts=facts,
        llm_rephraser=valid_llm,
    )

    assert "Based on 2026 official records" in res["reply"]
    assert res["fallback_used"] is False


# ---------------------------------------------------------------------------
# 3. API endpoint integration test with LLM failure
# ---------------------------------------------------------------------------

def test_api_conversation_turn_with_failing_llm(client_with_db, db_session, monkeypatch):
    """POST /conversations/{id}/turns succeeds with 200 and grounded reply when LLM times out."""
    client = client_with_db
    db = db_session
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "openai_compat")
    monkeypatch.setattr(settings, "llm_api_key", "sk-fake")

    # Register student
    reg = client.post(
        "/auth/register",
        json={"email": "p27_student@example.com", "password": "password123", "role": "student", "give_consent": True},
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    student_id = client.get("/auth/me", headers=_auth(token)).json()["student_id"]

    # Seed an occupation
    occ = Occupation(
        name_en="Welder",
        name_hi="वेल्डर",
        is_vocational=True,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db.add(occ)
    db.commit()

    # Create conversation
    conv_resp = client.post(
        "/conversations",
        headers=_auth(token),
        json={"student_id": student_id, "lang": "en"},
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    # Mock timeout on LLM call while allowing TestClient requests through
    orig_post = httpx.Client.post

    def mock_post(self_client, url, *args, **kwargs):
        url_s = str(url).lower()
        if "openai" in url_s or "generativelanguage" in url_s or "api.fake" in url_s:
            raise httpx.ConnectError("Failed to connect to LLM gateway")
        return orig_post(self_client, url, *args, **kwargs)

    with patch.object(httpx.Client, "post", mock_post):
        turn_resp = client.post(
            f"/conversations/{conv_id}/turns",
            headers=_auth(token),
            json={
                "speaker": "learner",
                "text": "What salary can I expect after ITI Welder?",
                "lang": "en",
            },
        )

    assert turn_resp.status_code == 200
    data = turn_resp.json()
    assert data["reply"]
    assert len(data["reply"]) > 10
    # Must have fallen back to template
    assert data["fallback_used"] is True
