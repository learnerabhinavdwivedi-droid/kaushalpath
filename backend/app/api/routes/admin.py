"""Admin and scheme authority analytics routes (Phase 13: Resistance & Sentiment Analytics)."""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_scheme_admin
from app.db.session import get_db
from app.models.centre import Centre
from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.occupation import Occupation
from app.models.recommendation import Recommendation
from app.models.student import Student
from app.models.user import User
from app.services.analytics_svc import MIN_GROUP
from app.services.resistance import calculate_shift_label

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/resistance")
def get_resistance_analytics(
    group_by: str = Query("district", pattern="^(district|trade|topic)$"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    high_threshold: float = Query(0.60, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_scheme_admin),
) -> dict[str, Any]:
    """Admin resistance analytics across district, trade, or topic with k>=5 suppression."""
    query = select(Conversation)
    if from_date:
        try:
            dt_from = datetime.fromisoformat(from_date)
            query = query.where(Conversation.created_at >= dt_from)
        except ValueError:
            pass
    if to_date:
        try:
            dt_to = datetime.fromisoformat(to_date)
            query = query.where(Conversation.created_at <= dt_to)
        except ValueError:
            pass

    conversations = db.scalars(query).all()
    if not conversations:
        return {
            "group_by": group_by,
            "total_conversations": 0,
            "suppressed_groups": 0,
            "groups": [],
        }

    # Fetch students
    student_ids = list({c.student_id for c in conversations})
    stmt_stu = select(Student).where(Student.id.in_(student_ids))
    students = {s.id: s for s in db.scalars(stmt_stu).all()}

    # Fetch top recommendation for each student (for trade grouping)
    recs = db.scalars(
        select(Recommendation)
        .where(Recommendation.student_id.in_(student_ids), Recommendation.rank == 1)
    ).all()
    occ_by_student = {r.student_id: r.occupation_id for r in recs}

    occ_ids = list(set(occ_by_student.values()))
    occs = {}
    if occ_ids:
        stmt_occ = select(Occupation).where(Occupation.id.in_(occ_ids))
        occs = {o.id: o.name_en for o in db.scalars(stmt_occ).all()}

    # Fetch snapshots by conversation
    conv_ids = [c.id for c in conversations]
    snapshots = db.scalars(
        select(ResistanceSnapshot).where(ResistanceSnapshot.conversation_id.in_(conv_ids))
    ).all()
    rs_by_conv: dict[int, list[float]] = defaultdict(list)
    for s in snapshots:
        rs_by_conv[s.conversation_id].append(s.rs)

    # Fetch turns by conversation
    turns = db.scalars(
        select(Turn).where(Turn.conversation_id.in_(conv_ids)).order_by(Turn.id.asc())
    ).all()
    turns_by_conv: dict[int, list[Turn]] = defaultdict(list)
    for t in turns:
        turns_by_conv[t.conversation_id].append(t)

    # Group conversations
    grouped_convs: dict[str, list[Conversation]] = defaultdict(list)

    for c in conversations:
        stu = students.get(c.student_id)
        if group_by == "district":
            key = stu.district if stu and stu.district else "Unknown District"
            grouped_convs[key].append(c)
        elif group_by == "trade":
            occ_id = occ_by_student.get(c.student_id)
            key = occs.get(occ_id, "General Vocational") if occ_id else "General Vocational"
            grouped_convs[key].append(c)
        elif group_by == "topic":
            c_turns = turns_by_conv.get(c.id, [])
            topics = [t.topic for t in c_turns if t.topic]
            primary_topic = Counter(topics).most_common(1)[0][0] if topics else "other"
            grouped_convs[primary_topic].append(c)

    # Apply suppression (MIN_GROUP = 5)
    kept_groups: list[dict[str, Any]] = []
    suppressed_count = 0

    for key, c_list in grouped_convs.items():
        n = len(c_list)
        if n < MIN_GROUP:
            suppressed_count += 1
            continue

        all_rs: list[float] = []
        topic_counts: Counter[str] = Counter()
        shift_counter: Counter[str] = Counter()

        for c in c_list:
            rs_vals = rs_by_conv.get(c.id, [])
            all_rs.extend(rs_vals)

            c_turns = turns_by_conv.get(c.id, [])
            for t in c_turns:
                if t.topic:
                    topic_counts[t.topic] += 1

            shift = calculate_shift_label(c_turns)
            shift_counter[shift] += 1

        avg_rs = round(sum(all_rs) / len(all_rs), 3) if all_rs else 0.0
        high_count = sum(1 for v in all_rs if v >= high_threshold)
        share_high = round(high_count / len(all_rs), 3) if all_rs else 0.0
        top_topics = [t for t, _ in topic_counts.most_common(3)]

        kept_groups.append({
            "key": key,
            "n": n,
            "avg_rs": avg_rs,
            "share_high_resistance": share_high,
            "top_topics": top_topics,
            "shift_counts": {
                "softened": shift_counter["softened"],
                "hardened": shift_counter["hardened"],
                "unchanged": shift_counter["unchanged"],
            },
        })

    # Sort descending by avg_rs
    kept_groups.sort(key=lambda g: g["avg_rs"], reverse=True)

    return {
        "group_by": group_by,
        "total_conversations": len(conversations),
        "suppressed_groups": suppressed_count,
        "groups": kept_groups,
    }


@router.get("/resistance/timeseries")
def get_resistance_timeseries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_scheme_admin),
) -> dict[str, Any]:
    """Daily timeseries of average resistance score and conversation volume."""
    stmt_snaps = select(ResistanceSnapshot).order_by(ResistanceSnapshot.created_at.asc())
    snapshots = db.scalars(stmt_snaps).all()
    if not snapshots:
        return {"timeseries": []}

    daily_scores: dict[str, list[float]] = defaultdict(list)
    daily_convs: dict[str, set[int]] = defaultdict(set)

    for s in snapshots:
        d_str = s.created_at.strftime("%Y-%m-%d") if s.created_at else "2026-10-06"
        daily_scores[d_str].append(s.rs)
        daily_convs[d_str].add(s.conversation_id)

    timeseries = []
    for d_str in sorted(daily_scores.keys()):
        scores = daily_scores[d_str]
        timeseries.append({
            "date": d_str,
            "avg_rs": round(sum(scores) / len(scores), 3),
            "n_turns": len(scores),
            "n_conversations": len(daily_convs[d_str]),
        })

    return {"timeseries": timeseries}


