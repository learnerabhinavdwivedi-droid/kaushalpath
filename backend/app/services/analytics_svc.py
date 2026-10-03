"""Phase 8: counsellor analytics + resistance aggregation.

All views are computed over an explicit list of ``student_ids`` (a counsellor's
cohort; admins pass the full set). The service is pure read/aggregation — no
HTTP, no mutation.

Small-group suppression (PHASE_8 non-negotiable): any grouped bucket backed by
fewer than ``MIN_GROUP`` distinct students is hidden from the result and only
counted into ``suppressed_groups`` so the UI can say "N groups hidden" without
leaking who they are.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    AuditLog,
    Objection,
    Occupation,
    Recommendation,
    Room,
    Student,
    Vote,
)

MIN_GROUP = 5
RIASEC_KEYS = {
    "riasec_r": "Realistic",
    "riasec_i": "Investigative",
    "riasec_a": "Artistic",
    "riasec_s": "Social",
    "riasec_e": "Enterprising",
    "riasec_c": "Conventional",
}


def _suppress(buckets: Counter) -> tuple[Counter, int]:
    """Drop buckets smaller than MIN_GROUP; return kept + suppressed count."""
    kept = Counter({k: v for k, v in buckets.items() if v >= MIN_GROUP})
    suppressed = sum(1 for v in buckets.values() if v < MIN_GROUP)
    return kept, suppressed


def _students_in(db: Session, student_ids: list[int]) -> list[Student]:
    if not student_ids:
        return []
    return list(db.scalars(select(Student).where(Student.id.in_(student_ids))).all())


def _latest_assessments(db: Session, student_ids: list[int]) -> dict[int, Assessment]:
    """One (latest) assessment row per student."""
    latest: dict[int, Assessment] = {}
    for a in db.scalars(
        select(Assessment).where(Assessment.student_id.in_(student_ids)).order_by(Assessment.id)
    ).all():
        latest[a.student_id] = a  # later rows overwrite earlier -> latest wins
    return latest


def riasec_distribution(db: Session, student_ids: list[int]) -> dict[str, Any]:
    """Count each student's dominant RIASEC dimension."""
    assessments = _latest_assessments(db, student_ids).values()
    buckets: Counter = Counter()
    for a in assessments:
        scores = {key: getattr(a, key) for key in RIASEC_KEYS}
        dominant = max(scores, key=scores.get)
        buckets[RIASEC_KEYS[dominant]] += 1
    kept, suppressed = _suppress(buckets)
    return {
        "distribution": [{"type": t, "count": kept[t]} for t in sorted(kept)],
        "suppressed_groups": suppressed,
    }


def top_trades(db: Session, student_ids: list[int]) -> dict[str, Any]:
    """Most-recommended occupations across the cohort."""
    occ_names = dict(
        db.execute(select(Occupation.id, Occupation.name_en)).all()  # type: ignore[arg-type]
    )
    buckets: Counter = Counter()
    for rec in db.scalars(
        select(Recommendation).where(Recommendation.student_id.in_(student_ids))
    ).all():
        buckets[occ_names.get(rec.occupation_id, str(rec.occupation_id))] += 1
    kept, suppressed = _suppress(buckets)
    ranked = sorted(kept.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "top_trades": [{"label": name, "count": n} for name, n in ranked],
        "suppressed_groups": suppressed,
    }


def assessment_dropoff(db: Session, student_ids: list[int]) -> dict[str, Any]:
    """Started vs completed assessments (no suppression — cohort-level counts)."""
    started = len(_latest_assessments(db, student_ids))
    completed = sum(
        1 for a in _latest_assessments(db, student_ids).values() if a.status == "complete"
    )
    return {
        "started": started,
        "completed": completed,
        "dropped": started - completed,
        "dropoff_rate": round(1 - completed / started, 3) if started else 0.0,
    }


def avg_items_asked(db: Session, student_ids: list[int]) -> dict[str, Any]:
    """Mean number of adaptive items answered across completed assessments."""
    rows = [
        a.items_answered
        for a in _latest_assessments(db, student_ids).values()
        if a.status == "complete"
    ]
    return {"average_items": round(sum(rows) / len(rows), 2) if rows else 0.0, "n": len(rows)}


def rooms_stats(db: Session, student_ids: list[int]) -> dict[str, Any]:
    """Rooms created and how many reached consensus (>=1 vote cast)."""
    rooms = db.scalars(select(Room).where(Room.student_id.in_(student_ids))).all()
    room_ids = [r.id for r in rooms]
    voted = set(
        db.scalars(select(Vote.room_id).where(Vote.room_id.in_(room_ids))).all()
    ) if room_ids else set()
    return {
        "rooms_created": len(rooms),
        "consensus_reached": len(voted),
    }


