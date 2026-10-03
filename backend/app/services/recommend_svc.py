"""Phase 3: Recommendation orchestration service."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.explain.reason_codes import generate_reason_codes
from app.ml.ranking.features import extract_features
from app.ml.ranking.filters import filter_courses
from app.ml.ranking.ranker import Ranker
from app.ml.retrieval.searcher import Searcher
from app.models.assessment import Assessment
from app.models.course import Course
from app.models.occupation import Occupation
from app.models.recommendation import Recommendation
from app.models.student import Student

logger = logging.getLogger(__name__)

class RecommendService:
    def __init__(self, db: Session):
        self.db = db
        self.searcher = Searcher()
        self.ranker = Ranker()

    def get_recommendations(self, student_id: int, top_k: int = 3) -> dict:
        student = self.db.get(Student, student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found.")

        # Get latest assessment
        assessment = self.db.scalar(
            select(Assessment)
            .where(Assessment.student_id == student_id)
            .order_by(Assessment.created_at.desc())
            .limit(1)
        )
        if not assessment:
            raise ValueError(f"Assessment not found for student {student_id}.")

        student_riasec = {
            "R": assessment.riasec_r,
            "I": assessment.riasec_i,
            "A": assessment.riasec_a,
            "S": assessment.riasec_s,
            "E": assessment.riasec_e,
            "C": assessment.riasec_c,
        }
        student_apt = {
            "num": assessment.apt_num,
            "verbal": assessment.apt_verbal,
            "spatial": assessment.apt_spatial,
            "mech": assessment.apt_mech,
        }

        courses = self.db.scalars(select(Course)).all()
        if not courses:
            return {"recommendations": [], "rejected": []}

        # 1. Filter
        eligible_courses, rejected_courses = filter_courses(student, courses)

        # 2. Retrieval (semantic search on occupations)
        # Getting top 3 RIASEC letters for query
        top_riasec = sorted(student_riasec.keys(), key=lambda k: student_riasec[k], reverse=True)[:3]
        retrieval_results = self.searcher.search(top_riasec=top_riasec, aptitudes=list(student_apt.keys()), stated_interests="", top_k=50)
        retrieval_map = {occ_id: score for occ_id, score in retrieval_results}

        # Gather occupations for eligible courses
        items_to_rank = []
        for course in eligible_courses:
            occupation = self.db.get(Occupation, course.occupation_id)
            if not occupation:
                continue

            ret_score = retrieval_map.get(occupation.id, 0.0)

            # 3. Features
            features = extract_features(student, occupation, course, student_riasec, student_apt, ret_score)
            
            items_to_rank.append({
                "course": course,
                "occupation": occupation,
                "features": features
            })

        # 4. Rank
        ranked_items = self.ranker.rank(items_to_rank)
        
        top_items = ranked_items[:top_k]
        
        # 5. Explain and Save
        final_recs = []
        for rank, item in enumerate(top_items, start=1):
            course = item["course"]
            occupation = item["occupation"]
            
            reasons = generate_reason_codes(student, occupation, course, item["features"], student_riasec)
            
            rec = Recommendation(
                student_id=student_id,
                course_id=course.id,
                rank=rank,
                score=item["score"],
                reasons_json=reasons
            )
            self.db.add(rec)
            
            final_recs.append({
                "rank": rank,
                "course_name": course.name,
                "occupation_name": occupation.name_en,
                "score": item["score"],
                "reasons": reasons
            })

        self.db.commit()

        # Just returning names of rejected courses for transparency
        rejected_summary = [{"course": r["course"].name, "reasons": r["reasons"]} for r in rejected_courses]

        return {
            "recommendations": final_recs,
            "rejected": rejected_summary
        }