@router.get("/resistance/map")
def get_resistance_map(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_scheme_admin),
) -> dict[str, Any]:
    """District coordinates and resistance intensity for GIS heatmap."""
    # Compute center coords by district
    centre_rows = db.execute(
        select(Centre.district, Centre.state, func.avg(Centre.lat), func.avg(Centre.lon))
        .where(Centre.lat.isnot(None), Centre.lon.isnot(None))
        .group_by(Centre.district, Centre.state)
    ).all()
    coords = {
        row[0]: {"state": row[1], "lat": float(row[2]), "lon": float(row[3])}
        for row in centre_rows
        if row[0]
    }

    # Compute district resistance
    conversations = db.scalars(select(Conversation)).all()
    student_ids = list({c.student_id for c in conversations})
    students = {}
    if student_ids:
        stmt_stu = select(Student).where(Student.id.in_(student_ids))
        students = {s.id: s for s in db.scalars(stmt_stu).all()}

    conv_ids = [c.id for c in conversations]
    stmt_snap = select(ResistanceSnapshot).where(ResistanceSnapshot.conversation_id.in_(conv_ids))
    snapshots = db.scalars(stmt_snap).all()
    rs_by_conv: dict[int, list[float]] = defaultdict(list)
    for s in snapshots:
        rs_by_conv[s.conversation_id].append(s.rs)

    district_convs: dict[str, list[int]] = defaultdict(list)
    district_state: dict[str, str] = {}
    for c in conversations:
        stu = students.get(c.student_id)
        if stu and stu.district:
            district_convs[stu.district].append(c.id)
            district_state[stu.district] = stu.state

    map_points = []
    suppressed_count = 0

    for dist, c_ids in district_convs.items():
        n = len(c_ids)
        if n < MIN_GROUP:
            suppressed_count += 1
            continue

        all_rs: list[float] = []
        for cid in c_ids:
            all_rs.extend(rs_by_conv.get(cid, []))

        avg_rs = round(sum(all_rs) / len(all_rs), 3) if all_rs else 0.0
        coord = coords.get(dist, {})
        lat = coord.get("lat", 26.8467)  # Fallback UP/central coord
        lon = coord.get("lon", 80.9462)
        st = coord.get("state") or district_state.get(dist, "Uttar Pradesh")

        map_points.append({
            "district": dist,
            "state": st,
            "lat": lat,
            "lon": lon,
            "avg_rs": avg_rs,
            "n": n,
            "is_suppressed": False,
        })

    return {
        "map_points": map_points,
        "suppressed_districts": suppressed_count,
    }


