"""Phase 5: Demo Flow. Registers users, creates room, votes, prints consensus."""
import time

import httpx

BASE_URL = "http://localhost:8000"

def main():
    print("Starting Demo Flow...")
    client = httpx.Client(base_url=BASE_URL)
    
    # 1. Register Student
    print("1. Registering Student...")
    student_data = {
        "email": f"student_{int(time.time())}@example.com",
        "password": "password123",
        "role": "student",
        "lang": "en",
        "give_consent": True
    }
    resp = client.post("/auth/register", json=student_data)
    if resp.status_code != 200:
        print("Failed to register student:", resp.text)
        return
    student_token = resp.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    
    # 2. Register Parent
    print("2. Registering Parent...")
    parent_data = {
        "email": f"parent_{int(time.time())}@example.com",
        "password": "password123",
        "role": "parent",
        "lang": "hi",
        "give_consent": True
    }
    resp = client.post("/auth/register", json=parent_data)
    if resp.status_code != 200:
        print("Failed to register parent:", resp.text)
        return
    parent_token = resp.json()["access_token"]
    parent_headers = {"Authorization": f"Bearer {parent_token}"}
    
    # 3. Create Room (Student)
    print("3. Creating Room...")
    resp = client.post("/rooms", headers=student_headers)
    if resp.status_code != 200:
        print("Failed to create room:", resp.text)
        return
    room_code = resp.json()["code"]
    print(f"   Room created with code: {room_code}")
    
    # 4. Join Room (Parent)
    print("4. Parent joining room...")
    resp = client.post(f"/rooms/{room_code}/join", headers=parent_headers)
    if resp.status_code != 200:
        print("Failed to join room:", resp.text)
        return
        
    # 5. Vote
    print("5. Casting votes...")
    votes = [
        (student_headers, 1, 5),
        (student_headers, 2, 3),
        (parent_headers, 1, 4),
        (parent_headers, 2, 1),
    ]
    for headers, occ, score in votes:
        client.post(
            f"/rooms/{room_code}/vote",
            headers=headers,
            json={"occupation_id": occ, "score": score},
        )
    
    # 6. Consensus
    print("6. Getting consensus...")
    resp = client.get(f"/rooms/{room_code}/consensus", headers=student_headers)
    print(f"Consensus Result: {resp.json()}")

if __name__ == "__main__":
    main()
