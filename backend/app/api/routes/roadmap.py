"""Phase 5: Roadmap route."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/roadmap", tags=["roadmap"])

@router.get("/{occupation_id}")
def get_roadmap(occupation_id: int, district: str = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate roadmap for an occupation."""
    
    # Mocked implementation per Phase 5 prompt
    steps = [
        {"step": 1, "type": "eligibility", "detail": "Check minimum education (e.g. 10th pass)"},
        {"step": 2, "type": "course", "detail": "Enroll in suggested ITI course"},
        {"step": 3, "type": "centres", "detail": f"Find nearest centres in {district or 'your area'}"},
        {"step": 4, "type": "certification", "detail": "Complete NSQF aligned certification"},
        {"step": 5, "type": "placement", "detail": "Apprenticeship placement expected within 6 months"}
    ]
    
    return {
        "occupation_id": occupation_id,
        "district": district,
        "is_demo": True,
        "source": "Mock Roadmap Engine",
        "steps": steps
    }
