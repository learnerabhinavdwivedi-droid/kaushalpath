"""Phase 20: Grounded Occupation Ability Requirements (O*NET 31.0 Abilities)."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EvidenceMixin, SourceMixin, TimestampMixin


class OccupationAbility(Base, TimestampMixin, SourceMixin, EvidenceMixin):
    """Ability requirement profile per occupation (numerical, verbal, spatial, mechanical).

    Grounded in O*NET 31.0 Abilities and Knowledge (Grade A).
    Powers personalized, trade-specific aptitude matching in recommendation ranking.
    """
    __tablename__ = "occupation_abilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    occupation_id: Mapped[int] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # 4 core aptitude dimensions, scaled 0.0 to 1.0 (O*NET normalized)
    required_num: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    required_verbal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    required_spatial: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    required_mech: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Primary aptitude dimension distinguishing this trade ('num', 'verbal', 'spatial', 'mech')
    primary_ability: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Relationship back to Occupation
    occupation = relationship("Occupation", backref="ability_requirement", lazy="joined")
