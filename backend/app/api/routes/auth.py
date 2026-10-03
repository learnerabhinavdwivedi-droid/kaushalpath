"""Phase 5: Auth routes (register / login / refresh / delete), rate-limited."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.db.base import utcnow
from app.db.session import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.auth import MeOut, RefreshRequest, Token, UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=Token)
@limiter.limit("10/5 minutes")
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
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
        consent_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if user.role == "student":
        db.add(
            Student(
                user_id=user.id,
                edu_level="10th",
                district="Unknown",
                state="Unknown",
            )
        )
        db.commit()

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
def refresh(request: Request, req: RefreshRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(req.refresh_token, settings.secret_key, algorithms=[ALGORITHM])
        if not payload.get("refresh"):
            raise credentials_exception
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.get("/me", response_model=MeOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the caller's identity + linked student_id (null if not a student)."""
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "lang": current_user.lang,
        "student_id": student.id if student else None,
    }


@router.delete("/students/me")
def delete_student_me(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not a student")

    db.delete(current_user)
    db.commit()
    return {"status": "ok"}
