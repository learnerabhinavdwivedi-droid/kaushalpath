"""Phase 26 Unit Tests: Household Income-Band Tailoring (PS Row R7).

Covers:
1. Same persona, held constant except income_band, produces different reason codes
   (AFFORDABLE_FOR_INCOME_BAND vs HIGH_FEE_RELATIVE_TO_INCOME_BAND) across low/mid/high bands.
2. Same objection topic (income or cost), same persona otherwise, produces different
   fact ordering/selection in conversational replies across income bands:
   - low: leads with scheme/stipend/waiver facts before earnings;
   - high: leads with career progression/NSQF level-up/private-sector placement facts.
3. Bilingual Hindi & English parity for all tailored objection branches.
4. Transparent rule-based branch logging verification.
5. Extracted features affordability signal consistency.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import pytest

from app.core.budget import (
    INCOME_AFFORDABILITY_THRESHOLDS,
    is_affordable_for_income_band,
    normalize_income_band,
    scheme_subsidy_pct,
)
from app.ml.explain.reason_codes import generate_reason_codes
from app.ml.ranking.features import extract_features
from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student
from app.services.conversation.grounder import ground_facts
from app.services.conversation.responder import build_template_reply, generate_response


class DummyStudent:
    """Mock student model holding attributes for pure function testing."""

    def __init__(
        self,
        income_band: str | None = "mid",
        budget_band: str = "mid",
        edu_level: str = "10th",
        district: str = "Pune",
        state: str = "Maharashtra",
        language: str = "en",
        max_duration_months: int = 12,
    ) -> None:
        self.id = 101
        self.income_band = income_band
        self.budget_band = budget_band
        self.edu_level = edu_level
        self.district = district
        self.state = state
        self.language = language
        self.max_duration_months = max_duration_months


class DummyCourse:
    """Mock course model."""

    def __init__(
        self,
        id: int = 1,
        fee_inr: float = 20000.0,
        nsqf_level: int = 4,
        duration_months: int = 12,
        occupation_id: int = 10,
        min_edu: str = "10th",
    ) -> None:
        self.id = id
        self.fee_inr = fee_inr
        self.nsqf_level = nsqf_level
        self.duration_months = duration_months
        self.occupation_id = occupation_id
        self.min_edu = min_edu


class DummyOccupation:
    """Mock occupation model."""

    def __init__(
        self,
        id: int = 10,
        title: str = "Solar PV Installation Technician",
        nsqf_level: int = 4,
        is_vocational: bool = True,
    ) -> None:
        self.id = id
        self.title = title
        self.nsqf_level = nsqf_level
        self.is_vocational = is_vocational
        self.riasec_r = 0.8
        self.riasec_i = 0.6
        self.riasec_a = 0.2
        self.riasec_s = 0.3
        self.riasec_e = 0.4
        self.riasec_c = 0.5


# =========================================================================
# 1. Reason Codes Differentiation across Income Bands
# =========================================================================


def test_income_band_reason_codes_differentiates_across_bands() -> None:
    """Same persona, held constant except income_band, produces different reason codes."""
    occupation = DummyOccupation()
    riasec = {"R": 0.85, "I": 0.65, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.5}
    aptitude = {"num": 0.7, "verbal": 0.6, "spatial": 0.8, "mech": 0.85}

    # Course fee = INR 20,000 (exceeds low limit 10k, within mid limit 35k & high limit 80k)
    course_20k = DummyCourse(fee_inr=20000.0)

    # 1. Low income band (lt_1l / low) -> Fee 20k is high relative to income band
    student_low = DummyStudent(income_band="low", budget_band="low")
    feats_low = extract_features(student_low, occupation, course_20k, riasec, aptitude, net_cost_ratio=1.0)
    reasons_low = generate_reason_codes(student_low, occupation, course_20k, feats_low, riasec, lang="en")
    codes_low = [r["code"] for r in reasons_low]

    assert "HIGH_FEE_RELATIVE_TO_INCOME_BAND" in codes_low, (
        f"Low-income persona expected HIGH_FEE_RELATIVE_TO_INCOME_BAND for INR 20k fee, got {codes_low}"
    )
    assert "AFFORDABLE_FOR_INCOME_BAND" not in codes_low

    # 2. Medium income band (1l_3l / mid) -> Fee 20k is affordable for income band
    student_mid = DummyStudent(income_band="mid", budget_band="mid")
    feats_mid = extract_features(student_mid, occupation, course_20k, riasec, aptitude, net_cost_ratio=0.33)
    reasons_mid = generate_reason_codes(student_mid, occupation, course_20k, feats_mid, riasec, lang="en")
    codes_mid = [r["code"] for r in reasons_mid]

    assert "AFFORDABLE_FOR_INCOME_BAND" in codes_mid, (
        f"Mid-income persona expected AFFORDABLE_FOR_INCOME_BAND for INR 20k fee, got {codes_mid}"
    )
    assert "HIGH_FEE_RELATIVE_TO_INCOME_BAND" not in codes_mid

    # 3. High income band (gt_6l / high) -> Fee 20k is affordable for income band
    student_high = DummyStudent(income_band="high", budget_band="high")
    feats_high = extract_features(student_high, occupation, course_20k, riasec, aptitude, net_cost_ratio=0.0)
    reasons_high = generate_reason_codes(student_high, occupation, course_20k, feats_high, riasec, lang="en")
    codes_high = [r["code"] for r in reasons_high]

    assert "AFFORDABLE_FOR_INCOME_BAND" in codes_high
    assert "HIGH_FEE_RELATIVE_TO_INCOME_BAND" not in codes_high

    # Course fee = INR 50,000 (exceeds low limit 10k and mid limit 35k, within high limit 80k)
    course_50k = DummyCourse(fee_inr=50000.0)

    # For mid-income student, 50k fee should now trigger HIGH_FEE_RELATIVE_TO_INCOME_BAND
    feats_mid_50k = extract_features(student_mid, occupation, course_50k, riasec, aptitude, net_cost_ratio=0.83)
    reasons_mid_50k = generate_reason_codes(student_mid, occupation, course_50k, feats_mid_50k, riasec, lang="en")
    codes_mid_50k = [r["code"] for r in reasons_mid_50k]
    assert "HIGH_FEE_RELATIVE_TO_INCOME_BAND" in codes_mid_50k

    # For high-income student, 50k fee remains AFFORDABLE_FOR_INCOME_BAND
    feats_high_50k = extract_features(student_high, occupation, course_50k, riasec, aptitude, net_cost_ratio=0.0)
    reasons_high_50k = generate_reason_codes(student_high, occupation, course_50k, feats_high_50k, riasec, lang="en")
    codes_high_50k = [r["code"] for r in reasons_high_50k]
    assert "AFFORDABLE_FOR_INCOME_BAND" in codes_high_50k


def test_scheme_benefit_makes_course_affordable_for_low_income() -> None:
    """Government scheme waiver reduces net fee and turns high-fee into affordable."""
    occupation = DummyOccupation()
    riasec = {"R": 0.85, "I": 0.65, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.5}
    aptitude = {"num": 0.7, "verbal": 0.6, "spatial": 0.8, "mech": 0.85}
    course_20k = DummyCourse(fee_inr=20000.0)

    # Low income student with 100% PMKVY/CTS waiver -> net fee = 0
    student_low = DummyStudent(income_band="lt_1l", budget_band="low")
    feats_subsidized = extract_features(
        student_low, occupation, course_20k, riasec, aptitude, net_cost_ratio=0.0
    )
    reasons_sub = generate_reason_codes(student_low, occupation, course_20k, feats_subsidized, riasec, lang="en")
    codes_sub = [r["code"] for r in reasons_sub]

    assert "AFFORDABLE_FOR_INCOME_BAND" in codes_sub
    aff_reason = next(r for r in reasons_sub if r["code"] == "AFFORDABLE_FOR_INCOME_BAND")
    assert aff_reason["evidence"]["net_fee"] == 0
    assert aff_reason["evidence"]["subsidy_pct"] == 100


# =========================================================================
# 2. Conversational Fact Ordering & Selection Differentiation
# =========================================================================


def test_conversational_reply_income_objection_ordering() -> None:
    """Income objection reply orders facts differently across income bands.

    - low income: leads with scheme/stipend/waiver facts before earnings facts;
    - high income: leads with progression/NSQF level-up/private-sector placement facts.
    """
    facts = [
        {"key": "median_salary", "value": 18500},
        {"key": "p25_salary", "value": 15000},
        {"key": "p75_salary", "value": 26000},
        {"key": "placement_rate", "value": 78.5},
        {"key": "n", "value": 150},
        {"key": "provider", "value": "Government Industrial Training Institute"},
        {"key": "district", "value": "Pune"},
        {"key": "state", "value": "Maharashtra"},
        {"key": "scheme_name", "value": "PMKVY 4.0"},
        {"key": "fee", "value": 4500},
        {"key": "source", "value": "DGT Outcome Registry"},
        {"key": "source_year", "value": 2026},
    ]

    # 1. Low income reply
    low_res = generate_response(topic="income", lang="en", facts=facts, income_band="low")
    low_reply = low_res["reply"]
    low_followups = low_res["followups"]

    # Low income reply must lead with scheme/waiver/stipend before median salary
    assert "waiver" in low_reply.lower() or "stipend" in low_reply.lower() or "scheme" in low_reply.lower()
    first_sentence_low = re.split(r"\.\s+", low_reply)[0].lower()
    assert ("waiver" in first_sentence_low or "stipend" in first_sentence_low or "free" in first_sentence_low)
    assert low_res["rule_branch"] == "income_low"
    assert low_res["income_band"] == "low"

    # 2. High income reply
    high_res = generate_response(topic="income", lang="en", facts=facts, income_band="high")
    high_reply = high_res["reply"]
    high_followups = high_res["followups"]

    # High income reply must lead with progression/NSQF/supervisory/private sector
    assert ("progression" in high_reply.lower() or "nsqf" in high_reply.lower() or "supervisory" in high_reply.lower() or "private" in high_reply.lower())
    first_sentence_high = re.split(r"\.\s+", high_reply)[0].lower()
    assert ("progression" in first_sentence_high or "nsqf" in first_sentence_high or "supervisory" in first_sentence_high or "private" in first_sentence_high)
    assert high_res["rule_branch"] == "income_high"
    assert high_res["income_band"] == "high"

    # 3. Medium income reply
    mid_res = generate_response(topic="income", lang="en", facts=facts, income_band="mid")
    mid_reply = mid_res["reply"]

    # All three must be distinct deterministic replies
    assert low_reply != high_reply
    assert low_reply != mid_reply
    assert high_reply != mid_reply

    # Followups should also reflect the branch
    assert any("waiver" in f.lower() or "stipend" in f.lower() for f in low_followups)
    assert any("private" in f.lower() or "supervisory" in f.lower() or "corporate" in f.lower() for f in high_followups)


def test_conversational_reply_cost_objection_ordering() -> None:
    """Cost objection reply branches deterministically on income band."""
    facts = [
        {"key": "fee", "value": 12000},
        {"key": "scheme_name", "value": "Craftsmen Training Scheme"},
        {"key": "provider", "value": "Model ITI Hub"},
        {"key": "placement_rate", "value": 82.0},
        {"key": "source", "value": "MSDE Tracer Studies"},
    ]

    low_res = generate_response(topic="cost", lang="en", facts=facts, income_band="low")
    high_res = generate_response(topic="cost", lang="en", facts=facts, income_band="high")
    mid_res = generate_response(topic="cost", lang="en", facts=facts, income_band="mid")

    # Low income emphasizes full fee waivers and zero upfront tuition
    assert "waiver" in low_res["reply"].lower() or "stipend" in low_res["reply"].lower() or "₹0" in low_res["reply"]
    assert low_res["rule_branch"] == "cost_low"

    # High income emphasizes return on investment, private industry roles, supervisory tiers
    assert "investment" in high_res["reply"].lower() or "supervisory" in high_res["reply"].lower() or "private" in high_res["reply"].lower()
    assert high_res["rule_branch"] == "cost_high"

    assert low_res["reply"] != high_res["reply"]
    assert low_res["reply"] != mid_res["reply"]


# =========================================================================
# 3. Bilingual Parity (Hindi & English)
# =========================================================================


@pytest.mark.parametrize("topic", ["income", "cost"])
@pytest.mark.parametrize("band", ["low", "mid", "high"])
def test_conversational_reply_hindi_parity(topic: str, band: str) -> None:
    """Hindi conversation templates interpolate clean without unrendered tokens."""
    facts = [
        {"key": "median_salary", "value": 19000},
        {"key": "p25_salary", "value": 15500},
        {"key": "p75_salary", "value": 25000},
        {"key": "placement_rate", "value": 75.0},
        {"key": "n", "value": 110},
        {"key": "provider", "value": "शासकीय औद्योगिक प्रशिक्षण संस्था"},
        {"key": "district", "value": "पुणे"},
        {"key": "state", "value": "महाराष्ट्र"},
        {"key": "scheme_name", "value": "पीएमकेवीवाई 4.0"},
        {"key": "fee", "value": 4500},
        {"key": "source", "value": "कौशल विकास एवं उद्यमशीलता मंत्रालय"},
        {"key": "source_year", "value": 2026},
        {"key": "income_band", "value": band},
    ]

    res = generate_response(topic=topic, lang="hi", facts=facts, income_band=band)
    reply = res["reply"]

    # Verify no un-substituted curly brace tokens remain
    assert "{" not in reply and "}" not in reply, f"Uninterpolated placeholder found in Hindi reply: {reply}"
    assert len(reply) > 20
    assert len(res["followups"]) >= 2


# =========================================================================
# 4. Transparent Rule-Based Branch Logging
# =========================================================================


def test_rule_based_branch_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Verify selection is a logged, rule-based branch per non-negotiable #4."""
    facts = [{"key": "provider", "value": "ITI Centre"}]

    with caplog.at_level(logging.INFO):
        generate_response(topic="income", lang="en", facts=facts, income_band="low")

    found_log = any(
        "Rule-based conversation branch applied: topic=income, income_band=low" in record.message
        for record in caplog.records
    )
    assert found_log, f"Expected rule-based branch log message, captured: {[r.message for r in caplog.records]}"


# =========================================================================
# 5. Features Extraction Affordability Signal
# =========================================================================


def test_features_affordability_signal() -> None:
    """extract_features includes net_fee, income_band, and affordability_code."""
    student = DummyStudent(income_band="low", budget_band="low")
    course = DummyCourse(fee_inr=15000.0)
    occ = DummyOccupation()
    riasec = {"R": 0.8, "I": 0.5, "A": 0.3, "S": 0.4, "E": 0.5, "C": 0.6}
    apt = {"num": 0.7, "verbal": 0.7, "spatial": 0.7, "mech": 0.7}

    feats = extract_features(student, occ, course, riasec, apt)

    assert "income_band" in feats
    assert feats["income_band"] == "low"
    assert "net_fee" in feats
    assert "affordability_code" in feats
    assert feats["has_data"]["affordability"] is True