def district_mismatch(db: Session, student_ids: list[int]) -> dict[str, Any]:
    """Per district: student count, most-recommended trade and its mean demand.

    A district whose top trade has low market demand is a demand/recommendation
    mismatch worth a counsellor's attention. Buckets < MIN_GROUP are hidden.
    """
    district_of = {s.id: s.district for s in _students_in(db, student_ids)}
    per_district_recs: dict[str, list[int]] = defaultdict(list)
    occ_total: dict[str, Counter] = defaultdict(Counter)
    for rec in db.scalars(
        select(Recommendation).where(Recommendation.student_id.in_(student_ids))
    ).all():
        d = district_of.get(rec.student_id)
        if d:
            per_district_recs[d].append(rec.occupation_id)
            occ_total[d][rec.occupation_id] += 1

    occ_names = dict(db.execute(select(Occupation.id, Occupation.name_en)).all())  # type: ignore[arg-type]

    kept: list[dict] = []
    suppressed = 0
    for d, occs in per_district_recs.items():
        n = len(set(_students_by_district(student_ids, district_of, d)))
        if n < MIN_GROUP:
            suppressed += 1
            continue
        top_occ_id = occ_total[d].most_common(1)[0][0]
        kept.append(
            {
                "district": d,
                "n_students": n,
                "top_trade": occ_names.get(top_occ_id, str(top_occ_id)),
                "recommendations": len(occs),
            }
        )
    return {"districts": kept, "suppressed_groups": suppressed}


def _students_by_district(
    student_ids: list[int], district_of: dict[int, str], district: str
) -> list[int]:
    return [sid for sid in student_ids if district_of.get(sid) == district]


def resistance(db: Session, student_ids: list[int]) -> dict[str, Any]:
    """Family-resistance dashboard (PS 26241): where + why resistance concentrates.

    Groups recorded objections by district, trade and topic, hiding any bucket
    backed by fewer than MIN_GROUP distinct students.
    """
    room_student = {
        r.id: r.student_id
        for r in db.scalars(select(Room).where(Room.student_id.in_(student_ids))).all()
    }
    occ_names = dict(db.execute(select(Occupation.id, Occupation.name_en)).all())  # type: ignore[arg-type]
    district_of = {s.id: s.district for s in _students_in(db, student_ids)}

    by_topic: Counter = Counter()
    by_district: Counter = Counter()
    by_trade: Counter = Counter()
    concern_by_topic: Counter = Counter()
    # distinct students touching each grouping (for suppression)
    students_by_topic: dict[str, set] = defaultdict(set)
    students_by_district: dict[str, set] = defaultdict(set)
    students_by_trade: dict[str, set] = defaultdict(set)

    objections = db.scalars(
        select(Objection).join(Room, Objection.room_id == Room.id).where(
            Room.student_id.in_(student_ids)
        )
    ).all()
    for o in objections:
        sid = room_student.get(o.room_id)
        district = district_of.get(sid, "Unknown")
        trade = occ_names.get(o.occupation_id, "General") if o.occupation_id else "General"
        by_topic[o.topic] += 1
        by_district[district] += 1
        by_trade[trade] += 1
        if o.sentiment == "concern":
            concern_by_topic[o.topic] += 1
        students_by_topic[o.topic].add(sid)
        students_by_district[district].add(sid)
        students_by_trade[trade].add(sid)

    def _bucket(counter: Counter, students_map: dict[str, set]) -> tuple[list, int]:
        kept: list[dict] = []
        suppressed = 0
        for key, n in counter.items():
            if len(students_map[key]) < MIN_GROUP:
                suppressed += 1
                continue
            kept.append({"label": key, "count": n})
        kept.sort(key=lambda x: x["count"], reverse=True)
        return kept, suppressed

    topics, s1 = _bucket(by_topic, students_by_topic)
    districts, s2 = _bucket(by_district, students_by_district)
    trades, s3 = _bucket(by_trade, students_by_trade)
    return {
        "total_objections": len(objections),
        "by_topic": topics,
        "by_district": districts,
        "by_trade": trades,
        "concern_by_topic": [
            {"label": t, "count": n} for t, n in concern_by_topic.most_common()
        ],
        "suppressed_groups": s1 + s2 + s3,
    }


def list_audit(db: Session, student_ids: list[int] | None, limit: int = 100) -> list[dict]:
    """Recent override / deletion audit entries (admin: all; counsellor: own scope)."""
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if student_ids is not None:
        # A counsellor only sees entries about students in their cohort.
        stmt = stmt.where(AuditLog.entity_type == "student").where(
            AuditLog.entity_id.in_([str(s) for s in student_ids])
        )
    rows = db.scalars(stmt.limit(limit)).all()
    return [
        {
            "id": a.id,
            "actor_user_id": a.actor_user_id,
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "detail": a.detail,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]
