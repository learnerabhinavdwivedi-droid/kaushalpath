"""Import all models so `Base.metadata` is fully populated (Alembic + create_all)."""
from app.models.assessment import Assessment
from app.models.audit import AuditLog
from app.models.centre import Centre
from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.course import Course
from app.models.feedback import Feedback
from app.models.human import (
    CounsellorAssignment,
    CounsellorOverride,
    Escalation,
    Objection,
)
from app.models.market import Market
from app.models.mentor import MentorRequest
from app.models.occupation import Occupation
from app.models.progression import ProgressionPath
from app.models.provider_outcome import ProviderOutcome
from app.models.recommendation import Recommendation
from app.models.room import CriteriaWeight, Room, RoomMember, CallRequest
from app.models.scheme import Scheme
from app.models.student import Student
from app.models.user import User
from app.models.vote import Vote

__all__ = [
    "User",
    "Student",
    "Assessment",
    "Occupation",
    "Course",
    "Centre",
    "Market",
    "ProviderOutcome",
    "ProgressionPath",
    "Scheme",
    "Room",
    "RoomMember",
    "CriteriaWeight",
    "CallRequest",
    "Vote",
    "Recommendation",
    "Feedback",
    "Escalation",
    "CounsellorAssignment",
    "CounsellorOverride",
    "Objection",
    "MentorRequest",
    "AuditLog",
    "Conversation",
    "Turn",
    "ResistanceSnapshot",
]
