"""Phase 5: Family decision rooms, weights, votes, consensus, compare, escalation."""
import random
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.human import CounsellorAssignment, Escalation, Objection
from app.models.room import CriteriaWeight, Room, RoomMember
from app.models.student import Student
from app.models.user import User
from app.models.vote import Vote
from app.schemas.room import (
    CompareRequest,
    ConsensusResponse,
    EscalationCreate,
    EscalationResponse,
    ObjectionCreate,
    ObjectionOut,
    RoomResponse,
    RoomSnapshotResponse,
    VoteCreate,
    WeightsUpdate,
)
from app.services.compare_svc import compare_occupations

router = APIRouter(prefix="/rooms", tags=["rooms"])

_VOTE_MAX_VARIANCE = 4.0  # variance ceiling for a 1-5 score range


def generate_room_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def get_room_and_verify_member(code: str, user_id: int, db: Session) -> Room:
    room = db.query(Room).filter(Room.code == code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    member = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room.id, RoomMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    return room


def _member_user_ids(room_id: int, db: Session) -> list[int]:
    rows = db.scalars(select(RoomMember.user_id).where(RoomMember.room_id == room_id)).all()
    return list(rows)


@router.post("", response_model=RoomResponse)
def create_room(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create rooms")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    code = generate_room_code()
    while db.query(Room).filter(Room.code == code).first():
        code = generate_room_code()

    room = Room(code=code, student_id=student.id)
    db.add(room)
    db.commit()
    db.refresh(room)

    db.add(RoomMember(room_id=room.id, user_id=current_user.id, role="student"))
    db.add(CriteriaWeight(room_id=room.id, user_id=current_user.id))
    db.commit()

    return {"code": room.code, "student_id": room.student_id}


@router.post("/{code}/join")
def join_room(
    code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.code == code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room.id, RoomMember.user_id == current_user.id)
        .first()
    )
    if not member:
        db.add(RoomMember(room_id=room.id, user_id=current_user.id, role=current_user.role))
        db.add(CriteriaWeight(room_id=room.id, user_id=current_user.id))
        db.commit()

    return {"status": "joined", "room_code": room.code}


@router.put("/{code}/weights")
def update_weights(
    code: str,
    weights_in: WeightsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = get_room_and_verify_member(code, current_user.id, db)

    values = [
        weights_in.cost,
        weights_in.duration,
        weights_in.salary,
        weights_in.local_jobs,
        weights_in.distance,
    ]
    total = sum(values) or 1.0

    cw = (
        db.query(CriteriaWeight)
        .filter(CriteriaWeight.room_id == room.id, CriteriaWeight.user_id == current_user.id)
        .first()
    )
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
def cast_vote(
    code: str,
    vote_in: VoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = get_room_and_verify_member(code, current_user.id, db)

    vote = (
        db.query(Vote)
        .filter(
            Vote.room_id == room.id,
            Vote.user_id == current_user.id,
            Vote.occupation_id == vote_in.occupation_id,
        )
        .first()
    )
    if vote:
        vote.score = vote_in.score
    else:
        db.add(
            Vote(
                room_id=room.id,
                user_id=current_user.id,
                occupation_id=vote_in.occupation_id,
                score=vote_in.score,
            )
        )

    db.commit()
    return {"status": "voted"}


@router.get("/{code}/consensus", response_model=ConsensusResponse)
def get_consensus(
    code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    room = get_room_and_verify_member(code, current_user.id, db)

    votes = db.query(Vote).filter(Vote.room_id == room.id).all()
    if not votes:
        return {"ranking": [], "agreement_index": 0.0, "next_step": "Vote to see consensus."}

    scores: dict[int, list[int]] = {}
    for v in votes:
        scores.setdefault(v.occupation_id, []).append(v.score)

    ranking = []
    variances = []
    for occ_id, s in scores.items():
        avg = sum(s) / len(s)
        var = sum((x - avg) ** 2 for x in s) / len(s)
        variances.append(var)
        ranking.append({"occupation_id": occ_id, "avg_score": round(avg, 2)})

    ranking.sort(key=lambda x: x["avg_score"], reverse=True)
    avg_variance = sum(variances) / len(variances) if variances else 0.0
    agreement_index = max(0.0, min(1.0, 1.0 - (avg_variance / _VOTE_MAX_VARIANCE)))
    next_step = "discuss cost vs salary" if agreement_index < 0.7 else "ready for roadmap"

    return {
        "ranking": ranking,
        "agreement_index": round(agreement_index, 2),
        "next_step": next_step,
    }


@router.post("/{code}/compare")
def compare_options(
    code: str,
    req: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = get_room_and_verify_member(code, current_user.id, db)
    if not req.occupation_ids:
        raise HTTPException(status_code=400, detail="occupation_ids must not be empty")
    return compare_occupations(
        db,
        room_id=room.id,
        student_id=room.student_id,
        member_user_ids=_member_user_ids(room.id, db),
        occupation_ids=req.occupation_ids,
    )


@router.get("/{code}", response_model=RoomSnapshotResponse)
def get_room(
    code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Room snapshot for the UI: members, each member's weights, votes and
    recorded objections. Personal identity is never leaked — members are shown
    only by ``(user_id, role)``."""
    room = get_room_and_verify_member(code, current_user.id, db)

    members = db.query(RoomMember).filter(RoomMember.room_id == room.id).all()
    weights = db.query(CriteriaWeight).filter(CriteriaWeight.room_id == room.id).all()
    votes = db.query(Vote).filter(Vote.room_id == room.id).all()
    objections = db.query(Objection).filter(Objection.room_id == room.id).all()

    return {
        "code": room.code,
        "student_id": room.student_id,
        "members": [{"user_id": m.user_id, "role": m.role} for m in members],
        "weights": [
            {
                "user_id": w.user_id,
                "cost": w.cost,
                "duration": w.duration,
                "salary": w.salary,
                "local_jobs": w.local_jobs,
                "distance": w.distance,
            }
            for w in weights
        ],
        "votes": [
            {"user_id": v.user_id, "occupation_id": v.occupation_id, "score": v.score}
            for v in votes
        ],
        "objections": [
            {
                "id": o.id,
                "raised_by_user_id": o.raised_by_user_id,
                "occupation_id": o.occupation_id,
                "topic": o.topic,
                "sentiment": o.sentiment,
            }
            for o in objections
        ],
    }


@router.post("/{code}/objection", response_model=ObjectionOut)
def record_objection(
    code: str,
    req: ObjectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tag a parental objection raised from the deterministic conversation
    surface (topic + sentiment). Feeds the Phase 8 admin resistance dashboard."""
    room = get_room_and_verify_member(code, current_user.id, db)
    obj = Objection(
        room_id=room.id,
        raised_by_user_id=current_user.id,
        occupation_id=req.occupation_id,
        topic=req.topic,
        sentiment=req.sentiment,
        note=req.note,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {
        "id": obj.id,
        "raised_by_user_id": obj.raised_by_user_id,
        "occupation_id": obj.occupation_id,
        "topic": obj.topic,
        "sentiment": obj.sentiment,
    }


@router.post("/{code}/escalate", response_model=EscalationResponse)
def escalate(
    code: str,
    req: EscalationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = get_room_and_verify_member(code, current_user.id, db)
    counsellor = db.scalars(
        select(CounsellorAssignment.counsellor_id).where(
            CounsellorAssignment.student_id == room.student_id
        )
    ).first()
    esc = Escalation(
        room_id=room.id,
        raised_by_user_id=current_user.id,
        student_id=room.student_id,
        occupation_id=req.occupation_id,
        reason=req.reason,
        status="open",
        assigned_counsellor_id=counsellor,
    )
    db.add(esc)
    db.commit()
    db.refresh(esc)
    return {
        "id": esc.id,
        "room_code": room.code,
        "status": esc.status,
        "reason": esc.reason,
    }
