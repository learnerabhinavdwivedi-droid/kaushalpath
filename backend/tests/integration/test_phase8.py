"""Phase 8: counsellor dashboard, role permissions, small-group suppression,
feedback loop (+ retraining export) and the audit trail."""
from __future__ import annotations

import json

from app.models import (
    Assessment,
    AuditLog,
    CounsellorAssignment,
    Objection,
    Occupation,
    Recommendation,
    Room,
    Student,
)
from app.services.feedback_export_svc import build_samples, export_feedback

DIM = ["riasec_r", "riasec_i", "riasec_a", "riasec_s", "riasec_e", "riasec_c"]


def _register(client, email, role):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password", "role": role, "give_consent": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _set_district(db, student, district):
    row = db.get(Student, student)
    row.district = district
    db.commit()


def _seed_world(client, db, n_pune=5, n_nagpur=2):
    """Cohort of 5 Pune + 2 Nagpur students, each with a complete RIASEC-R
    assessment and a rank-1 recommendation of 'Electrician'.
    Tokens are returned in seed order: the first ``n_pune`` are Pune."""
    occ = Occupation(name_en="Electrician", source="test", is_demo=True, nsqf_level=3)
    db.add(occ)
    db.commit()
    db.refresh(occ)

    tokens = []
    for label, count, district in (("pune", n_pune, "Pune"), ("nag", n_nagpur, "Nagpur")):
        for i in range(count):
            token = _register(client, f"{label}{i}@t.com", "student")
            tokens.append(token)
            sid = client.get("/auth/me", headers=_auth(token)).json()["student_id"]
            _set_district(db, sid, district)
            riasec = {k: 1.0 for k in DIM}
            riasec["riasec_r"] = 9.0
            db.add(
                Assessment(
                    student_id=sid, status="complete", items_answered=12, confidence=0.8, **riasec
                )
            )
            db.add(
                Recommendation(
                    student_id=sid,
                    occupation_id=occ.id,
                    rank=1,
                    score=0.9,
                    reasons_json=[{"code": "TEST", "description": "x", "source": "test"}],
                    model_version="test-v1",
                )
            )
            db.commit()
    return occ, tokens


def _assign_all(client, db, counsellor_user_id):
    for student in db.query(Student).all():
        db.add(CounsellorAssignment(counsellor_id=counsellor_user_id, student_id=student.id))
    db.commit()


def test_non_counsellor_cannot_touch_dashboard(client_with_db, db_session):
    client = client_with_db
    student = _register(client, "plain-student@t.com", "student")
    for path in ("/counsellor/cohort", "/counsellor/analytics", "/counsellor/resistance",
                 "/counsellor/audit", "/counsellor/students/1"):
        resp = client.get(path, headers=_auth(student))
        assert resp.status_code == 403, f"{path} -> {resp.status_code}"


def test_counsellor_scoped_to_assigned_students(client_with_db, db_session):
    client = client_with_db
    _seed_world(client, db_session)
    counsellor = _register(client, "couns1@t.com", "counsellor")

    # Unassigned counsellor sees an empty cohort, not other people's students.
    assert client.get("/counsellor/cohort", headers=_auth(counsellor)).json() == []
    denied = client.get("/counsellor/students/1", headers=_auth(counsellor))
    assert denied.status_code == 403

    counsellor_uid = client.get("/auth/me", headers=_auth(counsellor)).json()["user_id"]
    first_student = db_session.query(Student).order_by(Student.id).first()
    db_session.add(CounsellorAssignment(counsellor_id=counsellor_uid, student_id=first_student.id))
    db_session.commit()

    cohort = client.get("/counsellor/cohort", headers=_auth(counsellor)).json()
    assert len(cohort) == 1
    assert cohort[0]["student_id"] == first_student.id
    detail = client.get(f"/counsellor/students/{first_student.id}", headers=_auth(counsellor))
    assert detail.status_code == 200


def test_cohort_filters(client_with_db, db_session):
    client = client_with_db
    _seed_world(client, db_session)
    admin = _register(client, "admin1@t.com", "admin")
    headers = _auth(admin)

    all_rows = client.get("/counsellor/cohort", headers=headers).json()
    assert len(all_rows) == 7
    pune = client.get("/counsellor/cohort?district=Pune", headers=headers).json()
    assert len(pune) == 5
    assessed = client.get("/counsellor/cohort?status=assessed", headers=headers).json()
    assert len(assessed) == 7
    none = client.get("/counsellor/cohort?district=Mumbai", headers=headers).json()
    assert none == []


def test_analytics_hides_small_groups(client_with_db, db_session):
    client = client_with_db
    _seed_world(client, db_session)
    admin = _register(client, "admin2@t.com", "admin")
    body = client.get("/counsellor/analytics", headers=_auth(admin)).json()

    # 7 students share the dominant type / top trade -> visible.
    assert body["riasec"]["distribution"] == [{"type": "Realistic", "count": 7}]
    assert body["top_trades"]["top_trades"] == [{"label": "Electrician", "count": 7}]
    # District buckets: Pune n=5 survives, Nagpur n=2 is suppressed.
    districts = body["district_mismatch"]["districts"]
    assert [d["district"] for d in districts] == ["Pune"]
    assert districts[0]["n_students"] == 5
    assert body["district_mismatch"]["suppressed_groups"] == 1
    assert body["dropoff"]["started"] == 7 and body["dropoff"]["dropped"] == 0
    assert body["avg_items"]["average_items"] == 12.0


