"""Phase 7: room snapshot + objection-recording integration tests."""
from __future__ import annotations

from app.models.occupation import Occupation


def _register(client, email, role):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password", "role": role, "give_consent": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_occupations(db, n=2):
    rows = []
    for i in range(1, n + 1):
        occ = Occupation(name_en=f"Occupation {i}", source="test", is_demo=True, nsqf_level=3)
        db.add(occ)
        rows.append(occ)
    db.commit()
    for occ in rows:
        db.refresh(occ)
    return [occ.id for occ in rows]


def test_room_snapshot_reflects_members_weights_and_votes(client_with_db, db_session):
    client = client_with_db
    occ_ids = _seed_occupations(db_session)

    student = _register(client, "snap-s@test.com", "student")["access_token"]
    parent = _register(client, "snap-p@test.com", "parent")["access_token"]

    code = client.post("/rooms", headers=_auth(student)).json()["code"]
    client.post(f"/rooms/{code}/join", headers=_auth(parent))

    snap = client.get(f"/rooms/{code}", headers=_auth(student))
    assert snap.status_code == 200, snap.text
    body = snap.json()
    assert body["code"] == code
    assert len(body["members"]) == 2
    assert len(body["weights"]) == 2  # one per member, default weights
    assert body["votes"] == []
    assert body["objections"] == []
    # Identity is never leaked in the snapshot.
    assert "email" not in body["members"][0]

    client.put(
        f"/rooms/{code}/weights",
        headers=_auth(parent),
        json={"cost": 0.5, "duration": 0.0, "salary": 1.0, "local_jobs": 0.0, "distance": 0.0},
    )
    client.post(
        f"/rooms/{code}/vote",
        headers=_auth(student),
        json={"occupation_id": occ_ids[0], "score": 5},
    )

    body2 = client.get(f"/rooms/{code}", headers=_auth(parent)).json()
    assert len(body2["votes"]) == 1
    assert body2["votes"][0]["occupation_id"] == occ_ids[0]
    parent_weights = [w for w in body2["weights"] if w["salary"] > w["cost"]][0]
    assert parent_weights["salary"] == 1.0 / 1.5


def test_objection_recorded_and_invalid_topic_rejected(client_with_db, db_session):
    client = client_with_db
    occ_ids = _seed_occupations(db_session, n=1)

    student = _register(client, "obj-s@test.com", "student")["access_token"]
    parent = _register(client, "obj-p@test.com", "parent")["access_token"]

    code = client.post("/rooms", headers=_auth(student)).json()["code"]
    client.post(f"/rooms/{code}/join", headers=_auth(parent))

    obj = client.post(
        f"/rooms/{code}/objection",
        headers=_auth(parent),
        json={"topic": "income", "sentiment": "concern", "occupation_id": occ_ids[0]},
    )
    assert obj.status_code == 200, obj.text
    assert obj.json()["topic"] == "income"
    assert obj.json()["sentiment"] == "concern"

    snap = client.get(f"/rooms/{code}", headers=_auth(student)).json()
    assert len(snap["objections"]) == 1
    assert snap["objections"][0]["occupation_id"] == occ_ids[0]

    bad = client.post(
        f"/rooms/{code}/objection",
        headers=_auth(parent),
        json={"topic": "not-a-real-topic"},
    )
    assert bad.status_code == 422


def test_non_member_cannot_read_snapshot(client_with_db):
    client = client_with_db
    student = _register(client, "own-s@test.com", "student")["access_token"]
    stranger = _register(client, "stranger@test.com", "parent")["access_token"]

    code = client.post("/rooms", headers=_auth(student)).json()["code"]
    denied = client.get(f"/rooms/{code}", headers=_auth(stranger))
    assert denied.status_code == 403
