"""Phase 5: Counsellor routes — cohort, escalation queue, audited overrides."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assessment import Assessment
from app.models.human import CounsellorAssignment, CounsellorOverride, Escalation
from app.models.student import Student
from app.models.user import User

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
    stmt = select(CounsellorAssignment.student_id)
    if user.role != "admin":
        stmt = stmt.where(CounsellorAssignment.counsellor_id == user.id)
    return list(db.scalars(stmt).all())


@router.get("/cohort")
def get_cohort(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Students assigned to this counsellor (admin sees the whole cohort)."""
    _require_counsellor_or_admin(current_user)
    student_ids = _assigned_student_ids(current_user, db)
    if not student_ids:
        return []

    assessed = set(
        db.scalars(
            select(Assessment.student_id).where(Assessment.student_id.in_(student_ids))
        ).all()
    )
    cohort = []
    for student in db.scalars(select(Student).where(Student.id.in_(student_ids))).all():
        cohort.append(
            {
                "student_id": student.id,
                "district": student.district,
                "edu_level": student.edu_level,
                "status": "assessed" if student.id in assessed else "pending_assessment",
            }
        )
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
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Open escalation queue for this counsellor (admin sees all open)."""
    _require_counsellor_or_admin(current_user)
    stmt = select(Escalation).where(Escalation.status == "open")
    if current_user.role != "admin":
        stmt = stmt.where(Escalation.assigned_counsellor_id == current_user.id)
    queue = [
        {
            "id": e.id,
            "room_id": e.room_id,
            "student_id": e.student_id,
            "occupation_id": e.occupation_id,
            "reason": e.reason,
            "status": e.status,
        }
        for e in db.scalars(stmt.order_by(Escalation.id)).all()
    ]
    return queue


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(
    escalation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_counsellor_or_admin(current_user)
    esc = db.get(Escalation, escalation_id)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if current_user.role != "admin" and esc.assigned_counsellor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your escalation")
    esc.status = "resolved"
    db.commit()
    return {"id": esc.id, "status": esc.status}


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
