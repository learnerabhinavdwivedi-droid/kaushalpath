"""Phase 5: Auth schemas."""
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "student"
    lang: str = "en"
    give_consent: bool = False

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class MeOut(BaseModel):
    user_id: int
    # Output only; registration already validates at input. Phase 15 guest
    # accounts carry a synthetic reserved-domain email that EmailStr would
    # (rightly) refuse to serialise.
    email: str
    role: str
    lang: str
    student_id: int | None = None


class GuestCreate(BaseModel):
    """Phase 15: parent guest join — room code + first name, no email/password."""

    room_code: str = Field(min_length=3, max_length=12)
    name: str = Field(min_length=1, max_length=60)
    phone: str | None = Field(default=None, max_length=24)
    lang: str = Field(default="hi", max_length=8)

    @field_validator("phone")
    @classmethod
    def _digits_only(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        digits = re.sub(r"\D", "", v)
        if not 7 <= len(digits) <= 15:
            raise ValueError("phone must have 7-15 digits")
        return digits


class GuestToken(BaseModel):
    """Scoped parent hand-off: 24 h access token bound to the room's family."""

    access_token: str
    token_type: str = "bearer"
    room_code: str
    room_id: int
    student_id: int
    name: str
