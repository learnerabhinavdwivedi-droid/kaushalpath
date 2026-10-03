"""Phase 3: recommendation pipeline integration (filter -> rank -> explain -> persist).

Seeds a tiny in-memory dataset + a completed assessment and asserts the service
returns top-3 with >=2 reasons each and PERSISTS rows (the historical crash was
`Recommendation(course_id=...)` on a column that didn't exist / occupation_id not
set). Also exercises POST /recommend through the ASGI app.
"""
from __future__ import annotations

import pytest

from app.models import (
    Assessment,
    Centre,
    Course,
    Market,
    Occupation,
    Recommendation,
    Student,
    User,
)
from app.services.recommend_svc import RecommendService

SOURCE = {"source": "test", "is_demo": True}


@pytest.fixture()
def session(db_session):
    _seed(db_session)
    yield db_session


def _seed(s) -> None:
    s.add(User(id=1, email="s@t.test", hashed_password="x", role="student", lang="en"))
    s.add(Student(
        id=1, user_id=1, age=18, edu_level="10th", district="Pune", state="MH",
        budget_band="high", relocate_ok=True, language="en", max_duration_months=24,
    ))
    # A realistic profile that strongly matches the "Electrician" occupation (R/I).
    s.add(Assessment(
        id=1, student_id=1, status="completed", items_answered=20, confidence=0.96,
        riasec_r=0.95, riasec_i=0.85, riasec_a=0.3, riasec_s=0.4, riasec_e=0.2, riasec_c=0.5,
        apt_num=0.8, apt_verbal=0.5, apt_spatial=0.9, apt_mech=0.85,
    ))
    s.add_all([
        Occupation(
            id=1, name_en="Electrician", nsqf_level=5, description="Wiring and repair",
            riasec_r=9, riasec_i=7, riasec_a=2, riasec_s=3, riasec_e=2, riasec_c=4, **SOURCE,
        ),
        Occupation(
            id=2, name_en="Fashion Designer", nsqf_level=4, description="Apparel design",
            riasec_r=2, riasec_i=3, riasec_a=9, riasec_s=3, riasec_e=4, riasec_c=2, **SOURCE,
        ),
    ])
    s.add_all([
        Course(id=1, occupation_id=1, name="ITI Electrician", nsqf_level=5,
               duration_months=12, min_edu="10th", fee_inr=20000, **SOURCE),
        Course(id=2, occupation_id=2, name="Fashion Diploma", nsqf_level=4,
               duration_months=18, min_edu="12th", fee_inr=40000, **SOURCE),
    ])
    s.add_all([
        Centre(id=1, course_id=1, name="Pune ITI", district="Pune", state="MH", **SOURCE),
        Centre(id=2, course_id=2, name="Mumbai Design", district="Mumbai", state="MH", **SOURCE),
    ])
    s.add_all([
        Market(id=1, occupation_id=1, state="MH", avg_salary_inr=300000, demand_index=80, **SOURCE),
        Market(id=2, occupation_id=2, state="MH", avg_salary_inr=250000, demand_index=40, **SOURCE),
    ])
    s.commit()


def test_service_returns_reasoned_ranking_and_persists(session):
    from sqlalchemy import select

    result = RecommendService(session).get_recommendations(student_id=1, top_k=3)

    recs = result["recommendations"]
    assert len(recs) >= 1
    # Electrician (R/I) should outrank Fashion (A) for this profile.
    assert recs[0]["occupation_name"] == "Electrician"
    for r in recs:
        assert len(r["reasons"]) >= 2, "each recommendation needs >=2 reason codes"
        assert all(rsn.get("description") for rsn in r["reasons"]), "reasons must carry text"

    persisted = session.scalars(select(Recommendation).where(Recommendation.student_id == 1)).all()
    assert persisted, "recommendations must be stored"
    top = [p for p in persisted if p.rank == 1][0]
    assert top.occupation_id == 1
    assert top.course_id == 1
    assert top.model_version


def test_rejected_are_reported_not_silently_dropped(session):
    # A student who cannot relocate and has 10th edu: Fashion (12th min, Mumbai) rejected.
    student = session.get(Student, 1)
    student.relocate_ok = False
    session.commit()
    result = RecommendService(session).get_recommendations(student_id=1, top_k=3)
    rejected_names = {r["course"] for r in result["rejected"]}
    assert "Fashion Diploma" in rejected_names


def test_recommend_endpoint_ok(session, client_with_db):
    resp = client_with_db.post("/recommend", json={"student_id": 1, "top_k": 3})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recommendations"][0]["occupation_name"] == "Electrician"


def test_recommend_endpoint_404_unknown_student(client_with_db):
    resp = client_with_db.post("/recommend", json={"student_id": 999})
    assert resp.status_code == 404
