"""Phase 5/8: Counsellor routes — cohort, escalation queue, audited overrides,
student detail, analytics, resistance dashboard and the audit trail."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import utcnow
from app.db.session import get_db
from app.models import (
    Assessment,
    CounsellorAssignment,
    CounsellorOverride,
    Escalation,
    Objection,
    Occupation,
    Recommendation,
    Room,
    RoomMember,
    CallRequest,
    Student,
    User,
    Vote,
)
from app.models.mentor import MentorRequest
from app.schemas.counsellor import (
    AnalyticsOut,
    AuditEntryOut,
    CohortRow,
    RecommendationRow,
    ResistanceOut,
    RoomStatusOut,
    StudentDetailOut,
)
from app.schemas.escalation import EscalationOut
from app.services import analytics_svc
from app.services.audit_svc import record_audit
from app.services.escalation_svc import claim_escalation

router = APIRouter(prefix="/counsellor", tags=["counsellor"])


class OverrideRequest(BaseModel):
    student_id: int
    occupation_id: int
    note: str


class AssignRequest(BaseModel):
    counsellor_id: int
    student_id: int


def _require_counsellor_or_admin(user: User) -> None:
    if user.role not in ("counsellor", "admin"):
        raise HTTPException(status_code=403, detail="Counsellor access only")


def _assigned_student_ids(user: User, db: Session) -> list[int]:
    """Cohort scope: counsellor = assigned students; admin = every student."""
    if user.role == "admin":
        return list(db.scalars(select(Student.id)).all())
    stmt = select(CounsellorAssignment.student_id).where(
        CounsellorAssignment.counsellor_id == user.id
    )
    return list(db.scalars(stmt).all())


@router.get("/cohort", response_model=list[CohortRow])
def get_cohort(
    district: str | None = None,
    edu_level: str | None = None,
    language: str | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Students assigned to this counsellor (admin sees the whole cohort),
    filterable by district / education level / language / assessment status."""
    _require_counsellor_or_admin(current_user)
    student_ids = _assigned_student_ids(current_user, db)
    if not student_ids:
        return []

    assessed = dict(
        db.execute(
            select(Assessment.student_id, func.count(Assessment.id))
            .where(Assessment.student_id.in_(student_ids))
            .group_by(Assessment.student_id)
        ).all()
    )
    rooms = dict(
        db.execute(
            select(Room.student_id, func.count(Room.id))
            .where(Room.student_id.in_(student_ids))
            .group_by(Room.student_id)
        ).all()
    )
    open_esc = dict(
        db.execute(
            select(Escalation.student_id, func.count(Escalation.id))
            .where(Escalation.student_id.in_(student_ids), Escalation.status == "open")
            .group_by(Escalation.student_id)
        ).all()
    )

    cohort: list[dict] = []
    for student in db.scalars(select(Student).where(Student.id.in_(student_ids))).all():
        row = {
            "student_id": student.id,
            "district": student.district,
            "edu_level": student.edu_level,
            "language": student.language,
            "status": "assessed" if student.id in assessed else "pending_assessment",
            "has_room": student.id in rooms,
            "open_escalations": open_esc.get(student.id, 0),
        }
        if district and row["district"].lower() != district.lower():
            continue
        if edu_level and row["edu_level"] != edu_level:
            continue
        if language and row["language"] != language:
            continue
        if status and row["status"] != status:
            continue
        cohort.append(row)
    return cohort