@router.get("/resistance/export.csv")
def export_resistance_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_scheme_admin),
) -> Response:
    """Download resistance analytics dataset as CSV."""
    conversations = db.scalars(select(Conversation).order_by(Conversation.id.asc())).all()
    student_ids = list({c.student_id for c in conversations})
    students = {}
    if student_ids:
        stmt_stu = select(Student).where(Student.id.in_(student_ids))
        students = {s.id: s for s in db.scalars(stmt_stu).all()}

    recs: list[Recommendation] = []
    if student_ids:
        stmt_rec = (
            select(Recommendation)
            .where(Recommendation.student_id.in_(student_ids), Recommendation.rank == 1)
        )
        recs = list(db.scalars(stmt_rec).all())
    occ_by_student = {r.student_id: r.occupation_id for r in recs}
    occ_ids = list(set(occ_by_student.values()))
    occs = {}
    if occ_ids:
        stmt_occ = select(Occupation).where(Occupation.id.in_(occ_ids))
        occs = {o.id: o.name_en for o in db.scalars(stmt_occ).all()}

    conv_ids = [c.id for c in conversations]
    snapshots: list[ResistanceSnapshot] = []
    if conv_ids:
        stmt_snap = select(ResistanceSnapshot).where(
            ResistanceSnapshot.conversation_id.in_(conv_ids)
        )
        snapshots = list(db.scalars(stmt_snap).all())
    rs_by_conv: dict[int, list[float]] = defaultdict(list)
    for s in snapshots:
        rs_by_conv[s.conversation_id].append(s.rs)

    turns: list[Turn] = []
    if conv_ids:
        stmt_turns = (
            select(Turn)
            .where(Turn.conversation_id.in_(conv_ids))
            .order_by(Turn.id.asc())
        )
        turns = list(db.scalars(stmt_turns).all())
    turns_by_conv: dict[int, list[Turn]] = defaultdict(list)
    for t in turns:
        turns_by_conv[t.conversation_id].append(t)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "conversation_id",
        "student_id",
        "district",
        "state",
        "trade",
        "shift_label",
        "avg_rs",
        "high_resistance",
        "created_at",
    ])

    for c in conversations:
        stu = students.get(c.student_id)
        dist = stu.district if stu else ""
        state = stu.state if stu else ""
        occ_id = occ_by_student.get(c.student_id)
        trade = occs.get(occ_id, "Vocational Trade") if occ_id else "Vocational Trade"

        c_turns = turns_by_conv.get(c.id, [])
        shift = calculate_shift_label(c_turns)

        rs_vals = rs_by_conv.get(c.id, [])
        avg_rs = round(sum(rs_vals) / len(rs_vals), 3) if rs_vals else 0.0
        high_res = "Yes" if avg_rs >= 0.60 else "No"
        c_at = c.created_at.isoformat() if c.created_at else ""

        writer.writerow([
            c.id,
            c.student_id,
            dist,
            state,
            trade,
            shift,
            avg_rs,
            high_res,
            c_at,
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resistance_export.csv"},
    )
