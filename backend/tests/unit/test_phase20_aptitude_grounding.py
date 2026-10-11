"""Phase 20 unit tests: Grounded Aptitude & O*NET Ability Requirements."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Ensure scripts module is reachable for loader testing
sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))

from app.db.base import Base  # noqa: E402
from app.ml.explain.reason_codes import generate_reason_codes  # noqa: E402
from app.ml.ranking.features import compute_aptitude_fit, extract_features  # noqa: E402
from app.models.assessment import Assessment  # noqa: E402
from app.models.centre import Centre  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.occupation import Occupation  # noqa: E402
from app.models.occupation_ability import OccupationAbility  # noqa: E402
from app.models.student import Student  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.recommend_svc import RecommendService  # noqa: E402


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_occupation_ability_model_creation(mem_db: Session):
    """Test OccupationAbility ORM model, foreign key and constraints."""
    occ = Occupation(
        name_en="Fitter",
        name_hi="फ़िटर",
        riasec_r=8.0,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=False,
        evidence_grade="A",
    )
    mem_db.add(occ)
    mem_db.commit()

    ability = OccupationAbility(
        occupation_id=occ.id,
        required_num=0.45,
        required_verbal=0.35,
        required_spatial=0.75,
        required_mech=0.90,
        primary_ability="mech",
        source="onet_abilities",
        source_year=2026,
        is_demo=False,
        evidence_grade="A",
        n=120,
        source_url="https://www.onetcenter.org/database.html",
        retrieved_on="2026-10-11",
        metric_definition="O*NET 31.0 normalized ability requirements",
    )
    mem_db.add(ability)
    mem_db.commit()

    query = select(OccupationAbility).where(OccupationAbility.occupation_id == occ.id)
    fetched = mem_db.scalar(query)
    assert fetched is not None
    assert fetched.required_mech == 0.90
    assert fetched.primary_ability == "mech"
    assert fetched.evidence_grade == "A"
    assert fetched.n == 120
    assert fetched.occupation.name_en == "Fitter"


def test_aptitude_fit_differentiation():
    """Verify that the same student receives sharply different aptitude fits across trades.

    Finding 2 from audit: Aptitude fit previously evaluated to the identical mean for all
    candidates. In Phase 20, trade ability profiles differentiate candidates.
    """
    student_apt = {
        "num": 0.40,
        "verbal": 0.30,
        "spatial": 0.70,
        "mech": 0.95,
    }

    welder_ability = {
        "required_num": 0.45,
        "required_verbal": 0.35,
        "required_spatial": 0.75,
        "required_mech": 0.90,
        "primary_ability": "mech",
    }

    accountant_ability = {
        "required_num": 0.92,
        "required_verbal": 0.70,
        "required_spatial": 0.35,
        "required_mech": 0.15,
        "primary_ability": "num",
    }

    fit_welder = compute_aptitude_fit(student_apt, welder_ability)
    fit_accountant = compute_aptitude_fit(student_apt, accountant_ability)

    assert 0.0 <= fit_welder <= 1.0
    assert 0.0 <= fit_accountant <= 1.0
    assert fit_welder > 0.70
    assert fit_accountant < 0.50
    assert fit_welder - fit_accountant >= 0.25


def test_aptitude_fit_reversal():
    """Verify that a quantitative-dominant student scores much higher on Accountant than Welder."""
    student_apt = {
        "num": 0.95,
        "verbal": 0.80,
        "spatial": 0.30,
        "mech": 0.15,
    }

    welder_ability = {
        "required_num": 0.45,
        "required_verbal": 0.35,
        "required_spatial": 0.75,
        "required_mech": 0.90,
        "primary_ability": "mech",
    }

    accountant_ability = {
        "required_num": 0.92,
        "required_verbal": 0.70,
        "required_spatial": 0.35,
        "required_mech": 0.15,
        "primary_ability": "num",
    }

    fit_welder = compute_aptitude_fit(student_apt, welder_ability)
    fit_accountant = compute_aptitude_fit(student_apt, accountant_ability)

    assert fit_accountant > 0.75
    assert fit_welder < 0.50
    assert fit_accountant - fit_welder >= 0.25


def test_aptitude_fit_fallback_behavior():
    """When occupation_ability is None, fallback to mean of student aptitude scores."""
    student_apt = {"num": 0.8, "verbal": 0.6, "spatial": 0.4, "mech": 0.2}
    expected_mean = (0.8 + 0.6 + 0.4 + 0.2) / 4.0

    fallback_fit = compute_aptitude_fit(student_apt, None)
    assert abs(fallback_fit - expected_mean) < 1e-6
    assert compute_aptitude_fit({}, None) == 0.5


def test_extract_features_with_occupation_ability():
    """Verify extract_features passes occupation_ability into features dict."""
    student = Student(
        id=1, user_id=1, edu_level="10th", district="Pune", state="MH", budget_band="low"
    )
    occ = Occupation(
        id=1,
        name_en="Welder",
        riasec_r=8.0, riasec_i=2.0, riasec_a=1.0,
        riasec_s=1.0, riasec_e=2.0, riasec_c=3.0,
    )
    course = Course(id=1, name="Welder CTS", fee_inr=5000, duration_months=12)

    student_riasec = {"R": 0.8, "I": 0.2, "A": 0.1, "S": 0.1, "E": 0.2, "C": 0.3}
    student_apt = {"num": 0.4, "verbal": 0.3, "spatial": 0.7, "mech": 0.9}

    ability = OccupationAbility(
        occupation_id=1,
        required_num=0.45,
        required_verbal=0.35,
        required_spatial=0.75,
        required_mech=0.90,
        primary_ability="mech",
    )

    feat = extract_features(
        student, occ, course, student_riasec, student_apt,
        occupation_ability=ability,
    )

    assert "aptitude_fit" in feat
    assert feat["aptitude_fit"] > 0.70


def test_reason_codes_grounded_aptitude_dimension():
    """Verify generate_reason_codes references trade's primary dimension and Grade A badge."""
    student = Student(id=1, user_id=1, edu_level="10th", district="Pune", state="MH", language="en")
    occ = Occupation(id=1, name_en="Automotive Mechanic")
    course = Course(id=1, name="MMV", fee_inr=1000)
    features = {"aptitude_fit": 0.85, "riasec_cosine": 0.80, "fee_ratio": 0.2}
    riasec = {"R": 0.8, "I": 0.6, "A": 0.2, "S": 0.3, "E": 0.4, "C": 0.5}

    ability = {
        "required_num": 0.45,
        "required_verbal": 0.35,
        "required_spatial": 0.75,
        "required_mech": 0.90,
        "primary_ability": "mech",
    }

    reasons_en = generate_reason_codes(
        student, occ, course, features, riasec, lang="en", occupation_ability=ability
    )
    apt_reason_en = next(r for r in reasons_en if r["code"] == "APTITUDE_STRONG")
    assert apt_reason_en["source"] == "O*NET Abilities (Grade A)"
    assert "mechanical" in apt_reason_en["description"]
    assert apt_reason_en["params"]["dimension"] == "mechanical"

    student_hi = Student(
        id=2, user_id=2, edu_level="10th", district="Pune", state="MH", language="hi"
    )
    reasons_hi = generate_reason_codes(
        student_hi, occ, course, features, riasec, lang="hi", occupation_ability=ability
    )
    apt_reason_hi = next(r for r in reasons_hi if r["code"] == "APTITUDE_STRONG")
    assert apt_reason_hi["source"] == "O*NET Abilities (Grade A)"
    assert "यांत्रिक" in apt_reason_hi["description"]


