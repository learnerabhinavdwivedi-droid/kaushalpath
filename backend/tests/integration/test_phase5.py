"""Phase 5: auth + family-room integration tests.

Uses the shared `client_with_db` fixture (per-test in-memory schema with
`get_db` overridden) instead of module-level engine + global override, so the
file no longer clobbers — or is clobbered by — other test modules.
"""
from __future__ import annotations


def _register(client, email, role):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password", "role": role, "give_consent": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_auth_and_room_flow(client_with_db):
    client = client_with_db

    # 1-3. Register student + two parents
    student_token = _register(client, "student@test.com", "student")
    parent_token = _register(client, "parent@test.com", "parent")
    other_token = _register(client, "other@test.com", "parent")

    # 4. Create room
    headers_student = {"Authorization": f"Bearer {student_token}"}
    resp = client.post("/rooms", headers=headers_student)
    assert resp.status_code == 200, resp.text
    room_code = resp.json()["code"]

    # 5. Parent joins room
    headers_parent = {"Authorization": f"Bearer {parent_token}"}
    resp = client.post(f"/rooms/{room_code}/join", headers=headers_parent)
    assert resp.status_code == 200, resp.text

    # 6. Auth failure: unauthorized user tries to vote
    headers_other = {"Authorization": f"Bearer {other_token}"}
    vote_body = {"occupation_id": 1, "score": 5}
    resp = client.post(f"/rooms/{room_code}/vote", headers=headers_other, json=vote_body)
    assert resp.status_code == 403

    # 7. Weights normalization
    weights = {"cost": 1.0, "duration": 0.0, "salary": 0.0, "local_jobs": 0.0, "distance": 1.0}
    resp = client.put(f"/rooms/{room_code}/weights", headers=headers_student, json=weights)
    assert resp.status_code == 200, resp.text

    # 8. Consensus math
    client.post(f"/rooms/{room_code}/vote", headers=headers_student, json=vote_body)
    client.post(
        f"/rooms/{room_code}/vote", headers=headers_parent, json={"occupation_id": 1, "score": 3}
    )

    resp = client.get(f"/rooms/{room_code}/consensus", headers=headers_student)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ranking"][0]["occupation_id"] == 1
    assert data["ranking"][0]["avg_score"] == 4.0
    assert "agreement_index" in data

    # 9. Deletion
    resp = client.delete("/auth/students/me", headers=headers_student)
    assert resp.status_code == 200, resp.text
