"""Phase 5: Integration Tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Setup in-memory sqlite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_auth_and_room_flow():
    # 1. Register student
    resp = client.post("/auth/register", json={
        "email": "student@test.com",
        "password": "password",
        "role": "student",
        "give_consent": True
    })
    assert resp.status_code == 200
    student_token = resp.json()["access_token"]
    
    # 2. Register parent
    resp = client.post("/auth/register", json={
        "email": "parent@test.com",
        "password": "password",
        "role": "parent",
        "give_consent": True
    })
    assert resp.status_code == 200
    parent_token = resp.json()["access_token"]
    
    # 3. Register another parent (unauthorized to room later)
    resp = client.post("/auth/register", json={
        "email": "other@test.com",
        "password": "password",
        "role": "parent",
        "give_consent": True
    })
    other_token = resp.json()["access_token"]

    # 4. Create room
    headers_student = {"Authorization": f"Bearer {student_token}"}
    resp = client.post("/rooms", headers=headers_student)
    assert resp.status_code == 200
    room_code = resp.json()["code"]

    # 5. Parent joins room
    headers_parent = {"Authorization": f"Bearer {parent_token}"}
    resp = client.post(f"/rooms/{room_code}/join", headers=headers_parent)
    assert resp.status_code == 200

    # 6. Auth failure: unauthorized user tries to vote
    headers_other = {"Authorization": f"Bearer {other_token}"}
    resp = client.post(f"/rooms/{room_code}/vote", headers=headers_other, json={"occupation_id": 1, "score": 5})
    assert resp.status_code == 403

    # 7. Weights normalization
    resp = client.put(f"/rooms/{room_code}/weights", headers=headers_student, json={
        "cost": 1.0, "duration": 0.0, "salary": 0.0, "local_jobs": 0.0, "distance": 1.0
    })
    assert resp.status_code == 200

    # 8. Consensus math
    client.post(f"/rooms/{room_code}/vote", headers=headers_student, json={"occupation_id": 1, "score": 5})
    client.post(f"/rooms/{room_code}/vote", headers=headers_parent, json={"occupation_id": 1, "score": 3})
    
    resp = client.get(f"/rooms/{room_code}/consensus", headers=headers_student)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ranking"][0]["occupation_id"] == 1
    assert data["ranking"][0]["avg_score"] == 4.0
    assert "agreement_index" in data

    # 9. Deletion
    resp = client.delete("/auth/students/me", headers=headers_student)
    assert resp.status_code == 200
