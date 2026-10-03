"""Phase 5: Room schemas."""
from pydantic import BaseModel, Field, field_validator

from app.models.human import OBJECTION_SENTIMENTS, OBJECTION_TOPICS


class RoomCreate(BaseModel):
    # Optional parameters for creating a room
    pass

class RoomResponse(BaseModel):
    code: str
    student_id: int

class WeightsUpdate(BaseModel):
    cost: float = Field(ge=0.0, le=1.0)
    duration: float = Field(ge=0.0, le=1.0)
    salary: float = Field(ge=0.0, le=1.0)
    local_jobs: float = Field(ge=0.0, le=1.0)
    distance: float = Field(ge=0.0, le=1.0)

class VoteCreate(BaseModel):
    occupation_id: int
    score: int = Field(ge=1, le=5)

class CompareRequest(BaseModel):
    occupation_ids: list[int]

class EscalationCreate(BaseModel):
    reason: str = Field(min_length=1)
    occupation_id: int | None = None

class EscalationResponse(BaseModel):
    id: int
    room_code: str
    status: str
    reason: str

class ConsensusResponse(BaseModel):
    ranking: list[dict]
    agreement_index: float
    next_step: str


class RoomMemberOut(BaseModel):
    user_id: int
    role: str


class MemberWeightsOut(BaseModel):
    user_id: int
    cost: float
    duration: float
    salary: float
    local_jobs: float
    distance: float


class RoomVoteOut(BaseModel):
    user_id: int
    occupation_id: int
    score: int


class ObjectionOut(BaseModel):
    id: int
    raised_by_user_id: int
    occupation_id: int | None
    topic: str
    sentiment: str


class RoomSnapshotResponse(BaseModel):
    code: str
    student_id: int
    members: list[RoomMemberOut]
    weights: list[MemberWeightsOut]
    votes: list[RoomVoteOut]
    objections: list[ObjectionOut]


class ObjectionCreate(BaseModel):
    topic: str = Field(default="other")
    sentiment: str = Field(default="concern")
    occupation_id: int | None = None
    note: str | None = None

    @field_validator("topic")
    @classmethod
    def _topic_known(cls, v: str) -> str:
        if v not in OBJECTION_TOPICS:
            raise ValueError(f"topic must be one of {OBJECTION_TOPICS}")
        return v

    @field_validator("sentiment")
    @classmethod
    def _sentiment_known(cls, v: str) -> str:
        if v not in OBJECTION_SENTIMENTS:
            raise ValueError(f"sentiment must be one of {OBJECTION_SENTIMENTS}")
        return v
