"""Phase 5: Room routes."""
import random
import string

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.room import CriteriaWeight, Room, RoomMember
from app.models.student import Student
from app.models.user import User
from app.models.vote import Vote
from app.schemas.room import (
    CompareRequest,
    ConsensusResponse,
    RoomResponse,
    VoteCreate,
    WeightsUpdate,
)

router = APIRouter(prefix="/rooms", tags=["rooms"])

def generate_room_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_room_and_verify_member(code: str, user_id: int, db: Session) -> Room:
    room = db.query(Room).filter(Room.code == code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    member = db.query(RoomMember).filter(RoomMember.room_id == room.id, RoomMember.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    return room

@router.post("", response_model=RoomResponse)
def create_room(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create rooms")
    
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    code = generate_room_code()
    # Handle collision safely
    while db.query(Room).filter(Room.code == code).first():
        code = generate_room_code()

    room = Room(code=code, student_id=student.id)
    db.add(room)
    db.commit()
    db.refresh(room)

    # Add creator as member
    member = RoomMember(room_id=room.id, user_id=current_user.id, role="student")
    db.add(member)
    
    # Initialize default weights
    weights = CriteriaWeight(room_id=room.id, user_id=current_user.id)
    db.add(weights)
    
    db.commit()

    return {"code": room.code, "student_id": room.student_id}

@router.post("/{code}/join")
def join_room(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.code == code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = db.query(RoomMember).filter(RoomMember.room_id == room.id, RoomMember.user_id == current_user.id).first()
    if not member:
        member = RoomMember(room_id=room.id, user_id=current_user.id, role=current_user.role)
        db.add(member)
        weights = CriteriaWeight(room_id=room.id, user_id=current_user.id)
        db.add(weights)
        db.commit()

    return {"status": "joined", "room_code": room.code}

@router.put("/{code}/weights")
def update_weights(code: str, weights_in: WeightsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = get_room_and_verify_member(code, current_user.id, db)
    
    # Normalise weights
    total = sum([weights_in.cost, weights_in.duration, weights_in.salary, weights_in.local_jobs, weights_in.distance])
    if total == 0:
        total = 1.0 # fallback

    cw = db.query(CriteriaWeight).filter(CriteriaWeight.room_id == room.id, CriteriaWeight.user_id == current_user.id).first()
    if not cw:
        cw = CriteriaWeight(room_id=room.id, user_id=current_user.id)
        db.add(cw)

    cw.cost = weights_in.cost / total
    cw.duration = weights_in.duration / total
    cw.salary = weights_in.salary / total
    cw.local_jobs = weights_in.local_jobs / total
    cw.distance = weights_in.distance / total

    db.commit()
    return {"status": "updated"}

@router.post("/{code}/vote")
def cast_vote(code: str, vote_in: VoteCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = get_room_and_verify_member(code, current_user.id, db)
    
    vote = db.query(Vote).filter(
        Vote.room_id == room.id, 
        Vote.user_id == current_user.id,
        Vote.occupation_id == vote_in.occupation_id
    ).first()
    
    if vote:
        vote.score = vote_in.score
    else:
        vote = Vote(room_id=room.id, user_id=current_user.id, occupation_id=vote_in.occupation_id, score=vote_in.score)
        db.add(vote)

    db.commit()
    return {"status": "voted"}

@router.get("/{code}/consensus", response_model=ConsensusResponse)
def get_consensus(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = get_room_and_verify_member(code, current_user.id, db)
    
    votes = db.query(Vote).filter(Vote.room_id == room.id).all()
    if not votes:
        return {"ranking": [], "agreement_index": 0.0, "next_step": "Vote to see consensus."}
    
    scores = {}
    for v in votes:
        if v.occupation_id not in scores:
            scores[v.occupation_id] = []
        scores[v.occupation_id].append(v.score)
    
    ranking = []
    variances = []
    for occ_id, s in scores.items():
        avg = sum(s) / len(s)
        var = np.var(s) if len(s) > 1 else 0
        variances.append(var)
        ranking.append({
            "occupation_id": occ_id,
            "avg_score": round(avg, 2)
        })
    
    ranking = sorted(ranking, key=lambda x: x["avg_score"], reverse=True)
    avg_variance = sum(variances) / len(variances) if variances else 0
    agreement_index = max(0.0, min(1.0, 1.0 - (avg_variance / 4.0))) # variance max is approx 4 (range 1-5)

    next_step = "discuss cost vs salary" if agreement_index < 0.7 else "ready for roadmap"

    return {
        "ranking": ranking,
        "agreement_index": round(agreement_index, 2),
        "next_step": next_step
    }

@router.post("/{code}/compare")
def compare_options(code: str, req: CompareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = get_room_and_verify_member(code, current_user.id, db)
    # Stubbed implementation of comparison logic
    # In real implementation: gather weights for all members in room
    # Compute score per occupation based on normalized criteria
    # Find max divergence
    return {
        "status": "comparison_done",
        "disagree_highlight": "Member A values cost highly, Member B values salary.",
        "results": {}
    }
