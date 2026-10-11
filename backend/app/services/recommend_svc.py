"""Phase 23: Recommendation orchestration service (Recommender v2).

filter -> retrieve -> rank -> explain -> persist.
Features:
- aptitude_fit_occ: trade-grounded shortfall fit via Phase 21 IRT.
- interest_confidence: derived from SEM of learner's top RIASEC dimensions.
- earnings_median_pct & earnings_floor_pct: percentiles across eligible trades.
- placement_est & placement_conf: empirical Bayes shrunk placement signals.
- local_demand: state-level PLFS / PMKVY proxy.
- net_cost_ratio: net fee after scheme subsidy over budget limit.
- provider_quality: orders centres inside recommendation (does not rank courses).
- confidence & data_gaps: abstention & transparency signals.
- family_context: PLFS education route comparison association (never a promise).
"""
from __future__ import annotations

import csv
import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.budget import get_budget_limit
from app.ml.explain.reason_codes import generate_reason_codes
from app.ml.ranking.aptitude_fit import aptitude_match
from app.ml.ranking.features import extract_features
from app.ml.ranking.filters import filter_courses
from app.ml.ranking.ranker import Ranker
from app.ml.retrieval.searcher import Searcher
from app.models import (
    Assessment,
    Centre,
    Course,
    Market,
    Occupation,
    OccupationAbility,
    ProgressionPath,
    ProviderOutcome,
    Recommendation,
    Student,
)
from app.services.evidence_svc import EvidenceService
from app.services.geo_svc import match_district, match_state

logger = logging.getLogger(__name__)

_MAX_TOP_K = 10
_DIST_HOME_DISTRICT = 10.0
_DIST_HOME_STATE = 120.0
_DIST_OTHER = 450.0

_ROUTE_COMPARE_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "education_route_compare.csv"
)


