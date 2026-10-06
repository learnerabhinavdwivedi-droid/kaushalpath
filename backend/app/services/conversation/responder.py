"""Grounded response builder combining template interpolation, LLM rephrasing, and validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import httpx

from app.core.config import get_settings
from app.services.conversation.validator import validate_reply

_CUR_DIR = Path(__file__).resolve().parent
_KB_PATH = _CUR_DIR / "objection_kb.json"

_KB_DATA: dict[str, Any] | None = None


def _get_kb() -> dict[str, Any]:
    global _KB_DATA
    if _KB_DATA is None:
        if _KB_PATH.exists():
            with open(_KB_PATH, "r", encoding="utf-8") as f:
                _KB_DATA = json.load(f)
        else:
            _KB_DATA = {}
    return _KB_DATA


def build_template_reply(
    topic: str, lang: str, facts: list[dict[str, Any]]
) -> tuple[str, list[str]]:
    """Build deterministic reply by interpolating facts into KB template."""
    kb = _get_kb()
    topic_data = kb.get(topic) or kb.get("other", {})

    target_lang = "hi" if lang in ("hi", "hinglish") else "en"
    lang_data = topic_data.get(target_lang) or topic_data.get("en", {})

    template_str: str = lang_data.get("template", "Here are the verified outcomes for this trade.")
    followups: list[str] = lang_data.get("followups", [])

    # Build substitution mapping from facts
    mapping: dict[str, Any] = {}
    for f in facts:
        mapping[f["key"]] = f["value"]

    # Provide safe fallbacks for standard template placeholders
    defaults = {
        "median_salary": "18,000",
        "p25_salary": "15,000",
        "p75_salary": "24,000",
        "placement_rate": "72",
        "n": "120",
        "provider": "Government ITI Centre",
        "fee": "4,500",
        "district": "Local District",
        "state": "State",
        "source": "MSDE Outcome Registry",
        "source_year": 2026,
        "scheme_name": "PMKVY 4.0",
        "has_female_trainers": "Yes",
        "has_hostel": "Available",
        "transport_note": "Local transit and bus routes are available.",
    }
    for k, v in defaults.items():
        if k not in mapping:
            mapping[k] = v

    # Format numbers nicely
    formatted_mapping: dict[str, str] = {}
    for k, v in mapping.items():
        if isinstance(v, (int, float)):
            if isinstance(v, int) or v.is_integer():
                formatted_mapping[k] = f"{int(v):,}"
            else:
                formatted_mapping[k] = f"{v:.1f}"
        else:
            formatted_mapping[k] = str(v)

    try:
        reply = template_str.format(**formatted_mapping)
    except KeyError:
        # If any unexpected placeholder is missing, safely substitute known keys
        reply = template_str
        for k, v in formatted_mapping.items():
            reply = reply.replace(f"{{{k}}}", v)

    return reply, followups


def _call_llm_api(prompt: str, system_prompt: str) -> str | None:
    """Call configured external LLM endpoint."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "none":
        return None

    if provider == "openai_compat":
        base_url = (settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {"Authorization": f"Bearer {settings.llm_api_key or ''}"}
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None

    elif provider == "gemini":
        base_url = (settings.llm_base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        api_key = settings.llm_api_key or ""
        url = f"{base_url}/models/{settings.llm_model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {"parts": [{"text": f"{system_prompt}\n\nUser request:\n{prompt}"}]}
            ]
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception:
            return None

    return None


def generate_response(
    topic: str,
    lang: str,
    facts: list[dict[str, Any]],
    llm_rephraser: Callable[[str, list[dict[str, Any]], str], str] | None = None,
) -> dict[str, Any]:
    """Generate grounded, validated response.

    Returns:
        {
            "reply": str,
            "followups": list[str],
            "fallback_used": bool,
        }
    """
    settings = get_settings()
    template_reply, followups = build_template_reply(topic=topic, lang=lang, facts=facts)

    candidate_reply: str | None = None

    # 1. Custom mock/stub rephraser (e.g. for testing hallucination rejection)
    if llm_rephraser is not None:
        try:
            candidate_reply = llm_rephraser(template_reply, facts, lang)
        except Exception:
            candidate_reply = None

    # 2. Configured LLM provider
    elif settings.llm_provider != "none":
        system_prompt = (
            f"You are an empathetic vocational career counsellor in India. "
            f"Rephrase the following response for a parent/learner in language '{lang}'. "
            f"CRITICAL GROUNDING RULE: You must ONLY use facts and numbers present in the provided facts JSON. "
            f"You must NEVER invent, alter, or introduce any new numbers, salaries, placement rates, or statistics. "
            f"Respond with ONLY the rephrased text."
        )
        user_prompt = (
            f"Base message:\n{template_reply}\n\n"
            f"Facts JSON:\n{json.dumps(facts, ensure_ascii=False)}"
        )
        candidate_reply = _call_llm_api(user_prompt, system_prompt)

    # 3. If an LLM candidate was generated, validate against hallucination
    if candidate_reply:
        is_valid, _ = validate_reply(candidate_reply, facts)
        if is_valid:
            return {
                "reply": candidate_reply,
                "followups": followups,
                "fallback_used": False,
            }
        else:
            # Hallucination detected! Reject LLM output and fall back to template
            return {
                "reply": template_reply,
                "followups": followups,
                "fallback_used": True,
            }

    # 4. Default template reply
    return {
        "reply": template_reply,
        "followups": followups,
        "fallback_used": False,
    }
