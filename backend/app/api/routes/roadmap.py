"""Phase 5: Roadmap route (data-driven, no mocks)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Centre, Course, Market, Occupation
from app.models.user import User

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("/{occupation_id}")
def get_roadmap(
    occupation_id: int,
    district: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ordered, sourced steps for reaching an occupation."""
    occupation = db.get(Occupation, occupation_id)
    if not occupation:
        raise HTTPException(status_code=404, detail="Occupation not found")

    courses = db.scalars(
        select(Course).where(Course.occupation_id == occupation_id).order_by(Course.nsqf_level)
    ).all()
    course = courses[0] if courses else None

    steps: list[dict] = []

    min_edu = course.min_edu if course else None
    steps.append(
        {
            "step": 1,
            "type": "eligibility",
            "detail": f"Minimum education: {min_edu or 'check course entry requirements'}.",
        }
    )

    steps.append(
        {
            "step": 2,
            "type": "course",
            "detail": (
                f"Enrol in {course.name}"
                if course
                else "No mapped course found in the catalogue yet."
            ),
        }
    )

    centre_names: list[str] = []
    if course:
        centre_stmt = select(Centre).where(Centre.course_id == course.id)
        centres = db.scalars(centre_stmt).all()
        local = [c for c in centres if district and c.district == district]
        show = local or centres
        centre_names = [f"{c.name} ({c.district})" for c in show[:3]]
    steps.append(
        {
            "step": 3,
            "type": "centres",
            "detail": (
                "Nearest centres: " + ", ".join(centre_names)
                if centre_names
                else f"No centres listed near {district or 'your area'} yet."
            ),
        }
    )

    steps.append(
        {
            "step": 4,
            "type": "certification",
            "detail": (
                f"{course.cert_body or 'Certifying body TBD'} — NSQF level "
                f"{occupation.nsqf_level or course.nsqf_level or 'n/a'}."
                if course
                else f"NSQF level {occupation.nsqf_level or 'n/a'}."
            ),
        }
    )

    markets = db.scalars(select(Market).where(Market.occupation_id == occupation_id)).all()
    placements = [m.placement_rate for m in markets if m.placement_rate is not None]
    placement_note = (
        f"Placement signal ~{max(placements):.0f}%." if placements else "Placement data pending."
    )
    steps.append(
        {
            "step": 5,
            "type": "placement",
            "detail": f"Apprenticeship / placement — {placement_note}",
        }
    )

    timeline_fee = None
    if course:
        parts = []
        if course.duration_months:
            parts.append(f"~{course.duration_months} months")
        if course.fee_inr is not None:
            parts.append(f"fee ~INR {float(course.fee_inr):,.0f}")
        timeline_fee = ", ".join(parts) if parts else None

    is_demo = bool(getattr(occupation, "is_demo", True)) or any(
        bool(getattr(c, "is_demo", True)) for c in courses
    )
    return {
        "occupation_id": occupation_id,
        "occupation_name": occupation.name_en,
        "district": district,
        "is_demo": is_demo,
        "source": occupation.source,
        "expected": timeline_fee,
        "steps": steps,
    }
