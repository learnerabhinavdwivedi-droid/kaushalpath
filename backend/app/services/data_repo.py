"""Typed read queries over the Phase 1 data layer.

Repository functions only — no scoring, ranking or eligibility logic here (that
arrives in Phase 3). Every function takes an explicit `session` so callers own
the transaction. Returned objects are detached ORM rows or plain values.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Centre, Course, Market, Occupation


def get_occupations(
    session: Session,
    *,
    nsqf_level: int | None = None,
    min_nsqf_level: int | None = None,
    max_nsqf_level: int | None = None,
    name_contains: str | None = None,
    limit: int | None = None,
) -> Sequence[Occupation]:
    """Fetch occupations, optionally filtered by NSQF band / name substring."""
    stmt = select(Occupation)
    if nsqf_level is not None:
        stmt = stmt.where(Occupation.nsqf_level == nsqf_level)
    if min_nsqf_level is not None:
        stmt = stmt.where(Occupation.nsqf_level >= min_nsqf_level)
    if max_nsqf_level is not None:
        stmt = stmt.where(Occupation.nsqf_level <= max_nsqf_level)
    if name_contains:
        stmt = stmt.where(Occupation.name_en.ilike(f"%{name_contains}%"))
    stmt = stmt.order_by(Occupation.name_en)
    if limit is not None:
        stmt = stmt.limit(limit)
    return session.scalars(stmt).all()


def get_courses_for(
    session: Session,
    occupation_id: int,
    *,
    district: str | None = None,
) -> Sequence[Course]:
    """Courses for an occupation; when `district` is given, only those actually
    offered by a centre in that district (distinct)."""
    if district is None:
        stmt = (
            select(Course)
            .where(Course.occupation_id == occupation_id)
            .order_by(Course.nsqf_level, Course.name)
        )
        return session.scalars(stmt).all()

    stmt = (
        select(Course)
        .join(Centre, Centre.course_id == Course.id)
        .where(Course.occupation_id == occupation_id, Centre.district == district)
        .distinct()
        .order_by(Course.nsqf_level, Course.name)
    )
    return session.scalars(stmt).all()


def get_centres_for_course(session: Session, course_id: int) -> Sequence[Centre]:
    """Centres offering a given course, ordered by state then district."""
    stmt = (
        select(Centre)
        .where(Centre.course_id == course_id)
        .order_by(Centre.state, Centre.district)
    )
    return session.scalars(stmt).all()


def get_market(
    session: Session,
    occupation_id: int,
    state: str | None = None,
) -> Sequence[Market]:
    """Market rows for an occupation, optionally restricted to one state."""
    stmt = select(Market).where(Market.occupation_id == occupation_id)
    if state is not None:
        stmt = stmt.where(Market.state == state)
    stmt = stmt.order_by(Market.year.desc(), Market.state)
    return session.scalars(stmt).all()
