"""Assessment endpoints (PHASE_2.md).

Flow:
  POST /assessment/student?student_id=N   capture hard-constraint intake (income_band, …)
  GET  /assessment/next?student_id=N      start/resume -> first item (or POST /session)
  POST /assessment/answer                 submit {assessment_id, answer, item_id?}
  GET  /assessment/result?student_id=N    finished profile

Session state is resumable: re-calling /next with an ``assessment_id`` returns
the pending item without re-answering. Interest items carry a 1..5 scale;
aptitude items carry option strings. Text follows the student's stored language.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Assessment
from app.schemas import assessment as sch
from app.services import assessment_svc

router = APIRouter(prefix="/assessment", tags=["assessment"])

_BAD_REQUEST = status.HTTP_400_BAD_REQUEST
_NOT_FOUND = status.HTTP_404_NOT_FOUND


def _serve(assessment: Assessment, state: dict, item: dict | None) -> sch.NextItemOut:
    done = item is None
    payload = {
        "assessment_id": assessment.id,
        "status": state.get("status", "in_progress"),
        "done": done,
        "items_answered": state.get("items_answered", 0),
        "confidence": state.get("confidence", 0.0),
    }
    if not done:
        lang = state.get("lang", "en")
        text = item.get(f"text_{lang}") or item["text_en"]
        if item["section"] == "interest":
            payload["item"] = {"id": item["id"], "section": "interest", "text": text}
        else:
            payload["item"] = {
                "id": item["id"],
                "section": "aptitude",
                "dimension": item["dimension"],
                "text": text,
                "options": list(item["options"]),
            }
    return sch.NextItemOut(**payload)


@router.post(
    "/student",
    response_model=sch.ConstraintsIn,
    status_code=status.HTTP_201_CREATED,
    summary="Capture hard-constraint intake (incl household income_band)",
)
def upsert_student(
    student_id: int = Query(..., ge=1, description="Temporary id until auth in Phase 5"),
    payload: sch.ConstraintsIn = ...,  # noqa: B008
    db: Session = Depends(get_db),
) -> sch.ConstraintsIn:
    try:
        assessment_svc.get_or_create_student(db, student_id, payload.model_dump())
    except assessment_svc.BadRequest as exc:
        raise HTTPException(_BAD_REQUEST, str(exc)) from exc
    return payload


@router.post("/session", response_model=sch.NextItemOut, summary="Start (or restart) a session")
def new_session(
    student_id: int = Query(..., ge=1),
    restart: bool = Query(False, description="Abandon any open session and start fresh"),
    db: Session = Depends(get_db),
) -> sch.NextItemOut:
    assessment, state, item = assessment_svc.start_or_resume_session(
        db, student_id, restart=restart
    )
    return _serve(assessment, state, item)


@router.get("/next", response_model=sch.NextItemOut, summary="Next item (start or resume)")
def next_item(
    student_id: int | None = Query(None, ge=1),
    assessment_id: int | None = Query(None, ge=1, description="Resume a specific session"),
    db: Session = Depends(get_db),
) -> sch.NextItemOut:
    if assessment_id is not None:
        assessment = db.get(Assessment, assessment_id)
        if assessment is None:
            raise HTTPException(_NOT_FOUND, "assessment not found")
        state = assessment.state_json or {}
        interest_bank, aptitude_bank = assessment_svc.banks()
        from app.ml.assessment import adaptive

        item = adaptive.next_item(state, interest_bank, aptitude_bank)
        return _serve(assessment, state, item)
    if student_id is None:
        raise HTTPException(_BAD_REQUEST, "provide student_id or assessment_id")
    assessment, state, item = assessment_svc.start_or_resume_session(db, student_id)
    return _serve(assessment, state, item)


@router.post("/answer", response_model=sch.NextItemOut, summary="Submit an answer, advance session")
def answer(payload: sch.AnswerIn, db: Session = Depends(get_db)) -> sch.NextItemOut:
    try:
        assessment, state, item = assessment_svc.answer_item(
            db, payload.assessment_id, payload.answer, payload.item_id
        )
    except LookupError as exc:
        raise HTTPException(_NOT_FOUND, str(exc)) from exc
    except assessment_svc.BadRequest as exc:
        raise HTTPException(_BAD_REQUEST, str(exc)) from exc
    return _serve(assessment, state, item)


@router.get("/result", response_model=sch.ProfileOut, summary="Finished student profile")
def result(
    student_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> sch.ProfileOut:
    try:
        assessment = assessment_svc.get_result(db, student_id)
    except LookupError as exc:
        raise HTTPException(_NOT_FOUND, str(exc)) from exc
    return sch.ProfileOut(**assessment_svc.result_payload(assessment))
