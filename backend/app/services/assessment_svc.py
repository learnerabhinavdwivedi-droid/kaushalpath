"""Assessment service: DB glue around the pure adaptive engine.

`ml/assessment/adaptive.py` is DB-free and operates on a JSON-serialisable
session dict. This service owns the transaction: it persists that dict on
`assessments.state_json` (resumable across calls / processes) and denormalises
the finished profile into the typed columns. Routes catch `BadRequest` and map
it to HTTP 400; a missing resource is signalled with the ORM `None` they turn
into 404.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.ml.assessment import adaptive, scoring
from app.models import Assessment, Student, User

_BAD_REQUEST = 400

_interest_bank: list[dict] | None = None
_aptitude_bank: list[dict] | None = None


class BadRequest(Exception):
    """Client error the route layer turns into HTTP 400."""


def banks() -> tuple[list[dict], list[dict]]:
    """Item banks, loaded once and cached (read-only)."""
    global _interest_bank, _aptitude_bank
    if _interest_bank is None:
        _interest_bank = adaptive.load_interest_bank()
    if _aptitude_bank is None:
        _aptitude_bank = adaptive.load_aptitude_bank()
    return _interest_bank, _aptitude_bank


def _item_out(item: dict, section: str, lang: str) -> dict:
    text = item.get(f"text_{lang}") or item["text_en"]
    if section == "aptitude":
        return {
            "id": item["id"],
            "section": "aptitude",
            "dimension": item["dimension"],
            "text": text,
            "options": list(item["options"]),
        }
    return {
        "id": item["id"],
        "section": "interest",
        "text": text,
        "scale": [1, 2, 3, 4, 5],
    }


def _persist_state(assessment: Assessment, state: dict) -> None:
    """Store the session snapshot.

    The engine mutates `state` (which is the same object loaded from
    `assessment.state_json`) in place, so a plain re-assignment — even with a
    deep copy — compares equal to the loaded value and SQLAlchemy skips the
    UPDATE. `flag_modified` forces the JSON column onto the change set.
    """
    assessment.state_json = state
    flag_modified(assessment, "state_json")


def get_or_create_student(
    session: Session, student_id: int, constraints: dict[str, Any] | None = None
) -> Student:
    """Fetch a student or create a placeholder (temporary id until auth lands in
    Phase 5). `constraints` uses model field names; updates in place when given.
    """
    student = session.scalar(select(Student).where(Student.id == student_id))
    if student is not None:
        if constraints:
            for key, value in constraints.items():
                if value is not None:
                    setattr(student, key, value)
            try:
                session.commit()
            except IntegrityError as exc:  # CHECK-constraint violation
                session.rollback()
                raise BadRequest(str(exc.orig)) from exc
        return student

    c = constraints or {}
    user = User(
        email=f"student_{student_id}@example.test",
        hashed_password="demo-no-auth",
        role="student",
        lang=c.get("language", "hi"),
    )
    session.add(user)
    session.flush()
    student = Student(
        id=student_id,
        user_id=user.id,
        age=c.get("age"),
        edu_level=c.get("edu_level", "12th"),
        district=c.get("district", "unknown"),
        state=c.get("state", "unknown"),
        budget_band=c.get("budget_band", "mid"),
        income_band=c.get("income_band"),
        relocate_ok=c.get("relocate_ok", False),
        language=c.get("language", "hi"),
        max_duration_months=c.get("max_duration_months"),
    )
    session.add(student)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise BadRequest(str(exc.orig)) from exc
    return session.scalar(select(Student).where(Student.id == student_id))


def _sync_result_columns(assessment: Assessment, state: dict) -> None:
    """Denormalise the finished profile into the typed assessment columns."""
    riasec = state["riasec"]
    assessment.riasec_r = riasec["R"]
    assessment.riasec_i = riasec["I"]
    assessment.riasec_a = riasec["A"]
    assessment.riasec_s = riasec["S"]
    assessment.riasec_e = riasec["E"]
    assessment.riasec_c = riasec["C"]
    apt = state["aptitude"]
    assessment.apt_num = apt["num"]
    assessment.apt_verbal = apt["verbal"]
    assessment.apt_spatial = apt["spatial"]
    assessment.apt_mech = apt["mech"]
    assessment.confidence = state["confidence"]
    assessment.items_answered = state["items_answered"]


def start_or_resume_session(
    session: Session, student_id: int, restart: bool = False
) -> tuple[Assessment, dict, dict | None]:
    """Return (assessment, state, next_item_or_None). Reuses the open session
    unless `restart` is set (which abandons any in-progress assessment).
    """
    student = session.scalar(select(Student).where(Student.id == student_id))
    if student is None:
        get_or_create_student(session, student_id)
        student = session.scalar(select(Student).where(Student.id == student_id))

    if restart:
        for open_assessment in session.scalars(
            select(Assessment).where(
                Assessment.student_id == student_id, Assessment.status == "in_progress"
            )
        ).all():
            open_assessment.status = "abandoned"
        session.flush()

    assessment = None
    if not restart:
        assessment = session.scalar(
            select(Assessment)
            .where(Assessment.student_id == student_id, Assessment.status == "in_progress")
            .order_by(Assessment.id.desc())
        )
    if assessment is None:
        assessment = Assessment(
            student_id=student_id,
            status="in_progress",
            state_json=adaptive.new_state(),
            items_answered=0,
        )
        session.add(assessment)
        session.flush()

    interest_bank, aptitude_bank = banks()
    state = assessment.state_json or adaptive.new_state()
    state["lang"] = student.language  # surface preferred language to _serve
    item = adaptive.next_item(state, interest_bank, aptitude_bank)
    if item is not None:
        _persist_state(assessment, state)  # new object -> SQLAlchemy sees the change
        session.commit()
        return assessment, state, item

    if state.get("status") == "completed":
        assessment.status = "completed"
        _sync_result_columns(assessment, state)
    _persist_state(assessment, state)
    session.commit()
    return assessment, state, None


def answer_item(
    session: Session, assessment_id: int, answer: Any, item_id: str | None
) -> tuple[Assessment, dict, dict | None]:
    """Apply one answer to the currently-served item, persist and advance."""
    assessment = session.get(Assessment, assessment_id)
    if assessment is None:
        raise LookupError("assessment not found")
    if assessment.status != "in_progress":
        raise BadRequest("assessment already completed")

    interest_bank, aptitude_bank = banks()
    state = assessment.state_json or adaptive.new_state()
    current = adaptive.next_item(state, interest_bank, aptitude_bank)
    if current is None:
        raise BadRequest("assessment already complete")
    if item_id is not None and item_id != current["id"]:
        raise BadRequest(f"expected answer for item {current['id']!r}, got {item_id!r}")

    if current["section"] == "interest":
        try:
            value = int(answer)
        except (TypeError, ValueError):
            raise BadRequest("interest answer must be an integer 1..5") from None
        try:
            adaptive.record_interest_answer(state, interest_bank, current["id"], value)
        except ValueError as exc:  # engine range / unknown-item guard
            raise BadRequest(str(exc)) from exc
    else:
        if str(answer) not in [str(o) for o in current["options"]]:
            raise BadRequest("answer must be one of the item's options")
        adaptive.record_aptitude_answer(
            state, interest_bank, aptitude_bank, current["id"], answer
        )

    next_item = adaptive.next_item(state, interest_bank, aptitude_bank)
    if state.get("status") == "completed":
        assessment.status = "completed"
        _sync_result_columns(assessment, state)
    _persist_state(assessment, state)
    session.commit()
    return assessment, state, next_item


def get_result(session: Session, student_id: int) -> Assessment:
    """The student's completed profile (or, failing that, their latest session).

    Raises LookupError when the student has no assessment yet.
    """
    assessment = session.scalar(
        select(Assessment)
        .where(Assessment.student_id == student_id, Assessment.status == "completed")
        .order_by(Assessment.id.desc())
    )
    if assessment is None:
        assessment = session.scalar(
            select(Assessment)
            .where(Assessment.student_id == student_id)
            .order_by(Assessment.id.desc())
        )
    if assessment is None:
        raise LookupError("no assessment found for student")
    return assessment


def result_payload(assessment: Assessment) -> dict:
    riasec = {
        "R": assessment.riasec_r,
        "I": assessment.riasec_i,
        "A": assessment.riasec_a,
        "S": assessment.riasec_s,
        "E": assessment.riasec_e,
        "C": assessment.riasec_c,
    }
    return {
        "assessment_id": assessment.id,
        "student_id": assessment.student_id,
        "riasec": riasec,
        "top3_code": scoring.top3_code(riasec),
        "aptitude": {
            "num": assessment.apt_num,
            "verbal": assessment.apt_verbal,
            "spatial": assessment.apt_spatial,
            "mech": assessment.apt_mech,
        },
        "confidence": assessment.confidence,
        "items_answered": assessment.items_answered,
        "status": assessment.status,
    }
