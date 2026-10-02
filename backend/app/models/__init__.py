"""Import all models so `Base.metadata` is fully populated (Alembic + create_all)."""
from app.models.assessment import Assessment
from app.models.centre import Centre
from app.models.course import Course
from app.models.feedback import Feedback
from app.models.market import Market
from app.models.occupation import Occupation
from app.models.recommendation import Recommendation
from app.models.room import CriteriaWeight, Room, RoomMember
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
    "Room",
    "RoomMember",
    "CriteriaWeight",
    "Vote",
    "Recommendation",
    "Feedback",
]
