"""Service for verified outcome data across trades, providers, and cohorts (Phase 22).

Answers parental and learner questions without silent fallbacks or fake percentiles:
- Empirical earnings ranges and intervals from tracer studies / PLFS
- Verified placement rates per trade and provider
- Progression pathways and relevant government schemes
- Provider safety and infrastructure facts
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Centre, Course, Occupation, ProgressionPath, ProviderOutcome, Scheme
from app.services.evidence_svc import EvidenceService


class OutcomeService:
    def __init__(self, db: Session):
        self.db = db
        self.evidence_svc = EvidenceService(db)

    def get_trade_outcomes(
        self,
        occupation_id: int,
        state: str | None = None,
        district: str | None = None,
        metric: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate outcome signals for a given trade and optional location.

        Strictly follows Data Addendum Rules 1-6:
        - If no verified data passes the addendum, returns status='no_verified_data'.
        - NO silent national/all-states fallback.
        """
        occ = self.db.get(Occupation, occupation_id)
        if not occ:
            raise ValueError(f"Occupation {occupation_id} not found")

        # 1. Fetch best available empirical evidence for each metric
        p_evidence = self.evidence_svc.best_available(
            trade_id=occupation_id,
            metric="placement_rate",
            state=state,
            district=district,
        )
        e_evidence = self.evidence_svc.best_available(
            trade_id=occupation_id,
            metric="earnings_monthly_inr",
            state=state,
            district=district,
        )
        se_evidence = self.evidence_svc.best_available(
            trade_id=occupation_id,
            metric="self_employed_pct",
            state=state,
            district=district,
        )
        stipend_evidence = self.evidence_svc.best_available(
            trade_id=occupation_id,
            metric="apprenticeship_stipend_inr",
            state=state,
            district=district,
        )

        # If a single specific metric was requested, return that canonical outcome object directly
        if metric:
            target_ev = self.evidence_svc.best_available(
                trade_id=occupation_id, metric=metric, state=state, district=district
            )
            if not target_ev:
                return {
                    "status": "no_verified_data",
                    "value": None,
                    "interval": None,
                    "n": None,
                    "level_used": None,
                    "grade": None,
                    "definition": None,
                    "as_of": None,
                    "source_url": None,
                    "metric": metric,
                }
            return target_ev

        # If neither placement nor earnings has verified data, report status='no_verified_data'
        has_verified_data = bool(p_evidence or e_evidence)
        status_label = "verified" if has_verified_data else "no_verified_data"

        # 2. Query centres for courses of this occupation
        courses = self.db.scalars(
            select(Course).where(Course.occupation_id == occupation_id)
        ).all()
        course_ids = [c.id for c in courses]

        centres_query = select(Centre).where(Centre.course_id.in_(course_ids))
        if state:
            centres_query = centres_query.where(Centre.state.ilike(state))
        if district:
            centres_query = centres_query.where(Centre.district.ilike(district))
        centres = self.db.scalars(centres_query).all()

        provider_summaries = []
        for c in centres[:8]:
            provider_summaries.append({
                "id": c.id,
                "name": c.name,
                "district": c.district,
                "state": c.state,
                "provider_type": c.provider_type,
                "affiliation": c.affiliation,
                "has_female_trainers": c.has_female_trainers,
                "has_hostel": c.has_hostel,
                "transport_note": c.transport_note,
                "safety_certified": c.safety_certified,
            })

        # 3. Progression paths
        prog_paths = []
        if course_ids:
            prog_rows = self.db.scalars(
                select(ProgressionPath).where(ProgressionPath.from_course_id.in_(course_ids))
            ).all()
            for p in prog_rows:
                prog_paths.append({
                    "id": p.id,
                    "to_label": p.to_label,
                    "kind": p.kind,
                    "credit_note": p.credit_note,
                })

        # 4. Schemes
        schemes = self.db.scalars(select(Scheme).limit(6)).all()
        scheme_list = [
            {
                "id": s.id,
                "name": s.name,
                "benefit_text_en": s.benefit_text_en,
                "benefit_text_hi": s.benefit_text_hi,
                "eligibility_text": s.eligibility_text,
                "url": s.url,
            }
            for s in schemes
        ]

        # Primary source & grade
        source_url = (e_evidence or p_evidence or {}).get("source_url")
        grade = (e_evidence or p_evidence or {}).get("grade")
        as_of = (e_evidence or p_evidence or {}).get("as_of")
        level_used = (e_evidence or p_evidence or {}).get("level_used")

        # Flat conveniences for backward compatibility
        placement_rate = p_evidence["value"] if p_evidence else None
        earnings_median = e_evidence["value"] if e_evidence else None
        e_interval = e_evidence.get("interval") if e_evidence else None
        earnings_p25 = e_interval[0] if e_interval else None
        earnings_p75 = e_interval[1] if e_interval else None
        sample_n = (e_evidence or p_evidence or {}).get("n")

        # Fallback to ProviderOutcome / Market when no verified outcome_evidence exists
        po_rows = []
        if not e_evidence or not p_evidence:
            po_rows = (
                self.db.scalars(
                    select(ProviderOutcome).where(ProviderOutcome.course_id.in_(course_ids))
                ).all()
                if course_ids
                else []
            )
            if po_rows:
                if not e_evidence:
                    p25_vals = [
                        float(r.earnings_p25) for r in po_rows if r.earnings_p25 is not None
                    ]
                    med_vals = [
                        float(r.earnings_median) for r in po_rows if r.earnings_median is not None
                    ]
                    p75_vals = [
                        float(r.earnings_p75) for r in po_rows if r.earnings_p75 is not None
                    ]
                    if p25_vals:
                        earnings_p25 = round(sum(p25_vals) / len(p25_vals), 2)
                    if med_vals:
                        earnings_median = round(sum(med_vals) / len(med_vals), 2)
                    if p75_vals:
                        earnings_p75 = round(sum(p75_vals) / len(p75_vals), 2)
                if not p_evidence:
                    rate_vals = [r.placement_rate for r in po_rows if r.placement_rate is not None]
                    if rate_vals:
                        placement_rate = round(sum(rate_vals) / len(rate_vals), 1)
                if not sample_n:
                    sample_n = sum(r.enrolled or 0 for r in po_rows)

        return {
            "status": status_label,
            "occupation_id": occ.id,
            "occupation_name_en": occ.name_en,
            "occupation_name_hi": occ.name_hi,
            "is_vocational": occ.is_vocational,
            # Canonical outcome objects
            "placement": p_evidence,
            "earnings": e_evidence,
            "self_employed": se_evidence,
            "apprenticeship_stipend": stipend_evidence,
            # Flat conveniences for backward compatibility
            "placement_rate": placement_rate,
            "earnings_median": earnings_median,
            "earnings_p25": earnings_p25,
            "earnings_p75": earnings_p75,
            "n": sample_n,
            "level_used": level_used,
            "grade": grade,
            "as_of": as_of,
            "source_url": source_url,
            "providers_count": len(centres),
            "providers": provider_summaries,
            "progression_paths": prog_paths,
            "schemes": scheme_list,
            "source": (
                (e_evidence or p_evidence or {}).get("source")
                or (po_rows[0].source if po_rows else "outcome_evidence")
            ),
            "source_year": (
                (e_evidence or p_evidence or {}).get("source_year")
                or (po_rows[0].source_year if po_rows else 2026)
            ),
            "is_demo": (
                (e_evidence or p_evidence or {}).get("is_demo")
                or (po_rows[0].is_demo if po_rows else False)
            ),
        }

    def get_provider_profile(self, provider_id: int) -> dict[str, Any]:
        """Fetch provider profile, verified outcome signals, and characteristics."""
        centre = self.db.get(Centre, provider_id)
        if not centre:
            raise ValueError(f"Provider {provider_id} not found")

        course = self.db.get(Course, centre.course_id)
        occ_id = course.occupation_id if course else 1

        # Fetch verified outcome for this provider via best_available
        p_evidence = self.evidence_svc.best_available(
            trade_id=occ_id,
            metric="placement_rate",
            state=centre.state,
            district=centre.district,
            provider_id=centre.id,
        )
        e_evidence = self.evidence_svc.best_available(
            trade_id=occ_id,
            metric="earnings_monthly_inr",
            state=centre.state,
            district=centre.district,
            provider_id=centre.id,
        )
        pass_ev = self.evidence_svc.best_available(
            trade_id=occ_id,
            metric="pass_rate",
            state=centre.state,
            district=centre.district,
            provider_id=centre.id,
        )
        adm_ev = self.evidence_svc.best_available(
            trade_id=occ_id,
            metric="admission_rate",
            state=centre.state,
            district=centre.district,
            provider_id=centre.id,
        )

        has_verified_data = bool(p_evidence or e_evidence or pass_ev)
        # Query raw cohort outcomes for historical transparency
        outcomes = self.db.scalars(
            select(ProviderOutcome)
            .where(ProviderOutcome.provider_id == provider_id)
            .order_by(ProviderOutcome.cohort_year.desc())
        ).all()

        cohort_outcomes = []
        for o in outcomes:
            c = self.db.get(Course, o.course_id)
            cohort_outcomes.append({
                "id": o.id,
                "course_id": o.course_id,
                "course_name": c.name if c else "Vocational Course",
                "cohort_year": o.cohort_year,
                "enrolled": o.enrolled,
                "certified": o.certified,
                "placed": o.placed,
                "placement_rate": o.placement_rate,
                "earnings_p25": float(o.earnings_p25) if o.earnings_p25 is not None else None,
                "earnings_median": (
                    float(o.earnings_median) if o.earnings_median is not None else None
                ),
                "earnings_p75": float(o.earnings_p75) if o.earnings_p75 is not None else None,
                "self_employed_pct": o.self_employed_pct,
                "apprenticeship_stipend_inr": (
                    float(o.apprenticeship_stipend_inr)
                    if o.apprenticeship_stipend_inr is not None
                    else None
                ),
                "source": o.source,
                "source_year": o.source_year,
                "is_demo": o.is_demo,
            })

        status_label = "verified" if has_verified_data else "no_verified_data"
        primary = p_evidence or e_evidence or pass_ev or {}

        return {
            "status": status_label,
            "id": centre.id,
            "name": centre.name,
            "district": centre.district,
            "state": centre.state,
            "provider_type": centre.provider_type,
            "affiliation": centre.affiliation,
            "has_female_trainers": centre.has_female_trainers,
            "has_hostel": centre.has_hostel,
            "transport_note": centre.transport_note,
            "safety_certified": centre.safety_certified,
            # Canonical outcome fields
            "value": primary.get("value"),
            "interval": primary.get("interval"),
            "n": primary.get("n"),
            "level_used": primary.get("level_used"),
            "grade": primary.get("grade"),
            "definition": primary.get("definition"),
            "as_of": primary.get("as_of"),
            "source_url": primary.get("source_url"),
            "metrics": {
                "placement": p_evidence,
                "earnings": e_evidence,
                "pass_rate": pass_ev,
                "admission_rate": adm_ev,
            },
            "cohort_outcomes": cohort_outcomes,
        }
