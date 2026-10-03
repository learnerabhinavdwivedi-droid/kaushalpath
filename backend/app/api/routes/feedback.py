"""Phase 8: feedback loop routes.

A student/parent marks a recommendation helpful/chosen and may attach a
sentiment + objection-topic tag (the Phase 7 taxonomy). Rows land in the
``feedback`` table and are later merged into a retraining dataset by
``scripts/export_feedback.py`` (eval/gold stay untouched).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.feedback import Feedback
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.counsellor import FeedbackCreate, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])
settings = get_settings()


@router.post("", response_model=FeedbackOut)
def submit_feedback(
    req: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = db.get(Recommendation, req.recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    fb = Feedback(
        recommendation_id=req.recommendation_id,
        user_id=current_user.id,
        helpful=req.helpful,
        chosen=req.chosen,
        topic=req.topic,
        sentiment=req.sentiment,
        model_version=rec.model_version or settings.model_version,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return {
        "id": fb.id,
        "recommendation_id": fb.recommendation_id,
        "helpful": fb.helpful,
        "chosen": fb.chosen,
        "topic": fb.topic,
        "sentiment": fb.sentiment,
    }
