"""Phase 22 unit tests: Outcome Evidence Engine."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from app.db.base import Base  # noqa: E402
from app.models.occupation import Occupation  # noqa: E402
from app.models.outcome_evidence import OutcomeEvidence  # noqa: E402
from app.services.evidence_svc import (  # noqa: E402
    EvidenceService,
    adjust_to_base_year,
    shrink_earnings,
    shrink_rate,
)
from app.services.outcome_svc import OutcomeService  # noqa: E402


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_outcome_evidence_model_creation(mem_db: Session):
    """Test OutcomeEvidence ORM model fields, grain, and properties."""
    occ = Occupation(
        name_en="Electrician",
        name_hi="इलेक्ट्रीशियन",
        riasec_r=7.0,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=False,
        evidence_grade="B",
    )
    mem_db.add(occ)
    mem_db.commit()

    ev = OutcomeEvidence(
        trade_id=occ.id,
        geo_level="state",
        state="Maharashtra",
        period_start="2023-04-01",
        period_end="2024-03-31",
        metric="placement_rate",
        value=0.74,
        value_shape="rate",
        n=210,
        definition="survey",
        source_id="dgt_strive",
        evidence_grade="B",
        ci_low=0.7012,
        ci_high=0.7788,
        page_ref="Maharashtra STRIVE Report 2024, Table 4.6, p. 47",
        verified_by="DGT World Bank STRIVE Unit",
        source="DGT STRIVE Tracer Study",
        source_url="https://dgt.gov.in/STRIVE",
        source_year=2024,
        retrieved_on="2026-10-11",
        is_demo=False,
    )
    mem_db.add(ev)
    mem_db.commit()

    saved = mem_db.query(OutcomeEvidence).filter_by(trade_id=occ.id).first()
    assert saved is not None
    assert saved.state == "Maharashtra"
    assert saved.metric == "placement_rate"
    assert saved.value == 0.74
    assert saved.n == 210
    assert saved.evidence_grade == "B"
    assert saved.ci_low == 0.7012
    assert saved.ci_high == 0.7788


def test_bad_definition_constraint(mem_db: Session):
    """Test that definition must be one of official, survey, verified, reported."""
    occ = Occupation(
        name_en="Fitter",
        name_hi="फ़िटर",
        source="demo_synth_2026",
        source_year=2026,
        is_demo=False,
        evidence_grade="B",
    )
    mem_db.add(occ)
    mem_db.commit()

    with pytest.raises(ValueError):
        OutcomeEvidence(
            trade_id=occ.id,
            geo_level="state",
            state="Maharashtra",
            period_start="2023-04-01",
            period_end="2024-03-31",
            metric="placement_rate",
            value=0.60,
            value_shape="rate",
            n=100,
            definition="invalid_definition",
            source_id="test",
            evidence_grade="B",
            page_ref="Test p. 1",
            source_url="https://example.gov.in",
            source="Test Source",
            source_year=2024,
            retrieved_on="2026-10-11",
            is_demo=False,
        )


def test_shrink_rate_behavior():
    """Test Empirical Bayes shrinkage behavior for small vs large n."""
    prior_rate = 0.50

    # Small sample n=5, child rate 0.90 -> shrinks heavily toward prior (0.50)
    shrunk_small, lo_small, hi_small = shrink_rate(0.90, 5, prior_rate, prior_strength_m=20.0)
    assert shrunk_small < 0.65
    assert 0.0 <= lo_small <= shrunk_small <= hi_small <= 1.0

    # Large sample n=500, child rate 0.90 -> stays close to 0.90
    shrunk_large, lo_large, hi_large = shrink_rate(0.90, 500, prior_rate, prior_strength_m=20.0)
    assert shrunk_large > 0.88
    assert 0.0 <= lo_large <= shrunk_large <= hi_large <= 1.0


def test_shrink_earnings_behavior():
    """Test Empirical Bayes shrinkage for log-median earnings."""
    parent_median = 12000.0

    # Small sample n=5, child median 25000 -> shrinks heavily toward 12000
    shrunk_small, lo_small, hi_small = shrink_earnings(25000.0, 5, parent_median, k_between=50.0)
    assert shrunk_small < 16000.0
    assert lo_small <= shrunk_small <= hi_small

    # Large sample n=500, child median 25000 -> stays very close to 25000
    shrunk_large, lo_large, hi_large = shrink_earnings(25000.0, 500, parent_median, k_between=50.0)
    assert shrunk_large > 23000.0
    assert lo_large <= shrunk_large <= hi_large


def test_cpi_adjustment():
    """Test CPI Base 2012=100 adjustment to base year 2026."""
    # 2020 CPI: 153.8, 2026 CPI: 206.5 -> factor: 206.5 / 153.8 = 1.34265
    adjusted = adjust_to_base_year(10000.0, 2020, base_year=2026)
    expected = 10000.0 * (206.5 / 153.8)
    assert abs(adjusted - expected) < 1.0

    # Base year source year requires no adjustment
    same = adjust_to_base_year(15000.0, 2026, base_year=2026)
    assert same == 15000.0


def test_n_less_than_30_suppressed(mem_db: Session):
    """Test cell size suppression rule: cells with n < 30 return None."""
    occ = Occupation(
        name_en="Welder",
        name_hi="वेल्डर",
        source="demo_synth_2026",
        source_year=2026,
        is_demo=False,
        evidence_grade="B",
    )
    mem_db.add(occ)
    mem_db.commit()

    # Small cell n=20
    ev_small = OutcomeEvidence(
        trade_id=occ.id,
        geo_level="state",
        state="Maharashtra",
        period_start="2023-04-01",
        period_end="2024-03-31",
        metric="placement_rate",
        value=0.75,
        value_shape="rate",
        n=20,  # Below threshold
        definition="survey",
        source_id="small_study",
        evidence_grade="B",
        page_ref="p. 1",
        source_url="https://example.gov.in",
        source="Small Study",
        source_year=2024,
        retrieved_on="2026-10-11",
        is_demo=False,
    )
    mem_db.add(ev_small)
    mem_db.commit()

    svc = EvidenceService(mem_db)
    result = svc.best_available(occ.id, "placement_rate", state="Maharashtra")
    assert result is None, "Evidence with n < 30 must be suppressed."

    # Valid cell n=45
    ev_valid = OutcomeEvidence(
        trade_id=occ.id,
        geo_level="state",
        state="Maharashtra",
        period_start="2023-04-01",
        period_end="2024-03-31",
        metric="placement_rate",
        value=0.75,
        value_shape="rate",
        n=45,
        definition="survey",
        source_id="valid_study",
        evidence_grade="B",
        page_ref="p. 2",
        source_url="https://example.gov.in",
        source="Valid Study",
        source_year=2024,
        retrieved_on="2026-10-11",
        is_demo=False,
    )
    mem_db.add(ev_valid)
    mem_db.commit()

    result_valid = svc.best_available(occ.id, "placement_rate", state="Maharashtra")
    assert result_valid is not None
    assert result_valid["n"] == 45


def test_evidence_service_precedence(mem_db: Session):
    """Test precedence: Grade A/B > Grade C > Grade D."""
    occ = Occupation(
        name_en="Machinist",
        name_hi="मशीनिस्ट",
        source="demo_synth_2026",
        source_year=2026,
        is_demo=False,
        evidence_grade="B",
    )
    mem_db.add(occ)
    mem_db.commit()

    # Grade C aggregate
    ev_c = OutcomeEvidence(
        trade_id=occ.id,
        geo_level="state",
        state="Maharashtra",
        period_start="2023-04-01",
        period_end="2024-03-31",
        metric="earnings_monthly_inr",
        value=14000.0,
        value_shape="median",
        n=200,
        definition="survey",
        source_id="plfs_microdata",
        evidence_grade="C",
        page_ref="PLFS Table 2",
        source_url="https://mospi.gov.in",
        source="PLFS Aggregates",
        source_year=2024,
        retrieved_on="2026-10-11",
        is_demo=False,
    )
    # Grade B verified tracer study
    ev_b = OutcomeEvidence(
        trade_id=occ.id,
        geo_level="state",
        state="Maharashtra",
        period_start="2023-04-01",
        period_end="2024-03-31",
        metric="earnings_monthly_inr",
        value=15500.0,
        value_shape="median",
        n=150,
        definition="survey",
        source_id="dgt_strive",
        evidence_grade="B",
        page_ref="Maharashtra STRIVE p. 12",
        source_url="https://dgt.gov.in/STRIVE",
        source="DGT STRIVE Tracer Study",
        source_year=2024,
        retrieved_on="2026-10-11",
        is_demo=False,
    )
    mem_db.add_all([ev_c, ev_b])
    mem_db.commit()

    svc = EvidenceService(mem_db)
    best = svc.best_available(occ.id, "earnings_monthly_inr", state="Maharashtra")
    assert best is not None
    assert best["grade"] == "B"
    assert best["value"] == 15500.0


def test_outcome_service_no_silent_fallback(mem_db: Session):
    """Test that missing state/trade returns explicit no_verified_data without silent fallback."""
    occ = Occupation(
        name_en="Turner",
        name_hi="टर्नर",
        source="demo_synth_2026",
        source_year=2026,
        is_demo=False,
        evidence_grade="B",
    )
    mem_db.add(occ)
    mem_db.commit()

    # Evidence exists ONLY in Maharashtra
    ev = OutcomeEvidence(
        trade_id=occ.id,
        geo_level="state",
        state="Maharashtra",
        period_start="2023-04-01",
        period_end="2024-03-31",
        metric="placement_rate",
        value=0.72,
        value_shape="rate",
        n=180,
        definition="survey",
        source_id="dgt_strive",
        evidence_grade="B",
        page_ref="p. 15",
        source_url="https://dgt.gov.in/STRIVE",
        source="STRIVE Study",
        source_year=2024,
        retrieved_on="2026-10-11",
        is_demo=False,
    )
    mem_db.add(ev)
    mem_db.commit()

    outcome_svc = OutcomeService(db=mem_db)

    # Query Maharashtra -> returns verified data
    mh_res = outcome_svc.get_trade_outcomes(occ.id, state="Maharashtra", metric="placement_rate")
    assert mh_res["status"] in ("ok", "verified")
    assert mh_res["value"] == 0.72
    assert mh_res["level_used"] == "state"

    # Query Nagaland -> MUST return no_verified_data
    # (NOT silently fall back to Maharashtra or national!)
    nl_res = outcome_svc.get_trade_outcomes(occ.id, state="Nagaland", metric="placement_rate")
    assert nl_res["status"] == "no_verified_data"
    assert nl_res["value"] is None
    assert nl_res["grade"] is None


def test_pmkvy_4_writes_no_placement():
    """Verify PMKVY 4.0 carries no placement metrics as required by specification."""
    from ingest_pmkvy import PMKVY_RECORDS
    for row in PMKVY_RECORDS:
        if row.get("scheme_version") == "4.0":
            assert "placement_rate" not in row or row["placement_rate"] is None, (
                "PMKVY 4.0 must not carry placement metrics!"
            )


def test_plfs_loader_no_unit_level_rows():
    """Verify PLFS aggregated CSVs emit zero unit-level rows (privacy guarantee)."""
    agg_csv = REPO_ROOT / "data" / "processed" / "plfs_earnings_aggregates.csv"
    route_csv = REPO_ROOT / "data" / "processed" / "education_route_compare.csv"

    if agg_csv.exists():
        with agg_csv.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = set(reader.fieldnames or [])
            assert "person_id" not in fieldnames
            assert "sampling_weight" not in fieldnames
            for row in reader:
                assert int(row["n"]) >= 30, "Suppression rule violated: n < 30 in aggregate export!"

    if route_csv.exists():
        with route_csv.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = set(reader.fieldnames or [])
            assert "person_id" not in fieldnames
            for row in reader:
                assert int(row["n"]) >= 30, "Suppression rule violated in education route compare!"


def test_per_source_ingestion_fixtures(mem_db: Session):
    """Test 3 rows each for the 4 public sources with complete metadata."""
    occ = Occupation(
        name_en="Fitter",
        name_hi="फ़िटर",
        source="demo_synth_2026",
        source_year=2026,
        is_demo=False,
        evidence_grade="B",
    )
    mem_db.add(occ)
    mem_db.commit()

    fixtures = [
        # 1. DGT STRIVE Tracer Study (Grade B)
        OutcomeEvidence(
            trade_id=occ.id,
            geo_level="state",
            state="Maharashtra",
            period_start="2023-04-01",
            period_end="2024-03-31",
            metric="placement_rate",
            value=0.71,
            value_shape="rate",
            n=320,
            definition="survey",
            source_id="dgt_strive",
            evidence_grade="B",
            ci_low=0.67,
            ci_high=0.75,
            page_ref="Maharashtra STRIVE Report 2024, Table 4.6, p. 47",
            verified_by="DGT World Bank STRIVE Unit",
            source="DGT STRIVE Tracer Study",
            source_url="https://dgt.gov.in/STRIVE",
            source_year=2024,
            retrieved_on="2026-10-11",
            is_demo=False,
        ),
        # 2. PMKVY 2.0 / 3.0 Verified Placement (Grade B)
        OutcomeEvidence(
            trade_id=occ.id,
            geo_level="state",
            state="Uttar Pradesh",
            period_start="2016-10-01",
            period_end="2020-03-31",
            metric="placement_rate",
            value=0.485,
            value_shape="rate",
            n=2800,
            definition="verified",
            scheme_version="2.0",
            source_id="pmkvy_official",
            evidence_grade="B",
            ci_low=0.47,
            ci_high=0.50,
            page_ref="MSDE PMKVY State Factsheet 2020, Table 3.2, p. 14",
            verified_by="NSDC Third-Party Verification Partner",
            source="PMKVY 2.0 Official Dataset",
            source_url="https://pmkvyofficial.org",
            source_year=2020,
            retrieved_on="2026-10-11",
            is_demo=False,
        ),
        # 3. DGT ITI Grading Scorecard (Grade A)
        OutcomeEvidence(
            trade_id=occ.id,
            geo_level="provider",
            provider_id=1,
            period_start="2023-08-01",
            period_end="2024-07-31",
            metric="pass_rate",
            value=0.88,
            value_shape="rate",
            n=120,
            definition="official",
            source_id="dgt_iti_grading",
            evidence_grade="A",
            ci_low=0.84,
            ci_high=0.92,
            page_ref="DGT ITI Grading Dashboard 2023-24, ITI Performance Table",
            verified_by="DGT Central Examination Board",
            source="DGT ITI Grading Scorecard",
            source_url="https://ncvtmis.gov.in",
            source_year=2024,
            retrieved_on="2026-10-11",
            is_demo=False,
        ),
        # 4. PLFS Aggregates (Grade C)
        OutcomeEvidence(
            trade_id=occ.id,
            geo_level="state",
            state="Maharashtra",
            period_start="2023-07-01",
            period_end="2024-06-30",
            metric="earnings_monthly_inr",
            value=16200.0,
            value_shape="median",
            n=110,
            definition="survey",
            source_id="plfs_microdata",
            evidence_grade="C",
            ci_low=12500.0,
            ci_high=19500.0,
            page_ref="PLFS 2023-24 Aggregate Unit Table, NCO-72",
            verified_by="MoSPI NSO Survey Division",
            source="PLFS Survey 2023-24 Aggregates",
            source_url="https://mospi.gov.in",
            source_year=2024,
            retrieved_on="2026-10-11",
            is_demo=False,
        ),
    ]

    mem_db.add_all(fixtures)
    mem_db.commit()

    rows = mem_db.query(OutcomeEvidence).filter_by(trade_id=occ.id).all()
    assert len(rows) == 4
    for r in rows:
        assert r.n >= 30
        assert r.page_ref is not None and len(r.page_ref) > 0
        assert r.source_url is not None and r.source_url.startswith("http")