@lru_cache(maxsize=1)
def _load_route_compare() -> list[dict[str, str]]:
    if not _ROUTE_COMPARE_PATH.exists():
        return []
    with open(_ROUTE_COMPARE_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _normalize_edu_for_compare(edu_level: str) -> str:
    edu = edu_level.lower()
    if "8" in edu or "below" in edu:
        return "below_10th"
    if "10" in edu:
        return "class_10th"
    if "12" in edu or "diploma" in edu or "iti" in edu:
        return "class_12th"
    if "grad" in edu:
        return "graduate"
    return "class_10th"


def _get_family_context(state: str, edu_level: str) -> dict[str, Any] | None:
    rows = _load_route_compare()
    if not rows:
        return None
    gen_edu = _normalize_edu_for_compare(edu_level)
    state_clean = state.strip().lower()

    # Find matching rows in student state, fallback to national / any state
    matched = [
        r for r in rows
        if r.get("state", "").strip().lower() == state_clean
        and r.get("general_education", "").strip().lower() == gen_edu
    ]
    if not matched:
        matched = [
            r for r in rows
            if r.get("general_education", "").strip().lower() == gen_edu
        ]
    if not matched:
        return None

    baseline = next(
        (r for r in matched if str(r.get("vocational_trained")).lower() in ("false", "0")),
        None,
    )
    vocational = next(
        (r for r in matched if str(r.get("vocational_trained")).lower() in ("true", "1")),
        None,
    )

    if not baseline or not vocational:
        return None

    try:
        base_med = float(baseline["median_earnings_inr"])
        voc_med = float(vocational["median_earnings_inr"])
        n_val = int(vocational["n"])
        return {
            "education_baseline": base_med,
            "vocational_route": voc_med,
            "difference_inr": round(voc_med - base_med, 2),
            "n": n_val,
            "grade": "C",
            "interpretation_note": (
                vocational.get("interpretation_note")
                or "Empirical association from PLFS survey data; not a causal effect or promise."
            ),
        }
    except (KeyError, ValueError):
        return None


def _scheme_subsidy_pct(income_band: str | None) -> float:
    if not income_band:
        return 0.0
    band = income_band.lower()
    if band in ("lt_1l", "<1l"):
        return 1.0  # 100% subsidy
    if band in ("1l_3l", "1l-3l"):
        return 0.5  # 50% subsidy
    if band in ("3l_6l", "3l-6l"):
        return 0.25  # 25% subsidy
    return 0.0


class RecommendService:
    def __init__(self, db: Session):
        self.db = db
        self.searcher = Searcher()
        self.ranker = Ranker()
        self.evidence_svc = EvidenceService(db)

    def get_recommendations(self, student_id: int, top_k: int = 3) -> dict[str, Any]:
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

        # Interest confidence derived from assessment ordering confidence / SEM
        raw_conf = float(assessment.confidence) if assessment.confidence is not None else 0.0
        if raw_conf <= 0.0 and assessment.state_json and isinstance(assessment.state_json, dict):
            raw_conf = float(assessment.state_json.get("confidence", 0.0))
        interest_confidence = max(0.1, min(1.0, raw_conf)) if raw_conf > 0 else 1.0

        # Learner standard errors if recorded
        learner_se: dict[str, float] | None = None
        if assessment.state_json and isinstance(assessment.state_json, dict):
            learner_se = assessment.state_json.get("aptitude_se")

        courses = self.db.scalars(select(Course)).all()
        if not courses:
            return {
                "recommendations": [],
                "rejected": [],
                "counsellor_suggested": False,
                "family_context": None,
                "model_version": self.ranker.model_version,
            }

        centres_by_course = self._centres_by_course()
        markets_by_occ = self._markets_by_occ()
        abilities_by_occ = self._abilities_by_occ()
        progression_by_course = self._progression_by_course()
        provider_outcomes_by_centre = self._provider_outcomes_by_centre()

        # 1. Filter (hard constraints, reachability, budget limits)
        eligible_courses, rejected_courses = filter_courses(student, courses, centres_by_course)

        # 2. Retrieve (candidate generation only: top-50 shortlist)
        top_riasec = sorted(student_riasec, key=lambda k: student_riasec[k], reverse=True)[:3]
        stated_interests = (
            getattr(student, "work_preference", "")
            or getattr(student, "stated_interests", "")
            or ""
        )
        retrieval_results = self.searcher.search(
            top_riasec=[f"{letter} ({_RIASEC_WORD[letter]})" for letter in top_riasec],
            aptitudes=list(student_apt.keys()),
            stated_interests=stated_interests,
            top_k=50,
        )
        candidate_courses = eligible_courses
        if retrieval_results:
            retrieved_occ_ids = {occ_id for occ_id, _ in retrieval_results}
            shortlisted = [c for c in eligible_courses if c.occupation_id in retrieved_occ_ids]
            other_eligible = [c for c in eligible_courses if c.occupation_id not in retrieved_occ_ids]
            candidate_courses = (shortlisted + other_eligible)[:50] if shortlisted else eligible_courses[:50]
        else:
            candidate_courses = eligible_courses[:50]

        # 3. Pre-fetch best available outcome evidence across eligible occupations
        # and compute trade-level percentiles
        unique_occ_ids = {c.occupation_id for c in candidate_courses}
        ev_earnings_map: dict[int, dict[str, Any] | None] = {}
        ev_placement_map: dict[int, dict[str, Any] | None] = {}

        for occ_id in unique_occ_ids:
            ev_earnings_map[occ_id] = self.evidence_svc.best_available(
                occ_id, "earnings_monthly_inr", state=student.state, district=student.district
            )
            ev_placement_map[occ_id] = self.evidence_svc.best_available(
                occ_id, "placement_rate", state=student.state, district=student.district
            )

        # Log medians and floors across eligible trades that have earnings
        trade_medians: dict[int, float] = {}
        trade_floors: dict[int, float] = {}
        for occ_id, ev in ev_earnings_map.items():
            if ev and ev.get("value") is not None:
                val = float(ev["value"])
                trade_medians[occ_id] = math.log(max(val, 1.0))
                interval = ev.get("interval")
                p25 = (
                    float(interval[0])
                    if (interval and len(interval) >= 1 and interval[0])
                    else (val * 0.85)
                )
                trade_floors[occ_id] = math.log(max(p25, 1.0))

        all_med_vals = list(trade_medians.values())
        all_floor_vals = list(trade_floors.values())

        # 4. Build items for ranking
        items_to_rank: list[dict[str, Any]] = []
        budget_limit = get_budget_limit(student.budget_band)
        subsidy_rate = _scheme_subsidy_pct(student.income_band)

        for course in candidate_courses:
            occupation = self.db.get(Occupation, course.occupation_id)
            if not occupation or not getattr(occupation, "is_vocational", True):
                continue
            occ_ability = abilities_by_occ.get(occupation.id)

            # Trade percentiles
            occ_id = occupation.id
            if occ_id in trade_medians and all_med_vals:
                m_val = trade_medians[occ_id]
                earnings_median_pct = round(
                    sum(1 for v in all_med_vals if v <= m_val) / len(all_med_vals), 4
                )
                f_val = trade_floors[occ_id]
                earnings_floor_pct = round(
                    sum(1 for v in all_floor_vals if v <= f_val) / len(all_floor_vals), 4
                )
            else:
                earnings_median_pct = None
                earnings_floor_pct = None

            # Placement estimates
            ev_pl = ev_placement_map.get(occ_id)
            if ev_pl and ev_pl.get("value") is not None:
                placement_est = float(ev_pl["value"])
                ci = ev_pl.get("interval")
                placement_conf = (
                    round(float(ci[1]) - float(ci[0]), 4)
                    if (ci and len(ci) == 2)
                    else 0.10
                )
            else:
                placement_est = None
                placement_conf = None

            # Net cost ratio
            fee = float(course.fee_inr or 0.0)
            net_fee = fee * (1.0 - subsidy_rate)
            if budget_limit == float("inf"):
                net_cost_ratio = 0.0
            elif budget_limit > 0:
                net_cost_ratio = net_fee / budget_limit
            else:
                net_cost_ratio = 1.0

            # Local demand proxy
            occ_markets = markets_by_occ.get(occ_id, [])
            local_demand = _local_demand(occ_markets, state=student.state)

            # Progression pathways count
            paths = progression_by_course.get(course.id, [])
            progression_value = float(len(paths))

            # Centre ordering (provider quality)
            course_centres = centres_by_course.get(course.id, [])
            ordered_centres = _order_centres_by_quality(
                student, course_centres, provider_outcomes_by_centre
            )

            # Distance
            dist_km = _distance_km(student, course, course_centres)

            # Aptitude match & shortfalls
            shortfalls = None
            if occ_ability is not None:
                r_num = getattr(occ_ability, "required_num", 0.0) or 0.0
                r_verbal = getattr(occ_ability, "required_verbal", 0.0) or 0.0
                r_spatial = getattr(occ_ability, "required_spatial", 0.0) or 0.0
                r_mech = getattr(occ_ability, "required_mech", 0.0) or 0.0
                occ_reqs = {
                    "num": float(r_num),
                    "verbal": float(r_verbal),
                    "spatial": float(r_spatial),
                    "mech": float(r_mech),
                }
                apt_res = aptitude_match(student_apt, learner_se, occ_reqs)
                shortfalls = apt_res.get("shortfalls")

            features = extract_features(
                student,
                occupation,
                course,
                student_riasec,
                student_apt,
                distance_km=dist_km,
                occupation_ability=occ_ability,
                placement_est=placement_est,
                placement_conf=placement_conf,
                earnings_median_pct=earnings_median_pct,
                earnings_floor_pct=earnings_floor_pct,
                local_demand=local_demand,
                net_cost_ratio=net_cost_ratio,
                progression_value=progression_value,
                learner_se=learner_se,
            )

            items_to_rank.append({
                "course": course,
                "occupation": occupation,
                "features": features,
                "occupation_ability": occ_ability,
                "ev_earnings": ev_earnings_map.get(occ_id),
                "ev_placement": ev_pl,
                "progression_paths": paths,
                "ordered_centres": ordered_centres,
                "shortfalls": shortfalls,
            })

        ranked_items = self.ranker.rank(items_to_rank, interest_confidence=interest_confidence)
        top_items = ranked_items[:top_k]

        # 5. Explain, assemble confidence & data_gaps, persist
        lang = student.language or "en"
        final_recs = []
        confidences = []

        for rank, item in enumerate(top_items, start=1):
            course, occupation = item["course"], item["occupation"]
            ev_e = item["ev_earnings"]
            ev_p = item["ev_placement"]

            reasons = generate_reason_codes(
                student,
                occupation,
                course,
                item["features"],
                student_riasec,
                lang=lang,
                occupation_ability=item.get("occupation_ability"),
                earnings_evidence=ev_e,
                placement_evidence=ev_p,
                progression_paths=item.get("progression_paths"),
                ordered_centres=item.get("ordered_centres"),
                shortfalls=item.get("shortfalls"),
            )

            # Recommendation confidence & data_gaps
            data_gaps: list[str] = []
            if ev_e:
                geo_used = ev_e.get("level_used", "state")
                grade = ev_e.get("grade", "B")
                if geo_used != "district":
                    data_gaps.append(
                        f"No verified earnings for this trade in your district; "
                        f"showing the {geo_used} figure, Grade {grade}."
                    )
            else:
                data_gaps.append(
                    "No verified earnings data available for this trade in your region."
                )

            if ev_p:
                geo_used_p = ev_p.get("level_used", "state")
                grade_p = ev_p.get("grade", "B")
                if geo_used_p != "district":
                    data_gaps.append(
                        f"No verified placement rate in your district; "
                        f"showing {geo_used_p} figure, Grade {grade_p}."
                    )
            else:
                data_gaps.append(
                    "No verified placement rate available for this trade in your region."
                )

            if item["features"].get("distance_km") is None:
                data_gaps.append("No verified training centre identified in your home district.")

            # Rule for item confidence
            has_high_ev = bool(
                ev_e
                and ev_e.get("grade") in ("A", "B")
                and (ev_e.get("n") or 0) >= 30
            )
            if interest_confidence >= 0.75 and has_high_ev:
                item_confidence = "high"
            elif interest_confidence < 0.60 or (not ev_e and not ev_p):
                item_confidence = "low"
            else:
                item_confidence = "medium"

            confidences.append(item_confidence)

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
            self.db.flush()

            final_recs.append({
                "id": rec.id,
                "rank": rank,
                "occupation_id": occupation.id,
                "occupation_name": occupation.name_en,
                "course_id": course.id,
                "course_name": course.name,
                "score": round(item["score"], 4),
                "confidence": item_confidence,
                "data_gaps": data_gaps,
                "has_data": item["features"].get("has_data", {}),
                "reasons": reasons,
                "ordered_centres": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "district": c.district,
                        "state": c.state,
                    }
                    for c in item.get("ordered_centres", [])[:3]
                ],
                "is_demo": bool(getattr(occupation, "is_demo", True)),
            })

        self.db.commit()

        # Step 5: If all top-3 are low confidence, suggest counsellor & escalate
        counsellor_suggested = False
        top_confidences = confidences[:3]
        if top_confidences and all(c == "low" for c in top_confidences):
            counsellor_suggested = True
            try:
                from app.services.escalation_svc import create_escalation
                create_escalation(
                    self.db,
                    student_id=student.id,
                    raised_by_user_id=student.user_id,
                    reason="low_recommendation_confidence",
                    priority="normal",
                )
            except Exception as exc:
                logger.warning("Could not auto-create escalation on low confidence: %s", exc)

        # Step 7: Family context association
        family_context = _get_family_context(student.state, student.edu_level)

        rejected_summary = [
            {"course": r["course"].name, "course_id": r["course"].id, "reasons": r["reasons"]}
            for r in rejected_courses
        ]
        return {
            "recommendations": final_recs,
            "rejected": rejected_summary,
            "counsellor_suggested": counsellor_suggested,
            "family_context": family_context,
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

    def _abilities_by_occ(self) -> dict[int, OccupationAbility]:
        grouped: dict[int, OccupationAbility] = {}
        for row in self.db.scalars(select(OccupationAbility)).all():
            grouped[row.occupation_id] = row
        return grouped

    def _progression_by_course(self) -> dict[int, list[ProgressionPath]]:
        grouped: dict[int, list[ProgressionPath]] = {}
        for row in self.db.scalars(select(ProgressionPath)).all():
            cid = getattr(row, "from_course_id", None)
            if cid is not None:
                grouped.setdefault(cid, []).append(row)
        return grouped

    def _provider_outcomes_by_centre(self) -> dict[int, list[ProviderOutcome]]:
        grouped: dict[int, list[ProviderOutcome]] = {}
        for row in self.db.scalars(select(ProviderOutcome)).all():
            pid = getattr(row, "provider_id", None)
            if pid is not None:
                grouped.setdefault(pid, []).append(row)
        return grouped


_RIASEC_WORD = {
    "R": "Realistic/hands-on", "I": "Investigative/analytical", "A": "Artistic/creative",
    "S": "Social/helping", "E": "Enterprising/leading", "C": "Conventional/organising",
}


def _distance_km(student: Student, course: Course, centres: list[Centre]) -> float | None:
    if not centres:
        return None
    if any(match_district(student.district, c.district, student.state) for c in centres):
        return _DIST_HOME_DISTRICT
    if any(match_state(student.state, c.state) for c in centres):
        return _DIST_HOME_STATE
    return _DIST_OTHER


def _local_demand(rows: list[Market], state: str | None = None) -> float | None:
    if not rows:
        return None
    target_rows = rows
    if state:
        state_rows = [r for r in rows if r.state and match_state(state, r.state)]
        if state_rows:
            target_rows = state_rows

    demands = [r.demand_index for r in target_rows if r.demand_index is not None]
    placements = [r.placement_rate for r in target_rows if r.placement_rate is not None]

    parts: list[float] = []
    if demands:
        parts.append(min(max(sum(demands) / len(demands) / 100.0, 0.0), 1.0))
    if placements:
        mean_p = sum(placements) / len(placements)
        parts.append(min(max(mean_p / 100.0 if mean_p > 1.0 else mean_p, 0.0), 1.0))

    if not parts:
        return None
    return round(sum(parts) / len(parts), 4)


def _order_centres_by_quality(
    student: Student,
    centres: list[Centre],
    outcomes_by_centre: dict[int, list[ProviderOutcome]],
) -> list[Centre]:
    """Order centres inside recommendation: distance -> outcome n >= 30 -> scorecard."""
    if not centres:
        return []

    def _sort_key(c: Centre) -> tuple[int, int, float]:
        # 1. Distance tier: home district (0) -> home state (1) -> other (2)
        if match_district(student.district, c.district, student.state):
            dist_tier = 0
        elif match_state(student.state, c.state):
            dist_tier = 1
        else:
            dist_tier = 2

        # 2. Outcome sample size tier (n >= 30 gets 0, else 1)
        c_outcomes = outcomes_by_centre.get(c.id, [])
        has_adequate_n = any((o.enrolled or 0) >= 30 for o in c_outcomes)
        n_tier = 0 if has_adequate_n else 1

        # 3. Scorecard / placement rate (higher is better -> negative)
        placement_rates = [o.placement_rate for o in c_outcomes if o.placement_rate is not None]
        rate_val = -(max(placement_rates) if placement_rates else 0.0)

        return (dist_tier, n_tier, rate_val)

    return sorted(centres, key=_sort_key)
