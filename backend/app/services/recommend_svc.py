"""Phase 3: Recommendation orchestration service.

filter -> retrieve -> rank -> explain -> persist. Owns the DB session and
derives the data-backed features (centre distance, local demand, salary
percentile) before handing off to the pure ML modules. Stores each result on the
`recommendations` table (occupation + course + reason codes + model version).
Retrieval degrades to no-op when the FAISS index isn't built yet.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.explain.reason_codes import generate_reason_codes
from app.ml.ranking.features import extract_features
from app.ml.ranking.filters import filter_courses
from app.ml.ranking.ranker import Ranker
from app.ml.retrieval.searcher import Searcher
from app.models import Assessment, Centre, Course, Market, Occupation, Recommendation, Student

logger = logging.getLogger(__name__)

_MAX_TOP_K = 10
# Coarse distance proxies (km) since students carry no coordinates; keyed on
# where the nearest offering centre sits relative to the student.
_DIST_HOME_DISTRICT = 10.0
_DIST_HOME_STATE = 120.0
_DIST_OTHER = 450.0


class RecommendService:
    def __init__(self, db: Session):
        self.db = db
        self.searcher = Searcher()
        self.ranker = Ranker()

    def get_recommendations(self, student_id: int, top_k: int = 3) -> dict:
        top_k = max(1, min(top_k, _MAX_TOP_K))
        student = self.db.get(Student, student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found.")

        assessment = self.db.scalar(
            select(Assessment)
            .where(Assessment.student_id == student_id)
            .order_by(Assessment.id.desc())
            .limit(1)
        )
        if not assessment:
            raise ValueError(f"Assessment not found for student {student_id}.")

        student_riasec = {
            "R": assessment.riasec_r, "I": assessment.riasec_i, "A": assessment.riasec_a,
            "S": assessment.riasec_s, "E": assessment.riasec_e, "C": assessment.riasec_c,
        }
        student_apt = {
            "num": assessment.apt_num, "verbal": assessment.apt_verbal,
            "spatial": assessment.apt_spatial, "mech": assessment.apt_mech,
        }

        courses = self.db.scalars(select(Course)).all()
        if not courses:
            return {"recommendations": [], "rejected": []}

        # Pre-load centre + market reference data once for the whole pass.
        centres_by_course = self._centres_by_course()
        markets_by_occ = self._markets_by_occ()

        # 1. Filter (hard constraints, incl reachability)
        eligible_courses, rejected_courses = filter_courses(student, courses, centres_by_course)

        # 2. Retrieve (semantic shortlist; empty when index not built)
        top_riasec = sorted(student_riasec, key=lambda k: student_riasec[k], reverse=True)[:3]
        retrieval_results = self.searcher.search(
            top_riasec=[f"{letter} ({_RIASEC_WORD[letter]})" for letter in top_riasec],
            aptitudes=list(student_apt.keys()),
            stated_interests="",
            top_k=50,
        )
        retrieval_map = dict(retrieval_results)

        # 3-4. Features + rank
        items_to_rank = []
        for course in eligible_courses:
            occupation = self.db.get(Occupation, course.occupation_id)
            if not occupation:
                continue
            features = extract_features(
                student, occupation, course, student_riasec, student_apt,
                retrieval_score=retrieval_map.get(occupation.id, 0.0),
                distance_km=_distance_km(student, course, centres_by_course.get(course.id, [])),
                local_demand_index=_local_demand(markets_by_occ.get(occupation.id, [])),
                salary_percentile=_salary_percentile(markets_by_occ.get(occupation.id, [])),
            )
            items_to_rank.append(
                {"course": course, "occupation": occupation, "features": features}
            )

        ranked_items = self.ranker.rank(items_to_rank)
        top_items = ranked_items[:top_k]

        # 5. Explain + persist
        lang = student.language or "en"
        final_recs = []
        for rank, item in enumerate(top_items, start=1):
            course, occupation = item["course"], item["occupation"]
            reasons = generate_reason_codes(
                student, occupation, course, item["features"], student_riasec, lang=lang
            )
            rec = Recommendation(
                student_id=student_id,
                occupation_id=occupation.id,
                course_id=course.id,
                rank=rank,
                score=item["score"],
                reasons_json=reasons,
                model_version=self.ranker.model_version,
            )
            self.db.add(rec)
            # Flush so ``rec.id`` is populated — the feedback loop (Phase 8)
            # rates a *stored* recommendation and needs its primary key.
            self.db.flush()
            final_recs.append({
                "id": rec.id,
                "rank": rank,
                "occupation_id": occupation.id,
                "occupation_name": occupation.name_en,
                "course_id": course.id,
                "course_name": course.name,
                "score": round(item["score"], 4),
                "reasons": reasons,
                "is_demo": bool(getattr(occupation, "is_demo", True)),
            })

        self.db.commit()

        rejected_summary = [
            {"course": r["course"].name, "course_id": r["course"].id, "reasons": r["reasons"]}
            for r in rejected_courses
        ]
        return {
            "recommendations": final_recs,
            "rejected": rejected_summary,
            "model_version": self.ranker.model_version,
        }

    # --- data access helpers --------------------------------------------------
    def _centres_by_course(self) -> dict[int, list[Centre]]:
        grouped: dict[int, list[Centre]] = {}
        for centre in self.db.scalars(select(Centre)).all():
            grouped.setdefault(centre.course_id, []).append(centre)
        return grouped

    def _markets_by_occ(self) -> dict[int, list[Market]]:
        grouped: dict[int, list[Market]] = {}
        for row in self.db.scalars(select(Market)).all():
            grouped.setdefault(row.occupation_id, []).append(row)
        return grouped


_RIASEC_WORD = {
    "R": "Realistic/hands-on", "I": "Investigative/analytical", "A": "Artistic/creative",
    "S": "Social/helping", "E": "Enterprising/leading", "C": "Conventional/organising",
}


def _distance_km(student: Student, course: Course, centres: list[Centre]) -> float | None:
    if not centres:
        return None
    if any(c.district == student.district for c in centres):
        return _DIST_HOME_DISTRICT
    if any(c.state == student.state for c in centres):
        return _DIST_HOME_STATE
    return _DIST_OTHER


def _local_demand(rows: list[Market]) -> float | None:
    vals = [r.demand_index for r in rows if r.demand_index is not None]
    if not vals:
        return None
    # demand_index is stored on a 0..100 scale; normalise to 0..1.
    return min(max(sum(vals) / len(vals) / 100.0, 0.0), 1.0)


def _salary_percentile(rows: list[Market]) -> float | None:
    salaries = [float(r.avg_salary_inr) for r in rows if r.avg_salary_inr is not None]
    if len(salaries) < 2:
        return None
    ordered = sorted(salaries)
    median = ordered[len(ordered) // 2]
    top = ordered[-1]
    if top <= 0:
        return None
    # Share of the field's ceiling salary — a coarse, honest proxy on demo data.
    return min(median / top, 1.0)