def test_resistance_dashboard_aggregates_and_suppresses(client_with_db, db_session):
    client = client_with_db
    occ, pune_tokens = _seed_world(client, db_session)
    # One objection per Pune room (topic=income) -> 5 distinct students -> kept.
    admin = _register(client, "admin3@t.com", "admin")
    admin_uid = client.get("/auth/me", headers=_auth(admin)).json()["user_id"]

    pune_sids = [
        client.get("/auth/me", headers=_auth(t)).json()["student_id"]
        for t in pune_tokens[:5]  # Pune students are the first five seeded
    ]
    for sid in pune_sids:
        room = Room(code=f"R{sid}", student_id=sid)
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)
        db_session.add(
            Objection(
                room_id=room.id, raised_by_user_id=admin_uid, occupation_id=occ.id,
                topic="income", sentiment="concern",
            )
        )
    # A single-student room with a different topic -> suppressed bucket.
    solo = _register(client, "solo@t.com", "student")
    solo_sid = client.get("/auth/me", headers=_auth(solo)).json()["student_id"]
    _set_district(db_session, solo_sid, "Nagpur")
    room = Room(code="SOLO1", student_id=solo_sid)
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)
    db_session.add(
        Objection(
            room_id=room.id, raised_by_user_id=admin_uid, occupation_id=occ.id,
            topic="safety", sentiment="concern",
        )
    )
    db_session.commit()

    body = client.get("/counsellor/resistance", headers=_auth(admin)).json()
    # Admin scope includes the two extra Nagpur students from _seed_world, but
    # their rooms carry no objections, so only Pune (5) + solo (1) count here.
    assert body["total_objections"] == 6
    income = next(b for b in body["by_topic"] if b["label"] == "income")
    assert income["count"] == 5
    labels = [b["label"] for b in body["by_topic"]]
    assert "safety" not in labels  # backed by only 1 student
    assert [d["label"] for d in body["by_district"]] == ["Pune"]
    assert body["suppressed_groups"] >= 1


def test_override_records_audit(client_with_db, db_session):
    client = client_with_db
    occ, pune_tokens = _seed_world(client, db_session)
    admin = _register(client, "admin4@t.com", "admin")
    sid = client.get("/auth/me", headers=_auth(pune_tokens[0])).json()["student_id"]

    resp = client.post(
        "/counsellor/override",
        headers=_auth(admin),
        json={"student_id": sid, "occupation_id": occ.id, "note": "family prefers local centre"},
    )
    assert resp.status_code == 200, resp.text

    audit = client.get("/counsellor/audit", headers=_auth(admin)).json()
    assert len(audit) == 1
    entry = audit[0]
    assert entry["action"] == "override"
    assert entry["entity_type"] == "student"
    assert entry["entity_id"] == str(sid)
    assert entry["detail"]["note"] == "family prefers local centre"


def test_student_deletion_is_audited(client_with_db, db_session):
    client = client_with_db
    token = _register(client, "doomed@t.com", "student")
    sid = client.get("/auth/me", headers=_auth(token)).json()["student_id"]
    assert client.delete("/auth/students/me", headers=_auth(token)).status_code == 200

    admin = _register(client, "admin5@t.com", "admin")
    audit = client.get("/counsellor/audit", headers=_auth(admin)).json()
    deletions = [a for a in audit if a["action"] == "data_deletion"]
    assert len(deletions) == 1
    assert deletions[0]["entity_id"] == str(sid)
    # The trail must not preserve deleted personal data.
    assert "email" not in json.dumps(deletions[0]["detail"])


def test_feedback_roundtrip_and_retraining_export(client_with_db, db_session, tmp_path):
    client = client_with_db
    occ, pune_tokens = _seed_world(client, db_session)

    rec = db_session.query(Recommendation).filter_by(occupation_id=occ.id).first()
    student = pune_tokens[0]

    ok = client.post(
        "/feedback",
        headers=_auth(student),
        json={
            "recommendation_id": rec.id, "helpful": True, "chosen": False,
            "topic": "income", "sentiment": "concern",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["topic"] == "income"

    bad = client.post(
        "/feedback",
        headers=_auth(student),
        json={"recommendation_id": rec.id, "topic": "vibes"},
    )
    assert bad.status_code == 422

    missing = client.post(
        "/feedback",
        headers=_auth(student),
        json={"recommendation_id": 999999},
    )
    assert missing.status_code == 404

    samples = build_samples(db_session)
    assert len(samples) == 1
    sample = samples[0]
    assert sample["relevance"] == 1  # helpful, not chosen
    assert sample["sentiment"] == "concern"
    assert sample["district"] == "Pune"
    assert sample["model_version"] == "test-v1"

    out = tmp_path / "processed" / "retrain_feedback.jsonl"
    summary = export_feedback(db_session, out_path=out)
    assert summary["n_samples"] == 1 and summary["n_positive"] == 1
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["feedback_id"] == sample["feedback_id"]


def test_student_detail_shape(client_with_db, db_session):
    client = client_with_db
    occ, pune_tokens = _seed_world(client, db_session)
    admin = _register(client, "admin6@t.com", "admin")
    sid = client.get("/auth/me", headers=_auth(pune_tokens[0])).json()["student_id"]

    body = client.get(f"/counsellor/students/{sid}", headers=_auth(admin)).json()
    assert body["student_id"] == sid
    assert body["district"] == "Pune"
    assert body["assessment"]["status"] == "complete"
    assert body["assessment"]["riasec"]["R"] == 9.0
    assert body["recommendations"][0]["occupation_name"] == "Electrician"
    assert body["recommendations"][0]["reasons"][0]["code"] == "TEST"
    assert body["room"] is None
    assert AuditLog.__tablename__ == "audit_logs"