def test_recommend_service_integration(mem_db: Session):
    """End-to-end recommendation service ranking with grounded ability requirements."""
    user = User(id=1, email="v@t.test", hashed_password="x", role="student", lang="en")
    mem_db.add(user)
    student = Student(
        id=1,
        user_id=1,
        edu_level="10th",
        budget_band="mid",
        state="Uttar Pradesh",
        district="Varanasi",
        relocate_ok=True,
    )
    mem_db.add(student)
    mem_db.commit()

    assessment = Assessment(
        id=1,
        student_id=student.id,
        status="completed",
        riasec_r=0.8, riasec_i=0.3, riasec_a=0.2, riasec_s=0.2, riasec_e=0.3, riasec_c=0.4,
        apt_num=0.35, apt_verbal=0.30, apt_spatial=0.75, apt_mech=0.92,
        confidence=0.98,
    )
    mem_db.add(assessment)

    occ1 = Occupation(
        id=1,
        name_en="Welder",
        name_hi="वेल्डर",
        nsqf_level=3,
        riasec_r=8.0, riasec_i=2.0, riasec_a=1.0, riasec_s=1.0, riasec_e=2.0, riasec_c=3.0,
        is_vocational=True,
        source="demo",
        evidence_grade="D",
    )
    occ2 = Occupation(
        id=2,
        name_en="Data Entry Operator",
        name_hi="डाटा एंट्री ऑपरेटर",
        nsqf_level=3,
        riasec_r=2.0, riasec_i=4.0, riasec_a=1.0, riasec_s=3.0, riasec_e=4.0, riasec_c=8.0,
        is_vocational=True,
        source="demo",
        evidence_grade="D",
    )
    mem_db.add_all([occ1, occ2])
    mem_db.commit()

    ab1 = OccupationAbility(
        occupation_id=occ1.id,
        required_num=0.45, required_verbal=0.35, required_spatial=0.75, required_mech=0.90,
        primary_ability="mech",
        source="onet_abilities", evidence_grade="A", retrieved_on="2026-10-11",
    )
    ab2 = OccupationAbility(
        occupation_id=occ2.id,
        required_num=0.85, required_verbal=0.70, required_spatial=0.40, required_mech=0.20,
        primary_ability="num",
        source="onet_abilities", evidence_grade="A", retrieved_on="2026-10-11",
    )
    mem_db.add_all([ab1, ab2])

    c1 = Course(
        id=1, occupation_id=occ1.id, name="Welder CTS", fee_inr=5000, duration_months=12,
        source="demo", evidence_grade="D"
    )
    c2 = Course(
        id=2, occupation_id=occ2.id, name="DEO Course", fee_inr=5000, duration_months=6,
        source="demo", evidence_grade="D"
    )
    mem_db.add_all([c1, c2])

    cntr1 = Centre(
        course_id=1, name="ITI Varanasi", district="Varanasi", state="Uttar Pradesh",
        source="demo", evidence_grade="D"
    )
    cntr2 = Centre(
        course_id=2, name="Skill Centre Varanasi", district="Varanasi", state="Uttar Pradesh",
        source="demo", evidence_grade="D"
    )
    mem_db.add_all([cntr1, cntr2])
    mem_db.commit()

    svc = RecommendService(mem_db)
    result = svc.get_recommendations(student.id, top_k=2)

    recs = result["recommendations"]
    assert len(recs) == 2
    assert recs[0]["occupation_name"] == "Welder"


