"""Phase 5: Family comparison engine.

Turns a set of occupations into normalised criterion scores (0..1, higher is
better), applies each room member's stored criteria weights to produce a
weighted total per member, averages those into a combined family score, and
flags where the family disagrees most (largest member-score spread and, within
that option, the criterion whose weights diverge most between members).

All raw signals come from the seeded catalogue (courses / centres / market);
nothing here is mocked. Missing values degrade to a neutral 0.5 so an option is
never penalised for absent demo data.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Centre, Course, CriteriaWeight, Market, Occupation, Student

CRITERIA = ("cost", "duration", "salary", "local_jobs", "distance")

# Distance proxies (km) mirror recommend_svc so compare and rank agree.
_DIST_HOME_DISTRICT = 10.0
_DIST_HOME_STATE = 120.0
_DIST_OTHER = 450.0
_DEFAULT_WEIGHT = 0.2


def _student_location(db: Session, student_id: int) -> tuple[str | None, str | None]:
    student = db.get(Student, student_id)
    if not student:
        return None, None
    return student.district, student.state


def _course_distance(centres: list[Centre], district: str | None, state: str | None) -> float:
    if any(c.district == district for c in centres):
        return _DIST_HOME_DISTRICT
    if any(c.state == state for c in centres):
        return _DIST_HOME_STATE
    return _DIST_OTHER


def _raw_criteria(
    db: Session, occupation_id: int, district: str | None, state: str | None
) -> dict[str, float | None]:
    """Cheapest/shortest course, best salary/demand, nearest centre."""
    courses = db.scalars(select(Course).where(Course.occupation_id == occupation_id)).all()
    raw: dict[str, float | None] = {
        "cost": None,
        "duration": None,
        "salary": None,
        "local_jobs": None,
        "distance": None,
    }
    if courses:
        course_ids = [c.id for c in courses]
        fees = [float(c.fee_inr) for c in courses if c.fee_inr is not None]
        durations = [float(c.duration_months) for c in courses if c.duration_months is not None]
        if fees:
            raw["cost"] = min(fees)
        if durations:
            raw["duration"] = min(durations)

        centres = db.scalars(select(Centre).where(Centre.course_id.in_(course_ids))).all()
        if centres:
            raw["distance"] = _course_distance(centres, district, state)

    markets = db.scalars(select(Market).where(Market.occupation_id == occupation_id)).all()
    salaries = [float(m.avg_salary_inr) for m in markets if m.avg_salary_inr is not None]
    demands = [m.demand_index for m in markets if m.demand_index is not None]
    if salaries:
        raw["salary"] = max(salaries)
    if demands:
        raw["local_jobs"] = max(demands)
    return raw


def _normalise(raw_by_occ: dict[int, dict[str, float | None]]) -> dict[int, dict[str, float]]:
    """Min-max scale each criterion to 0..1; lower-is-better criteria invert."""
    scores: dict[int, dict[str, float]] = {oid: {} for oid in raw_by_occ}
    lower_better = {"cost", "duration", "distance"}
    for crit in CRITERIA:
        vals = [r[crit] for r in raw_by_occ.values() if r[crit] is not None]
        if not vals:
            for oid in scores:
                scores[oid][crit] = 0.5
            continue
        lo, hi = min(vals), max(vals)
        span = hi - lo
        for oid, raw in raw_by_occ.items():
            v = raw[crit]
            if v is None or span == 0:
                scores[oid][crit] = 0.5
                continue
            norm = (v - lo) / span
            scores[oid][crit] = round(1.0 - norm if crit in lower_better else norm, 4)
    return scores


def _member_weights(db: Session, room_id: int, user_ids: list[int]) -> dict[int, dict[str, float]]:
    weights: dict[int, dict[str, float]] = {}
    rows = db.scalars(
        select(CriteriaWeight).where(
            CriteriaWeight.room_id == room_id, CriteriaWeight.user_id.in_(user_ids)
        )
    ).all()
    by_user = {r.user_id: r for r in rows}
    for uid in user_ids:
        row = by_user.get(uid)
        if not row:
            weights[uid] = dict.fromkeys(CRITERIA, _DEFAULT_WEIGHT)
            continue
        weights[uid] = {
            "cost": row.cost,
            "duration": row.duration,
            "salary": row.salary,
            "local_jobs": row.local_jobs,
            "distance": row.distance,
        }
    return weights


def compare_occupations(
    db: Session,
    room_id: int,
    student_id: int,
    member_user_ids: list[int],
    occupation_ids: list[int],
) -> dict:
    district, state = _student_location(db, student_id)
    raw_by_occ = {oid: _raw_criteria(db, oid, district, state) for oid in occupation_ids}
    scores = _normalise(raw_by_occ)
    member_weights = _member_weights(db, room_id, member_user_ids)

    names = {
        o.id: o.name_en
        for o in db.scalars(select(Occupation).where(Occupation.id.in_(occupation_ids))).all()
    }

    results = []
    for oid in occupation_ids:
        crit = scores[oid]
        member_totals = {
            str(uid): round(sum(member_weights[uid][c] * crit[c] for c in CRITERIA), 4)
            for uid in member_user_ids
        }
        totals = list(member_totals.values())
        family_score = round(sum(totals) / len(totals), 4) if totals else 0.0
        results.append(
            {
                "occupation_id": oid,
                "occupation_name": names.get(oid, f"Occupation {oid}"),
                "criteria": crit,
                "member_totals": member_totals,
                "family_score": family_score,
                "spread": round(max(totals) - min(totals), 4) if totals else 0.0,
            }
        )

    results.sort(key=lambda r: r["family_score"], reverse=True)
    disagreement = _largest_disagreement(results, member_weights)
    return {"results": results, "disagreement": disagreement}


def _largest_disagreement(
    results: list[dict], member_weights: dict[int, dict[str, float]]
) -> dict:
    if len(results) < 1 or len(member_weights) < 2:
        return {"occupation_id": None, "criterion": None, "detail": "Not enough data to disagree."}
    top = max(results, key=lambda r: r["spread"])
    worst_crit = None
    worst_gap = 0.0
    for crit in CRITERIA:
        wvals = [w[crit] for w in member_weights.values()]
        gap = max(wvals) - min(wvals)
        if gap > worst_gap:
            worst_gap, worst_crit = gap, crit
    detail = (
        f"Members disagree most on '{top['occupation_name']}' "
        f"(score spread {top['spread']:.2f})."
    )
    if worst_crit:
        detail += f" Biggest weight clash: '{worst_crit}'."
    return {
        "occupation_id": top["occupation_id"],
        "criterion": worst_crit,
        "detail": detail,
    }
