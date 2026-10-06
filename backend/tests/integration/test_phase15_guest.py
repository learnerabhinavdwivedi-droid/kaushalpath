"""Integration tests for Phase 15 guest parent join + shared chat (PSID 26241).

Acceptance from the gap plan:
* POST /auth/guest {room_code, name, phone?} returns a scoped parent token
  with no email or password;
* the guest is a room member and can open the shared conversation, speak as
  parent and raise a hand-off;
* live escalation status is pollable by the family (without counsellor notes);
* an unknown room code is rejected.
"""
from __future__ import annotations


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _student_with_room(client):
    reg = client.post(
        "/auth/register",
        json={
            "email": "stu15@example.com",
            "password": "password123",
            "role": "student",
            "give_consent": True,
        },
    )
    assert reg.status_code == 200, reg.text
    stu_token = reg.json()["access_token"]
    me = client.get("/auth/me", headers=_auth(stu_token)).json()
    room = client.post("/rooms", headers=_auth(stu_token)).json()
    return stu_token, me["student_id"], room["code"], room["student_id"]


def test_guest_join_chat_and_escalate(client_with_db) -> None:
    client = client_with_db
    stu_token, student_id, code, room_student_id = _student_with_room(client)

    # Guest join: no email, no password — just the code and a first name.
    resp = client.post(
        "/auth/guest",
        json={"room_code": code, "name": "Ramesh", "phone": "+91 98765 43210", "lang": "hi"},
    )
    assert resp.status_code == 200, resp.text
    guest = resp.json()
    assert guest["room_code"] == code
    assert guest["student_id"] == room_student_id
    assert guest["name"] == "Ramesh"
    g_headers = _auth(guest["access_token"])

    who = client.get("/auth/me", headers=g_headers).json()
    assert who["role"] == "parent"
    assert who["email"].startswith("guest-")
    assert who["email"].endswith("@guest.kaushalpath.invalid")

    # The guest is now a room member and can see the room.
    snap = client.get(f"/rooms/{code}", headers=g_headers)
    assert snap.status_code == 200, snap.text
    assert snap.json()["room_id"] == guest["room_id"]

    # Shared conversation bound to the room; parent speaks in Hindi.
    conv = client.post(
        "/conversations",
        json={"student_id": student_id, "room_id": guest["room_id"], "lang": "hi"},
        headers=g_headers,
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]

    turn = client.post(
        f"/conversations/{conv_id}/turns",
        json={"speaker": "parent", "text": "बेटी के लिए यह सुरक्षित नहीं है"},
        headers=g_headers,
    )
    assert turn.status_code == 200, turn.text
    body = client.get(f"/conversations/{conv_id}", headers=g_headers).json()
    speakers = [t["speaker"] for t in body["turns"]]
    assert "parent" in speakers and "assistant" in speakers

    # Hand-off + live status poll (family sees lifecycle only, no notes).
    ack = client.post(
        f"/conversations/{conv_id}/escalate",
        json={
            "reason": "safety concern",
            "contact_phone": "9876543210",
            "preferred_slot": "evening",
        },
        headers=g_headers,
    )
    assert ack.status_code == 201, ack.text
    status = client.get(f"/conversations/{conv_id}/escalation", headers=g_headers)
    assert status.status_code == 200, status.text
    assert status.json()["id"] == ack.json()["id"]
    assert status.json()["status"] in ("open", "assigned")
    assert "notes" not in status.json()


def test_guest_join_unknown_code_rejected(client_with_db) -> None:
    client = client_with_db
    resp = client.post("/auth/guest", json={"room_code": "ZZZZZZ", "name": "Who"})
    assert resp.status_code == 404


def test_guest_phone_normalised_and_required_fields(client_with_db) -> None:
    client = client_with_db
    _, _, code, _ = _student_with_room(client)

    # Missing name -> validation error.
    bad = client.post("/auth/guest", json={"room_code": code})
    assert bad.status_code == 422

    # Garbage phone digits -> validation error, not silent acceptance.
    bad_phone = client.post(
        "/auth/guest", json={"room_code": code, "name": "Sita", "phone": "123"}
    )
    assert bad_phone.status_code == 422

    # And the student sees the guest as a parent member of their room.
    token = client.post(
        "/auth/login", data={"username": "stu15@example.com", "password": "password123"}
    ).json()["access_token"]
    g = client.post("/auth/guest", json={"room_code": code, "name": "Sita"}).json()
    snap = client.get(f"/rooms/{code}", headers=_auth(token)).json()
    assert any(m["role"] == "parent" for m in snap["members"])
    assert g["room_code"] == code