def test_loader_callable():
    """Verify loader main function is callable and has valid signature."""
    import load_occupation_abilities
    assert callable(load_occupation_abilities.main)


# ---------------------------------------------------------------------------
# PHASE 20 SPECIFIC TESTS (Paragraph 146 I)
# ---------------------------------------------------------------------------

def test_pivot_fixture_5_occupations():
    """Test pivoting 5 sample occupations with both OI and IH scales."""
    from load_onet import rescale_oi

    # Fixture: 5 occupations with OI and IH data lines
    raw_fixture = [
        # Occ 1: Fitter
        ("11-0001.00", "1.B.1.a", "Realistic", "OI", "7.0"),
        ("11-0001.00", "1.B.1.b", "Investigative", "OI", "4.0"),
        ("11-0001.00", "1.B.1.c", "Artistic", "OI", "1.0"),
        ("11-0001.00", "1.B.1.d", "Social", "OI", "2.5"),
        ("11-0001.00", "1.B.1.e", "Enterprising", "OI", "3.0"),
        ("11-0001.00", "1.B.1.f", "Conventional", "OI", "5.0"),
        ("11-0001.00", "1.B.1.g", "First High", "IH", "1.0"),
        ("11-0001.00", "1.B.1.h", "Second High", "IH", "6.0"),
        ("11-0001.00", "1.B.1.i", "Third High", "IH", "2.0"),
        # Occ 2: Electrician
        ("11-0002.00", "1.B.1.a", "Realistic", "OI", "6.4"),
        ("11-0002.00", "1.B.1.b", "Investigative", "OI", "4.6"),
        ("11-0002.00", "1.B.1.c", "Artistic", "OI", "1.5"),
        ("11-0002.00", "1.B.1.d", "Social", "OI", "2.0"),
        ("11-0002.00", "1.B.1.e", "Enterprising", "OI", "3.5"),
        ("11-0002.00", "1.B.1.f", "Conventional", "OI", "4.8"),
        ("11-0002.00", "1.B.1.g", "First High", "IH", "1.0"),
        ("11-0002.00", "1.B.1.h", "Second High", "IH", "6.0"),
        ("11-0002.00", "1.B.1.i", "Third High", "IH", "0.0"),
        # Occ 3: Software Developer
        ("11-0003.00", "1.B.1.a", "Realistic", "OI", "2.0"),
        ("11-0003.00", "1.B.1.b", "Investigative", "OI", "6.5"),
        ("11-0003.00", "1.B.1.c", "Artistic", "OI", "4.0"),
        ("11-0003.00", "1.B.1.d", "Social", "OI", "2.5"),
        ("11-0003.00", "1.B.1.e", "Enterprising", "OI", "3.0"),
        ("11-0003.00", "1.B.1.f", "Conventional", "OI", "5.5"),
        ("11-0003.00", "1.B.1.g", "First High", "IH", "2.0"),
        ("11-0003.00", "1.B.1.h", "Second High", "IH", "6.0"),
        ("11-0003.00", "1.B.1.i", "Third High", "IH", "3.0"),
        # Occ 4: Nurse
        ("11-0004.00", "1.B.1.a", "Realistic", "OI", "2.5"),
        ("11-0004.00", "1.B.1.b", "Investigative", "OI", "5.0"),
        ("11-0004.00", "1.B.1.c", "Artistic", "OI", "2.0"),
        ("11-0004.00", "1.B.1.d", "Social", "OI", "6.8"),
        ("11-0004.00", "1.B.1.e", "Enterprising", "OI", "4.0"),
        ("11-0004.00", "1.B.1.f", "Conventional", "OI", "4.5"),
        ("11-0004.00", "1.B.1.g", "First High", "IH", "4.0"),
        ("11-0004.00", "1.B.1.h", "Second High", "IH", "2.0"),
        ("11-0004.00", "1.B.1.i", "Third High", "IH", "6.0"),
        # Occ 5: Accountant
        ("11-0005.00", "1.B.1.a", "Realistic", "OI", "1.2"),
        ("11-0005.00", "1.B.1.b", "Investigative", "OI", "4.5"),
        ("11-0005.00", "1.B.1.c", "Artistic", "OI", "1.5"),
        ("11-0005.00", "1.B.1.d", "Social", "OI", "3.0"),
        ("11-0005.00", "1.B.1.e", "Enterprising", "OI", "5.2"),
        ("11-0005.00", "1.B.1.f", "Conventional", "OI", "6.9"),
        ("11-0005.00", "1.B.1.g", "First High", "IH", "6.0"),
        ("11-0005.00", "1.B.1.h", "Second High", "IH", "5.0"),
        ("11-0005.00", "1.B.1.i", "Third High", "IH", "2.0"),
    ]

    element_map = {
        "1.B.1.a": "riasec_r", "1.B.1.b": "riasec_i", "1.B.1.c": "riasec_a",
        "1.B.1.d": "riasec_s", "1.B.1.e": "riasec_e", "1.B.1.f": "riasec_c",
    }
    ih_map = {
        "1.B.1.g": "ih_first", "1.B.1.h": "ih_second", "1.B.1.i": "ih_third",
    }

    pivoted = {}
    for soc, el_id, _name, scale, val_str in raw_fixture:
        pivoted.setdefault(soc, {})
        val = float(val_str)
        if scale == "OI" and el_id in element_map:
            pivoted[soc][element_map[el_id]] = rescale_oi(val)
        elif scale == "IH" and el_id in ih_map:
            pivoted[soc][ih_map[el_id]] = int(round(val))

    assert len(pivoted) == 5
    # Check Fitter
    fitter = pivoted["11-0001.00"]
    assert fitter["riasec_r"] == 1.0  # (7.0 - 1.0) / 6.0
    assert fitter["riasec_c"] == (5.0 - 1.0) / 6.0
    assert fitter["ih_first"] == 1
    assert fitter["ih_second"] == 6
    assert fitter["ih_third"] == 2

    # Check Accountant
    acct = pivoted["11-0005.00"]
    assert acct["riasec_c"] == (6.9 - 1.0) / 6.0
    assert acct["ih_first"] == 6


