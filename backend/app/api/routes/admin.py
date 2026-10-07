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
from app.models.human import Escalation
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


@router.get("/resistance/dashboard")
def get_resistance_dashboard(
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    state: str | None = Query(None),
    trade: str | None = Query(None),
    lang: str | None = Query(None),
    high_threshold: float = Query(0.60, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_scheme_admin),
) -> dict[str, Any]:
    """Scheme-administrator resistance dashboard (Phase 16).

    One filtered aggregation feeding KPI strip, district bubbles/table,
    concern x trade matrix, 30-day trend, shift distribution, per-concern
    phrases and a demo flag. Small groups (n < MIN_GROUP) are suppressed.
    Read-only; every existing Phase 13 endpoint is left untouched.
    """
    query = select(Conversation)
    if from_date:
        try:
            query = query.where(Conversation.created_at >= datetime.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            query = query.where(Conversation.created_at <= datetime.fromisoformat(to_date))
        except ValueError:
            pass
    if lang:
        query = query.where(Conversation.lang == lang)
    conversations = list(db.scalars(query).all())

    student_ids = list({c.student_id for c in conversations})
    students = (
        {s.id: s for s in db.scalars(select(Student).where(Student.id.in_(student_ids))).all()}
        if student_ids
        else {}
    )

    # Trade = the student's top (rank 1) recommended occupation name.
    occ_by_student: dict[int, int] = {}
    if student_ids:
        recs = db.scalars(
            select(Recommendation).where(
                Recommendation.student_id.in_(student_ids), Recommendation.rank == 1
            )
        ).all()
        occ_by_student = {r.student_id: r.occupation_id for r in recs}
    occ_ids = list(set(occ_by_student.values()))
    occ_name: dict[int, str] = {}
    occ_demo: dict[int, bool] = {}
    if occ_ids:
        for o in db.scalars(select(Occupation).where(Occupation.id.in_(occ_ids))).all():
            occ_name[o.id] = o.name_en
            occ_demo[o.id] = bool(o.is_demo)

    # Apply the state + trade post-filters (they live on joined rows).
    def _trade_of(cid_student: int) -> str:
        oid = occ_by_student.get(cid_student)
        return occ_name.get(oid, "General Vocational") if oid else "General Vocational"

    if state:
        conversations = [
            c for c in conversations
            if students.get(c.student_id) and students[c.student_id].state == state
        ]
    if trade:
        conversations = [c for c in conversations if _trade_of(c.student_id) == trade]

    conv_ids = [c.id for c in conversations]
    total = len(conv_ids)

    # Escalated conversations (any Escalation row pointing at a conversation).
    escalated_ids: set[int] = set()
    esc_reasons: list[tuple[int, str]] = []  # (conversation_id, reason)
    if conv_ids:
        esc_stmt = select(Escalation).where(Escalation.conversation_id.in_(conv_ids))
        for e in db.scalars(esc_stmt).all():
            if e.conversation_id is not None:
                escalated_ids.add(e.conversation_id)
                if e.reason:
                    esc_reasons.append((e.conversation_id, e.reason))

    # Resistance snapshots per conversation (also reused for the 30-day trend).
    rs_by_conv: dict[int, list[float]] = defaultdict(list)
    snapshots_all: list[ResistanceSnapshot] = []
    if conv_ids:
        snap_stmt = select(ResistanceSnapshot).where(
            ResistanceSnapshot.conversation_id.in_(conv_ids)
        )
        snapshots_all = list(db.scalars(snap_stmt).all())
        for s in snapshots_all:
            rs_by_conv[s.conversation_id].append(s.rs)

    # Turns per conversation (topics + sentiment ordering for shift).
    turns_by_conv: dict[int, list[Turn]] = defaultdict(list)
    if conv_ids:
        for t in db.scalars(
            select(Turn).where(Turn.conversation_id.in_(conv_ids)).order_by(Turn.id.asc())
        ).all():
            turns_by_conv[t.conversation_id].append(t)

    # District centre coords (avg lat/lon), same projection source as /map.
    centre_rows = db.execute(
        select(Centre.district, Centre.state, func.avg(Centre.lat), func.avg(Centre.lon))
        .where(Centre.lat.isnot(None), Centre.lon.isnot(None))
        .group_by(Centre.district, Centre.state)
    ).all()
    coords = {
        r[0]: {"state": r[1], "lat": float(r[2]), "lon": float(r[3])}
        for r in centre_rows if r[0]
    }

    # ---- Per-conversation derived facts ----
    def _primary_topic(c_id: int) -> str:
        topics = [t.topic for t in turns_by_conv.get(c_id, []) if t.topic]
        return Counter(topics).most_common(1)[0][0] if topics else "other"

    conv_meta: dict[int, dict[str, Any]] = {}
    shift_counter: Counter[str] = Counter()
    concern_counter: Counter[str] = Counter()
    trade_counter: Counter[str] = Counter()
    high_conv = 0
    for c in conversations:
        rs_vals = rs_by_conv.get(c.id, [])
        avg_rs = round(sum(rs_vals) / len(rs_vals), 3) if rs_vals else 0.0
        is_high = any(v >= high_threshold for v in rs_vals)
        if is_high:
            high_conv += 1
        shift = calculate_shift_label(turns_by_conv.get(c.id, []))
        shift_counter[shift] += 1
        ptopic = _primary_topic(c.id)
        concern_counter[ptopic] += 1
        tname = _trade_of(c.student_id)
        trade_counter[tname] += 1
        conv_meta[c.id] = {
            "student_id": c.student_id,
            "district": students[c.student_id].district if students.get(c.student_id) else None,
            "state": students[c.student_id].state if students.get(c.student_id) else None,
            "avg_rs": avg_rs,
            "rs_vals": rs_vals,
            "is_high": is_high,
            "shift": shift,
            "topic": ptopic,
            "trade": tname,
            "topics": [t.topic for t in turns_by_conv.get(c.id, []) if t.topic],
        }

    families_counselled = len({c.student_id for c in conversations})
    top_concern = concern_counter.most_common(1)[0][0] if concern_counter else ""

    # ---- District grouping (bubble map + table) ----
    district_convs: dict[str, list[int]] = defaultdict(list)
    for c_id, meta in conv_meta.items():
        if meta["district"]:
            district_convs[meta["district"]].append(c_id)

    districts: list[dict[str, Any]] = []
    suppressed_groups = 0
    for dist, ids in district_convs.items():
        n = len(ids)
        all_rs = [v for cid in ids for v in conv_meta[cid]["rs_vals"]]
        avg_rs = round(sum(all_rs) / len(all_rs), 3) if all_rs else 0.0
        share_high = round(sum(1 for cid in ids if conv_meta[cid]["is_high"]) / n, 3) if n else 0.0
        shift_c: Counter[str] = Counter(conv_meta[cid]["shift"] for cid in ids)
        topic_c: Counter[str] = Counter(conv_meta[cid]["topic"] for cid in ids)
        coord = coords.get(dist, {})
        is_supp = n < MIN_GROUP
        if is_supp:
            suppressed_groups += 1
        shift_dict = {
            "softened": shift_c["softened"],
            "hardened": shift_c["hardened"],
            "unchanged": shift_c["unchanged"],
        }
        districts.append({
            "district": dist,
            "state": coord.get("state") or (conv_meta[ids[0]]["state"] if ids else None),
            "lat": coord.get("lat", 26.8467),
            "lon": coord.get("lon", 80.9462),
            "n": n,
            "avg_rs": None if is_supp else avg_rs,
            "share_high": None if is_supp else share_high,
            "top_topics": [] if is_supp else [tp for tp, _ in topic_c.most_common(3)],
            "shift": shift_dict,
            "is_suppressed": is_supp,
        })
    districts.sort(key=lambda d: (d["avg_rs"] or 0.0), reverse=True)

    # ---- Concern x trade matrix (top 6 each, cells < MIN_GROUP suppressed) ----
    concerns = [tp for tp, _ in concern_counter.most_common(6)]
    trades = [tr for tr, _ in trade_counter.most_common(6)]
    suppressed_cells = 0
    cell_counts: dict[tuple[str, str], int] = Counter()
    for meta in conv_meta.values():
        if meta["topic"] in concerns and meta["trade"] in trades:
            cell_counts[(meta["topic"], meta["trade"])] += 1
    cells: list[list[Any]] = []
    for tp in concerns:
        row = []
        for tr in trades:
            cnt = cell_counts.get((tp, tr), 0)
            if 0 < cnt < MIN_GROUP:
                suppressed_cells += 1
                row.append(None)
            else:
                row.append(cnt)
        cells.append(row)

    # ---- Top anonymised phrases per concern ----
    phrase_by_topic: dict[str, Counter[str]] = defaultdict(Counter)
    for c_id, reason in esc_reasons:
        meta = conv_meta.get(c_id)
        if meta:
            phrase_by_topic[meta["topic"]][reason.strip()[:120]] += 1
    phrases = {
        tp: [p for p, _ in phrase_by_topic[tp].most_common(5)]
        for tp in concerns if phrase_by_topic.get(tp)
    }

    # ---- 30-day trend (from the snapshots already loaded above) ----
    daily: dict[str, list[float]] = defaultdict(list)
    daily_convs: dict[str, set[int]] = defaultdict(set)
    for s in snapshots_all:
        d_str = s.created_at.strftime("%Y-%m-%d") if s.created_at else ""
        if not d_str:
            continue
        daily[d_str].append(s.rs)
        daily_convs[d_str].add(s.conversation_id)
    trend = [
        {"date": d, "avg_rs": round(sum(v) / len(v), 3), "n_conversations": len(daily_convs[d])}
        for d, v in sorted(daily.items())
    ][-30:]

    is_demo = (
        any(occ_demo.get(oid, False) for oid in occ_by_student.values())
        or bool(conversations)
    )

    return {
        "filters": {"from": from_date, "to": to_date, "state": state, "trade": trade, "lang": lang},
        "kpis": {
            "families_counselled": families_counselled,
            "total_conversations": total,
            "pct_high_resistance": round(high_conv / total * 100, 1) if total else 0.0,
            "top_concern": top_concern,
            "escalation_rate": round(len(escalated_ids) / total * 100, 1) if total else 0.0,
            "sentiment_improved_pct": (
                round(shift_counter["softened"] / total * 100, 1) if total else 0.0
            ),
        },
        "districts": districts,
        "matrix": {
            "concerns": concerns,
            "trades": trades,
            "cells": cells,
            "suppressed_cells": suppressed_cells,
        },
        "phrases": phrases,
        "trend": trend,
        "shift": {
            "softened": shift_counter["softened"],
            "hardened": shift_counter["hardened"],
            "unchanged": shift_counter["unchanged"],
        },
        "suppressed_groups": suppressed_groups,
        "high_threshold": high_threshold,
        "is_demo": bool(is_demo),
    }
