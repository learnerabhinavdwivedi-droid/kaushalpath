"""Phase 5: Room schemas."""
from pydantic import BaseModel, Field


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

class ConsensusResponse(BaseModel):
    ranking: list[dict]
    agreement_index: float
    next_step: str
