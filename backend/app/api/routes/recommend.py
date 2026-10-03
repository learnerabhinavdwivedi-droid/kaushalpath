"""API routes for Phase 3 recommendations."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.recommend_svc import RecommendService

router = APIRouter(prefix="/recommend", tags=["recommendation"])

class RecommendRequest(BaseModel):
    student_id: int
    top_k: int = 3

@router.post("")
def get_recommendations(req: RecommendRequest, db: Session = Depends(get_db)):
    """Generate recommendations for a given student based on their profile and assessment."""
    svc = RecommendService(db)
    try:
        results = svc.get_recommendations(req.student_id, req.top_k)
        return results
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