@router.post("/assign")
def assign_student(
    req: AssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin-only: put a student in a counsellor's cohort."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    counsellor = db.get(User, req.counsellor_id)
    if not counsellor or counsellor.role != "counsellor":
        raise HTTPException(status_code=404, detail="Counsellor not found")
    student = db.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    existing = db.scalars(
        select(CounsellorAssignment).where(
            CounsellorAssignment.counsellor_id == req.counsellor_id,
            CounsellorAssignment.student_id == req.student_id,
        )
    ).first()
    if not existing:
        db.add(CounsellorAssignment(counsellor_id=req.counsellor_id, student_id=req.student_id))
        db.commit()

    # Route any of this student's still-unassigned open escalations to them.
    for esc in db.scalars(
        select(Escalation).where(
            Escalation.student_id == req.student_id,
            Escalation.assigned_counsellor_id.is_(None),
        )
    ).all():
        esc.assigned_counsellor_id = req.counsellor_id
    db.commit()

    return {"status": "assigned", "counsellor_id": req.counsellor_id, "student_id": req.student_id}


@router.get("/escalations")
def list_escalations(
    status: str | None = None,
    pool: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Escalation queue for this counsellor (admin sees everything).

    A counsellor sees both their own assigned cases AND the shared pool of
    still-unassigned open cases (Phase 14: unassigned cases are no longer
    admin-only). Optional ``status`` filters the lifecycle; ``pool=true``
    restricts to unassigned open cases.
    """
    _require_counsellor_or_admin(current_user)
    stmt = select(Escalation)
    if current_user.role != "admin":
        assigned = Escalation.assigned_counsellor_id == current_user.id
        unassigned_pool = (
            Escalation.assigned_counsellor_id.is_(None) & (Escalation.status == "open")
        )
        stmt = stmt.where(assigned | unassigned_pool)
    if pool is True:
        stmt = stmt.where(
            Escalation.assigned_counsellor_id.is_(None), Escalation.status == "open"
        )
    if status:
        stmt = stmt.where(Escalation.status == status)

    queue = [
        {
            "id": e.id,
            "room_id": e.room_id,
            "conversation_id": e.conversation_id,
            "student_id": e.student_id,
            "occupation_id": e.occupation_id,
            "reason": e.reason,
            "status": e.status,
            "channel": e.channel,
            "priority": e.priority,
            "preferred_language": e.preferred_language,
            "assigned_counsellor_id": e.assigned_counsellor_id,
            "in_pool": e.assigned_counsellor_id is None,
        }
        for e in db.scalars(stmt.order_by(Escalation.id)).all()
    ]
    return queue


class NoteRequest(BaseModel):
    note: str = Field(min_length=1)


@router.post("/escalations/{escalation_id}/claim", response_model=EscalationOut)
def claim_escalation_route(
    escalation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atomically claim an open/pool case. 409 if another counsellor won it."""
    _require_counsellor_or_admin(current_user)
    esc = claim_escalation(db, escalation_id, current_user.id)
    if not esc:
        raise HTTPException(status_code=409, detail="Escalation already claimed or not open")
    record_audit(
        db,
        actor_user_id=current_user.id,
        action="escalation_claim",
        entity_type="escalation",
        entity_id=esc.id,
        detail={"student_id": esc.student_id},
    )
    db.commit()
    return esc


@router.post("/escalations/{escalation_id}/contact", response_model=EscalationOut)
def contact_escalation(
    escalation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a claimed case as contacted (counsellor reached the family)."""
    _require_counsellor_or_admin(current_user)
    esc = db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if current_user.role != "admin" and esc.assigned_counsellor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your escalation")
    if esc.status not in ("assigned", "contacted"):
        raise HTTPException(status_code=409, detail=f"Cannot contact from status={esc.status}")
    esc.mark("contacted")
    db.commit()
    db.refresh(esc)
    return esc


@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationOut)
def resolve_escalation(
    escalation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve an escalation once the family concern is closed out."""
    _require_counsellor_or_admin(current_user)
    esc = db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if current_user.role != "admin" and esc.assigned_counsellor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your escalation")
    if esc.status == "resolved":
        raise HTTPException(status_code=409, detail="Already resolved")
    esc.mark("resolved")
    record_audit(
        db,
        actor_user_id=current_user.id,
        action="escalation_resolve",
        entity_type="escalation",
        entity_id=esc.id,
        detail={"student_id": esc.student_id},
    )
    db.commit()
    db.refresh(esc)
    return esc


@router.post("/escalations/{escalation_id}/notes", response_model=EscalationOut)
def add_escalation_note(
    escalation_id: int,
    req: NoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Append a counsellor note to the case (audited free text)."""
    _require_counsellor_or_admin(current_user)
    esc = db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if current_user.role != "admin" and esc.assigned_counsellor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your escalation")
    stamp = utcnow().strftime("%Y-%m-%d %H:%M")
    prefix = f"{esc.notes}\n" if esc.notes else ""
    esc.notes = f"{prefix}[{stamp}] {req.note}"
    db.commit()
    db.refresh(esc)
    return esc


@router.post("/override")
def override_recommendation(
    req: OverrideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record an audited manual recommendation on top of the model output."""
    _require_counsellor_or_admin(current_user)

    student = db.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role != "admin":
        assigned = db.scalars(
            select(CounsellorAssignment).where(
                CounsellorAssignment.counsellor_id == current_user.id,
                CounsellorAssignment.student_id == req.student_id,
            )
        ).first()
        if not assigned:
            raise HTTPException(status_code=403, detail="Student not in your cohort")

    override = CounsellorOverride(
        counsellor_id=current_user.id,
        student_id=req.student_id,
        occupation_id=req.occupation_id,
        note=req.note,
    )
    db.add(override)
    db.commit()
    db.refresh(override)

    # Phase 8: overrides must also land in the general audit trail.
    record_audit(
        db,
        actor_user_id=current_user.id,
        action="override",
        entity_type="student",
        entity_id=req.student_id,
        detail={
            "override_id": override.id,
            "occupation_id": req.occupation_id,
            "note": req.note,
        },
    )

    return {
        "status": "overridden",
        "override_id": override.id,
        "note_logged": req.note,
        "audit": {
            "counsellor_id": override.counsellor_id,
            "student_id": override.student_id,
            "occupation_id": override.occupation_id,
            "created_at": override.created_at.isoformat(),
        },
    }


@router.get("/students/{student_id}", response_model=StudentDetailOut)
def student_detail(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full picture for one cohort student: profile, assessment, recommendations
    with reasons, recorded overrides and room status. Only assigned students are
    visible (PHASE_8 DO NOT: no leaks to non-assigned counsellors)."""
    _require_counsellor_or_admin(current_user)
    if current_user.role != "admin":
        assigned = db.scalars(
            select(CounsellorAssignment).where(
                CounsellorAssignment.counsellor_id == current_user.id,
                CounsellorAssignment.student_id == student_id,
            )
        ).first()
        if not assigned:
            raise HTTPException(status_code=403, detail="Student not in your cohort")

    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    assessment = db.scalars(
        select(Assessment)
        .where(Assessment.student_id == student_id)
        .order_by(Assessment.id.desc())
    ).first()
    occ_name = dict(db.execute(select(Occupation.id, Occupation.name_en)).all())
    occ_demo = dict(db.execute(select(Occupation.id, Occupation.is_demo)).all())
    recs = [
        RecommendationRow(
            occupation_id=r.occupation_id,
            occupation_name=occ_name.get(r.occupation_id, str(r.occupation_id)),
            rank=r.rank,
            score=r.score,
            reasons=r.reasons_json or [],
            is_demo=bool(occ_demo.get(r.occupation_id, True)),
        )
        for r in db.scalars(
            select(Recommendation)
            .where(Recommendation.student_id == student_id)
            .order_by(Recommendation.id, Recommendation.rank)
        ).all()
        if r.rank <= 3  # latest run only
    ]
    overrides = [
        {
            "occupation_id": o.occupation_id,
            "occupation_name": occ_name.get(o.occupation_id, str(o.occupation_id)),
            "note": o.note,
            "counsellor_id": o.counsellor_id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in db.scalars(
            select(CounsellorOverride)
            .where(CounsellorOverride.student_id == student_id)
            .order_by(CounsellorOverride.id.desc())
        ).all()
    ]

    room = db.scalars(
        select(Room).where(Room.student_id == student_id).order_by(Room.id.desc())
    ).first()
    room_out: RoomStatusOut | None = None
    if room:
        votes = db.scalars(select(Vote).where(Vote.room_id == room.id)).all()
        objections = db.scalars(select(Objection).where(Objection.room_id == room.id)).all()
        members = db.scalars(select(RoomMember).where(RoomMember.room_id == room.id)).all()
        room_out = RoomStatusOut(
            code=room.code,
            members=len(members),
            votes=len(votes),
            objections=len(objections),
            consensus_reached=any(m.role == "counsellor" for m in members)
            or len(votes) >= 2,
        )

    return StudentDetailOut(
        student_id=student.id,
        district=student.district,
        state=student.state,
        edu_level=student.edu_level,
        language=student.language,
        budget_band=student.budget_band,
        assessment=(
            {
                "status": assessment.status,
                "items_answered": assessment.items_answered,
                "confidence": assessment.confidence,
                "riasec": {
                    "R": assessment.riasec_r,
                    "I": assessment.riasec_i,
                    "A": assessment.riasec_a,
                    "S": assessment.riasec_s,
                    "E": assessment.riasec_e,
                    "C": assessment.riasec_c,
                },
            }
            if assessment
            else None
        ),
        recommendations=recs,
        overrides=overrides,
        room=room_out,
    )


def _scoped_student_ids(user: User, db: Session) -> list[int]:
    """Cohort scope for aggregate views (admin: everyone)."""
    return _assigned_student_ids(user, db)


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Cohort-level impact metrics. Groups smaller than 5 students are hidden
    server-side (small-group suppression)."""
    _require_counsellor_or_admin(current_user)
    ids = _scoped_student_ids(current_user, db)
    return {
        "riasec": analytics_svc.riasec_distribution(db, ids),
        "top_trades": analytics_svc.top_trades(db, ids),
        "dropoff": analytics_svc.assessment_dropoff(db, ids),
        "rooms": analytics_svc.rooms_stats(db, ids),
        "avg_items": analytics_svc.avg_items_asked(db, ids),
        "district_mismatch": analytics_svc.district_mismatch(db, ids),
    }


@router.get("/resistance", response_model=ResistanceOut)
def resistance_dashboard(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Where and why family resistance concentrates (topic / district / trade),
    built from the Phase 7 objection tags."""
    _require_counsellor_or_admin(current_user)
    ids = _scoped_student_ids(current_user, db)
    return analytics_svc.resistance(db, ids)


@router.get("/audit", response_model=list[AuditEntryOut])
def audit_log(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Override + data-deletion trail (admin: all; counsellor: own cohort)."""
    _require_counsellor_or_admin(current_user)
    ids = None if current_user.role == "admin" else _scoped_student_ids(current_user, db)
    return analytics_svc.list_audit(db, ids)


@router.get("/call-requests")
def list_call_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_counsellor_or_admin(current_user)
    reqs = db.query(CallRequest).order_by(CallRequest.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "room_id": r.room_id,
            "requested_by": r.requested_by_user_id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reqs
    ]

@router.get("/mentor-requests")
def list_mentor_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_counsellor_or_admin(current_user)
    reqs = db.query(MentorRequest).order_by(MentorRequest.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "phone_number": r.phone_number,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reqs
    ]
