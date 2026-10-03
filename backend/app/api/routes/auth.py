"""Phase 5: Auth routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.db.base import utcnow
from app.db.session import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.auth import Token, UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    
    if user_in.role not in ["student", "parent", "counsellor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role.",
        )

    if not user_in.give_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required to register.",
        )

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        lang=user_in.lang,
        consent_at=utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # If student, create a stub Student profile (they can update it later or during onboarding)
    if user.role == "student":
        student = Student(
            user_id=user.id,
            edu_level="10th", # Default stub
            district="Unknown",
            state="Unknown"
        )
        db.add(student)
        db.commit()

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id)
    }

@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id)
    }

@router.delete("/students/me")
def delete_student_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not a student")
    
    # cascade delete will handle it from User
    db.delete(current_user)
    db.commit()
    return {"status": "ok"}