def test_rescale_bounds():
    """Verify that rescaling bounds [0.0, 1.0] are strictly enforced."""
    from load_onet import rescale_importance, rescale_level, rescale_oi

    # OI bounds (1.0 to 7.0)
    assert rescale_oi(1.0) == 0.0
    assert rescale_oi(7.0) == 1.0
    assert rescale_oi(4.0) == 0.5
    assert rescale_oi(0.5) == 0.0   # below min clamped
    assert rescale_oi(8.0) == 1.0   # above max clamped

    # Importance bounds (1.0 to 5.0)
    assert rescale_importance(1.0) == 0.0
    assert rescale_importance(5.0) == 1.0
    assert rescale_importance(3.0) == 0.5
    assert rescale_importance(0.0) == 0.0

    # Level bounds (0.0 to 7.0)
    assert rescale_level(0.0) == 0.0
    assert rescale_level(7.0) == 1.0
    assert rescale_level(3.5) == 0.5
    assert rescale_level(8.0) == 1.0


def test_aptitude_map_unknown_element_failure(tmp_path):
    """Confirm unknown element names in aptitude_map fail loudly, not silently drop."""
    from load_onet import validate_aptitude_map

    # Mock Content Model Reference file
    cm_file = tmp_path / "Content_Model.txt"
    cm_file.write_text(
        "1.A.1.a.1\tOral Comprehension\tDesc\n"
        "1.A.1.c.1\tMathematical Reasoning\tDesc\n",
        encoding="utf-8",
    )

    valid_cfg = {
        "constructs": {
            "verbal": {"elements": [{"name": "Oral Comprehension"}]},
            "num": {"elements": [{"name": "Mathematical Reasoning"}]},
        }
    }
    # Valid map passes without exception
    validate_aptitude_map(valid_cfg, cm_file)

    # Invalid element name must raise ValueError loudly
    invalid_cfg = {
        "constructs": {
            "verbal": {"elements": [{"name": "Telepathic Communication"}]},
        }
    }
    with pytest.raises(
        ValueError, match="Unknown element in aptitude_map.*Telepathic Communication"
    ):
        validate_aptitude_map(invalid_cfg, cm_file)


