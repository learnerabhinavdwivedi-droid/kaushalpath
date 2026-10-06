"""Phase 11 integration tests: outcome data, provider facts, loader fixtures,
and vocational filter."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = BACKEND_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import load_provided_dataset  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models import (  # noqa: E402
    Centre,
    Course,
    Occupation,
    ProgressionPath,
    ProviderOutcome,
    Scheme,
)


def test_outcomes_api_shape_and_provenance(client_with_db, db_session: Session) -> None:
    # Set up test trade and outcomes
    occ = Occupation(
        name_en="Fitter",
        name_hi="फिटर",
        is_vocational=True,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db_session.add(occ)
    db_session.flush()

    course = Course(
        occupation_id=occ.id,
        name="ITI Fitter",
        nsqf_level=5,
        fee_inr=15000,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db_session.add(course)
    db_session.flush()

    centre = Centre(
        course_id=course.id,
        name="Government ITI Kanpur",
        district="Kanpur",
        state="Uttar Pradesh",
        provider_type="Government ITI",
        affiliation="NCVT",
        has_female_trainers=True,
        has_hostel=True,
        transport_note="Direct bus",
        safety_certified=True,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db_session.add(centre)
    db_session.flush()

    po = ProviderOutcome(
        provider_id=centre.id,
        course_id=course.id,
        cohort_year=2025,
        enrolled=50,
        certified=45,
        placed=40,
        placement_rate=88.9,
        earnings_p25=16000,
        earnings_median=19000,
        earnings_p75=23000,
        self_employed_pct=10.0,
        apprenticeship_stipend_inr=9500,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db_session.add(po)

    prog = ProgressionPath(
        from_course_id=course.id,
        to_label="Advanced Tooling Specialist",
        kind="nsqf_levelup",
        credit_note="Direct progression",
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db_session.add(prog)

    scheme = Scheme(
        name="PMKVY 4.0",
        benefit_text_en="Free skill training",
        benefit_text_hi="नि:शुल्क कौशल प्रशिक्षण",
        source="msde_official",
        source_year=2026,
        is_demo=True,
    )
    db_session.add(scheme)
    db_session.commit()

    resp = client_with_db.get(f"/outcomes?occupation_id={occ.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["occupation_id"] == occ.id
    assert data["occupation_name_en"] == "Fitter"
    assert data["is_vocational"] is True
    assert data["earnings_p25"] == 16000.0
    assert data["earnings_median"] == 19000.0
    assert data["earnings_p75"] == 23000.0
    assert data["placement_rate"] == 88.9
    assert data["n"] == 50
    assert data["source"] == "demo_synth_2026"
    assert data["is_demo"] is True
    assert len(data["progression_paths"]) == 1
    assert data["progression_paths"][0]["to_label"] == "Advanced Tooling Specialist"
    assert len(data["schemes"]) >= 1
    assert len(data["providers"]) == 1
    assert data["providers"][0]["has_female_trainers"] is True


def test_outcomes_api_404_on_missing_occupation(client_with_db) -> None:
    resp = client_with_db.get("/outcomes?occupation_id=999999")
    assert resp.status_code == 404


def test_provider_outcomes_endpoint(client_with_db, db_session: Session) -> None:
    occ = Occupation(name_en="Electrician", is_vocational=True, source="demo", is_demo=True)
    db_session.add(occ)
    db_session.flush()

    course = Course(occupation_id=occ.id, name="ITI Electrician", source="demo", is_demo=True)
    db_session.add(course)
    db_session.flush()

    centre = Centre(
        course_id=course.id,
        name="NSTI Mumbai",
        district="Mumbai",
        state="Maharashtra",
        provider_type="NSTI",
        has_female_trainers=True,
        has_hostel=False,
        transport_note="Local train station 500m",
        safety_certified=True,
        source="demo",
        is_demo=True,
    )
    db_session.add(centre)
    db_session.flush()

    po = ProviderOutcome(
        provider_id=centre.id,
        course_id=course.id,
        cohort_year=2025,
        enrolled=40,
        placed=35,
        placement_rate=87.5,
        earnings_median=21000,
        source="demo",
        is_demo=True,
    )
    db_session.add(po)
    db_session.commit()

    resp = client_with_db.get(f"/providers/{centre.id}/outcomes")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == centre.id
    assert data["name"] == "NSTI Mumbai"
    assert data["has_female_trainers"] is True
    assert data["has_hostel"] is False
    assert data["safety_certified"] is True
    assert len(data["cohort_outcomes"]) == 1
    assert data["cohort_outcomes"][0]["placement_rate"] == 87.5
    assert data["cohort_outcomes"][0]["earnings_median"] == 21000.0


def test_vocational_filter_in_recommender(db_session: Session) -> None:
    from app.models import Assessment, Student, User
    from app.services.recommend_svc import RecommendService

    # Create vocational & non-vocational occupations
    voc_occ = Occupation(
        name_en="Welder", is_vocational=True, riasec_r=8.0, source="demo", is_demo=True
    )
    non_voc_occ = Occupation(
        name_en="AI ML Engineer", is_vocational=False, riasec_r=8.0, source="demo", is_demo=True
    )
    db_session.add_all([voc_occ, non_voc_occ])
    db_session.flush()

    c1 = Course(
        occupation_id=voc_occ.id, name="ITI Welder", nsqf_level=4, min_edu="10th",
        fee_inr=15000, source="demo", is_demo=True,
    )
    c2 = Course(
        occupation_id=non_voc_occ.id, name="B.Tech AI", nsqf_level=7, min_edu="10th",
        fee_inr=15000, source="demo", is_demo=True,
    )
    db_session.add_all([c1, c2])
    db_session.flush()

    cnt1 = Centre(
        course_id=c1.id, name="Centre 1", district="Kanpur", state="Uttar Pradesh",
        source="demo", is_demo=True,
    )
    cnt2 = Centre(
        course_id=c2.id, name="Centre 2", district="Kanpur", state="Uttar Pradesh",
        source="demo", is_demo=True,
    )
    db_session.add_all([cnt1, cnt2])
    db_session.flush()

    u = User(email="teststudent@example.com", hashed_password="pw", role="student")
    db_session.add(u)
    db_session.flush()

    student = Student(
        user_id=u.id, edu_level="10th", state="Uttar Pradesh", district="Kanpur",
        budget_band="mid", relocate_ok=True,
    )
    db_session.add(student)
    db_session.flush()

    assessment = Assessment(
        student_id=student.id,
        riasec_r=7.0, riasec_i=3.0, riasec_a=2.0, riasec_s=2.0, riasec_e=2.0, riasec_c=3.0,
        apt_num=0.7, apt_verbal=0.6, apt_spatial=0.8, apt_mech=0.8,
        confidence=0.9,
        status="completed",
        state_json={},
    )
    db_session.add(assessment)
    db_session.commit()

    svc = RecommendService(db_session)
    res = svc.get_recommendations(student.id, top_k=5)

    recs = res["recommendations"]
    rec_occ_ids = {r["occupation_id"] for r in recs}
    assert non_voc_occ.id not in rec_occ_ids, "Non-vocational occupation must be excluded"
    assert voc_occ.id in rec_occ_ids, "Vocational occupation should be eligible"


def test_provenance_contract_on_all_phase11_tables(db_session: Session) -> None:
    """RULES: Every data row must carry source and is_demo."""
    # Seed a row in each
    occ = Occupation(name_en="Mason", is_vocational=True, source="demo", is_demo=True)
    db_session.add(occ)
    db_session.flush()

    course = Course(occupation_id=occ.id, name="ITI Mason", source="demo", is_demo=True)
    db_session.add(course)
    db_session.flush()

    centre = Centre(
        course_id=course.id, name="ITI Patna", district="Patna", state="Bihar",
        source="demo", is_demo=True,
    )
    db_session.add(centre)
    db_session.flush()

    po = ProviderOutcome(provider_id=centre.id, course_id=course.id, source="demo", is_demo=True)
    db_session.add(po)

    prog = ProgressionPath(
        from_course_id=course.id, to_label="Next Level", kind="nsqf_levelup",
        source="demo", is_demo=True,
    )
    db_session.add(prog)

    sch = Scheme(
        name="CTS", benefit_text_en="CTS", benefit_text_hi="CTS", source="demo", is_demo=True
    )
    db_session.add(sch)
    db_session.commit()

    for model in [ProviderOutcome, ProgressionPath, Scheme, Centre, Occupation]:
        bad_source = db_session.query(model).filter(
            (model.source.is_(None)) | (model.source == "")
        ).count()
        assert bad_source == 0, f"Table {model.__tablename__} contains rows missing source"

        bad_demo = db_session.query(model).filter(model.is_demo.is_(None)).count()
        assert bad_demo == 0, f"Table {model.__tablename__} contains rows missing is_demo"


def test_provided_loader_fixture_1_fuzzy_matching(tmp_path: Path, db_session: Session) -> None:
    """Fixture 1: CSV with variant headers without mapping.yaml
    (trade, state, avg_salary, placement)."""
    fixture_dir = tmp_path / "provided_fixture_1"
    fixture_dir.mkdir()
    csv_file = fixture_dir / "msde_eval_batch1.csv"

    fieldnames = ["trade", "state_name", "monthly_salary", "job_placement_rate", "batch_year"]
    rows = [
        {
            "trade": "Welder", "state_name": "Haryana", "monthly_salary": "₹22,500",
            "job_placement_rate": "82%", "batch_year": "2026",
        },
        {
            "trade": "Fitter", "state_name": "Punjab", "monthly_salary": "24k",
            "job_placement_rate": "86.5", "batch_year": "2026",
        },
    ]
    with csv_file.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    res = load_provided_dataset.main(get_session=lambda: db_session, base_dir=fixture_dir)
    assert res["loaded"] >= 2
    assert res["rejected"] == 0


def test_provided_loader_fixture_2_custom_mapping_yaml(tmp_path: Path, db_session: Session) -> None:
    """Fixture 2: CSV with arbitrary local headers parsed via custom mapping.yaml."""
    fixture_dir = tmp_path / "provided_fixture_2"
    fixture_dir.mkdir()

    # Create mapping.yaml
    mapping_file = fixture_dir / "mapping.yaml"
    mapping_content = """
name_en:
  - vyavsay_code
state:
  - pradesh_stithi
avg_salary_inr:
  - vetan_inr
placement_rate:
  - roji_roti_rate
"""
    mapping_file.write_text(mapping_content, encoding="utf-8")

    csv_file = fixture_dir / "custom_state_eval.csv"
    fieldnames = [
        "vyavsay_code", "pradesh_stithi", "vetan_inr", "roji_roti_rate", "unmapped_extra_info"
    ]
    rows = [
        {
            "vyavsay_code": "Electrician", "pradesh_stithi": "Odisha", "vetan_inr": "19500",
            "roji_roti_rate": "79.2", "unmapped_extra_info": "batch-A",
        },
    ]
    with csv_file.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    res = load_provided_dataset.main(get_session=lambda: db_session, base_dir=fixture_dir)
    assert res["loaded"] >= 1
    assert "unmapped_extra_info" in res["unmapped"]
