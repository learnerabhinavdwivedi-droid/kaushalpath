"""Phase 5: Auth schemas."""
from pydantic import BaseModel, EmailStr


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
    email: EmailStr
    role: str
    lang: str
    student_id: int | None = None