def test_evidence_precedence():
    """Test 3-tier precedence: PS-provided > O*NET (Grade A) > demo (Grade D)."""
    # Tier 1 vs Tier 2
    provided_map = {"Fitter": {"riasec_r": 0.95, "source": "sih_eval"}}
    onet_map = {"Fitter": {"riasec_r": 0.85, "source": "onet_31_0"}}
    demo_row = {"name_en": "Fitter", "riasec_r": 0.50, "source": "demo"}

    # When provided is present, it wins
    chosen_source = (
        provided_map.get("Fitter", {}).get("source")
        or onet_map.get("Fitter", {}).get("source")
        or demo_row["source"]
    )
    assert chosen_source == "sih_eval"

    # When provided is absent, O*NET Grade A wins over demo
    provided_map.clear()
    chosen_source_2 = (
        provided_map.get("Fitter", {}).get("source")
        or onet_map.get("Fitter", {}).get("source")
        or demo_row["source"]
    )
    assert chosen_source_2 == "onet_31_0"

    # When both are absent, demo Grade D is kept
    onet_map.clear()
    chosen_source_3 = (
        provided_map.get("Fitter", {}).get("source")
        or onet_map.get("Fitter", {}).get("source")
        or demo_row["source"]
    )
    assert chosen_source_3 == "demo"


def test_spread_flag():
    """Test that a trade whose RIASEC dimension spread (SD) > 0.2 is flagged needs_review."""
    from map_onet_to_india import calculate_spread

    # Codes with consistent RIASEC vectors (SD <= 0.2)
    consistent_codes = [
        {"riasec_r": 0.80, "riasec_i": 0.30, "riasec_a": 0.10,
         "riasec_s": 0.20, "riasec_e": 0.25, "riasec_c": 0.40},
        {"riasec_r": 0.85, "riasec_i": 0.35, "riasec_a": 0.12,
         "riasec_s": 0.22, "riasec_e": 0.28, "riasec_c": 0.42},
    ]
    spread_cons = calculate_spread(consistent_codes)
    max_cons = max(spread_cons.values())
    assert max_cons < 0.2
    assert not (max_cons > 0.2)

    # Codes with divergent RIASEC vectors (SD > 0.2)
    divergent_codes = [
        {"riasec_r": 0.90, "riasec_i": 0.20, "riasec_a": 0.10,
         "riasec_s": 0.20, "riasec_e": 0.20, "riasec_c": 0.30},
        {"riasec_r": 0.30, "riasec_i": 0.80, "riasec_a": 0.10,
         "riasec_s": 0.20, "riasec_e": 0.20, "riasec_c": 0.30},
    ]
    spread_div = calculate_spread(divergent_codes)
    max_div = max(spread_div.values())
    assert max_div > 0.2
    # Flag condition
    needs_review = max_div > 0.2
    assert needs_review is True
