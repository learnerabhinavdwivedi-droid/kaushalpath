"""Phase 5: Counsellor routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/counsellor", tags=["counsellor"])

class OverrideRequest(BaseModel):
    student_id: int
    occupation_id: int
    note: str

@router.get("/cohort")
def get_cohort(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "counsellor":
        raise HTTPException(status_code=403, detail="Counsellor access only")
    
    # Mock return list of assigned students
    # Real implementation would join Student and a hypothetical Assignment table
    return [
        {"student_id": 1, "name": "Student A", "status": "assessed"},
        {"student_id": 2, "name": "Student B", "status": "pending_vote"}
    ]

@router.post("/override")
def override_recommendation(req: OverrideRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "counsellor":
        raise HTTPException(status_code=403, detail="Counsellor access only")
    
    # Real implementation would store the override with an audit trail
    return {"status": "overridden", "note_logged": req.note}
