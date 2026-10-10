"""Phase 5: Auth routes (register / login / refresh / delete), rate-limited."""
import secrets
from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import or_
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
from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.human import Escalation
from app.models.mentor import MentorRequest
from app.models.room import CriteriaWeight, Room, RoomMember
from app.models.student import Student
from app.models.user import User
from app.schemas.auth import (
    GuestCreate,
    GuestToken,
    MeOut,
    RefreshRequest,
    Token,
    UserCreate,
)
from app.services.audit_svc import record_audit

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

    if user_in.role not in ["student", "parent", "counsellor", "admin", "scheme_admin"]:
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


@router.post("/guest", response_model=GuestToken)
@limiter.limit("10/5 minutes")
def guest_join(request: Request, body: GuestCreate, db: Session = Depends(get_db)):
    """Phase 15: parent guest join for a family room (no email or password).

    Creates a throwaway ``role=parent`` account with a synthetic, unreachable
    email and a random password (there is nothing to phish), binds it to the
    room and returns a 24 h access token. The display name is only echoed
    back — the phone is validated, used for nothing and never stored
    (DPDP data-minimisation).
    """
    code = body.room_code.strip().upper()
    room = db.query(Room).filter(Room.code == code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    user = User(
        email=f"guest-{uuid4().hex[:12]}@guest.kaushalpath.invalid",
        hashed_password=get_password_hash(secrets.token_urlsafe(24)),
        role="parent",
        lang=body.lang or "hi",
        consent_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if not db.query(RoomMember).filter(
        RoomMember.room_id == room.id, RoomMember.user_id == user.id
    ).first():
        db.add(RoomMember(room_id=room.id, user_id=user.id, role="parent"))
        db.add(CriteriaWeight(room_id=room.id, user_id=user.id))
        db.commit()

    return {
        "access_token": create_access_token(user.id, expires_delta=timedelta(hours=24)),
        "room_code": room.code,
        "room_id": room.id,
        "student_id": room.student_id,
        "name": body.name.strip(),
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

    student = db.query(Student).filter(Student.user_id == current_user.id).first()

    # Phase 18: right-to-erasure must clear the conversational trail, not just the
    # account. SQLite FK enforcement is OFF (no PRAGMA foreign_keys), so the
    # ondelete="CASCADE" clauses never fire -> we cascade every dependent row
    # explicitly: the student's conversations, their turns + resistance snapshots,
    # and every escalation raised by / about this student.
    n_conversations = n_turns = n_snapshots = n_escalations = 0
    if student:
        convs = db.query(Conversation).filter(Conversation.student_id == student.id).all()
        conv_ids = [c.id for c in convs]
        n_conversations = len(convs)
        n_turns = (
            db.query(Turn).filter(Turn.conversation_id.in_(conv_ids)).count() if conv_ids else 0
        )
        if conv_ids:
            n_snapshots = db.query(ResistanceSnapshot).filter(
                ResistanceSnapshot.conversation_id.in_(conv_ids)
            ).delete(synchronize_session=False)
        esc_conds = [
            Escalation.student_id == student.id,
            Escalation.raised_by_user_id == current_user.id,
        ]
        if conv_ids:
            esc_conds.append(Escalation.conversation_id.in_(conv_ids))
        n_escalations = db.query(Escalation).filter(or_(*esc_conds)).delete(
            synchronize_session=False
        )
        # Turn rows are removed by the ORM delete-orphan cascade on Conversation.
        for conv in convs:
            db.delete(conv)

    # Phase 8: data deletions must leave an audit trace. Only non-identifying
    # counts are stored (DPDP: the trail must not preserve the deleted data).
    record_audit(
        db,
        actor_user_id=current_user.id,
        action="data_deletion",
        entity_type="student",
        entity_id=student.id if student else None,
        detail={
            "deleted_by": "self",
            "role": current_user.role,
            "conversations": n_conversations,
            "turns": n_turns,
            "resistance_snapshots": n_snapshots,
            "escalations": n_escalations,
        },
    )

    db.delete(current_user)
    db.commit()
    return {"status": "ok"}


class MentorRequestIn(BaseModel):
    phone_number: str

@router.post("/mentor-request")
def create_mentor_request(
    req: MentorRequestIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Phase 18: Request a human mentor."""
    mr = MentorRequest(user_id=current_user.id, phone_number=req.phone_number)
    db.add(mr)
    db.commit()
    db.refresh(mr)
    return {"id": mr.id, "status": mr.status}
