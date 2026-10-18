"""Integration tests for Phase 28: MSDE dummy-dataset ingestion drill.

Verifies that load_provided_dataset.py handles:
1. Variant 1: State DGT technical education extract (scrambled order, Hindi-transliterated headers, audit columns, fiscal years).
2. Variant 2: Sector Skill Council / CSR format (Annual CTC in Lakhs/LPA, DD/MM/YYYY dates, missing district).
3. Variant 3: PMKVY Special Projects format (decimal ratio metrics, ISO-8601 timestamps, apprentice stipends, GPS coords).
4. Full provenance contract: is_demo=False, source='msde_provided_2026', source_year=2026.
5. Live mapping.yaml overrides for arbitrary unseen schemas without code modifications.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from sqlalchemy.orm import Session

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_FIXTURES_DIR = _BACKEND_DIR / "tests" / "fixtures" / "msde_dummy_variants"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import load_provided_dataset  # noqa: E402

from app.models import Centre, Course, Market, Occupation, ProviderOutcome  # noqa: E402


def _seed_base_reference_records(db_session: Session) -> None:
    """Ensure baseline occupations and courses exist for provider linking."""
    trades = [
        ("Fitter", "फिटर"),
        ("Electrician", "इलेक्ट्रीशियन"),
        ("Welder", "वेल्डर"),
        ("Mechanic Motor Vehicle", "मैकेनिक मोटर व्हीकल"),
        ("Automotive Service Technician", "ऑटोमोटिव सर्विस तकनीशियन"),
        ("Domestic Data Entry Operator", "डाटा एंट्री ऑपरेटर"),
        ("CNC Operator Machining", "सीएनसी ऑपरेटर"),
        ("General Duty Assistant", "जनरल ड्यूटी असिस्टेंट"),
        ("Solar Panel Installation Technician", "सोलर पैनल तकनीशियन"),
        ("Handloom Weaver", "हथकरघा बुनकर"),
        ("Mason (Reinforced Concrete)", "राजमिस्त्री"),
    ]
    for name_en, name_hi in trades:
        occ = db_session.query(Occupation).filter_by(name_en=name_en).first()
        if not occ:
            occ = Occupation(
                name_en=name_en,
                name_hi=name_hi,
                is_vocational=True,
                source="demo_seed",
                is_demo=True,
            )
            db_session.add(occ)
            db_session.flush()

        course = db_session.query(Course).filter_by(name=name_en).first()
        if not course:
            course = Course(
                occupation_id=occ.id,
                name=name_en,
                nsqf_level=4,
                source="demo_seed",
                is_demo=True,
            )
            db_session.add(course)
    db_session.commit()


def test_variant_1_state_dgt_ingestion(tmp_path: Path, db_session: Session) -> None:
    """Variant 1: State DGT technical education extract.

    Tests:
    - Scrambled column order and Hindi-transliterated column headers.
    - FY date extraction ('2024-25' -> 2025).
    - Currency parsing with commas and '/mo' suffix ('₹26,500/mo' -> 26500.0, '28k INR' -> 28000.0).
    - Unmapped audit columns (s_no, nirikshan_adhikari, kaifiyat) logged, not crashing.
    - Rows land in Market table with is_demo=False and source='msde_provided_2026'.
    """
    _seed_base_reference_records(db_session)
    source_csv = _FIXTURES_DIR / "variant_1_state_dgt.csv"
    assert source_csv.exists(), f"Missing fixture: {source_csv}"

    # Copy to isolated directory
    stage_dir = tmp_path / "stage_var1"
    stage_dir.mkdir()
    target_csv = stage_dir / "state_dgt_extract.csv"
    target_csv.write_bytes(source_csv.read_bytes())

    res = load_provided_dataset.main(get_session=lambda: db_session, base_dir=stage_dir)
    assert res["loaded"] >= 4, f"Expected >= 4 loaded, got {res['loaded']}"
    assert res["rejected"] == 0, f"Expected 0 rejects, got {res['rejected']}"
    assert "s_no" in res["unmapped"]
    assert "nirikshan_adhikari" in res["unmapped"]
    assert "kaifiyat" in res["unmapped"]

    # Verify Market records
    fitter_market = db_session.query(Market).join(Occupation).filter(
        Occupation.name_en == "Fitter",
        Market.state == "Maharashtra",
        Market.source == "msde_provided_2026",
    ).first()
    assert fitter_market is not None
    assert fitter_market.avg_salary_inr == 26500.0
    assert fitter_market.placement_rate == 88.5
    assert fitter_market.year in (2024, 2025)
    assert fitter_market.is_demo is False

    elec_market = db_session.query(Market).join(Occupation).filter(
        Occupation.name_en == "Electrician",
        Market.state == "Maharashtra",
        Market.source == "msde_provided_2026",
    ).first()
    assert elec_market is not None
    assert elec_market.avg_salary_inr == 28000.0
    assert elec_market.placement_rate == 91.0
    assert elec_market.is_demo is False


def test_variant_2_ssc_annual_package_ingestion(tmp_path: Path, db_session: Session) -> None:
    """Variant 2: Sector Skill Council / Industry CSR format.

    Tests:
    - Annual CTC packages in Lakhs / LPA converted to monthly earnings (e.g. 3.6L/yr -> 30000/mo, 2.88 LPA -> 24000/mo).
    - Cohort dates in DD/MM/YYYY format ('15/07/2025' -> 2025).
    - Cohort counts (enrolled, certified, placed) correctly ingested.
    - Unexpected columns (ssc_partner_code, csr_sponsor_name, audit_status) logged as unmapped.
    - Rows land in ProviderOutcome and Centre tables with is_demo=False.
    """
    _seed_base_reference_records(db_session)
    source_csv = _FIXTURES_DIR / "variant_2_ssc_annual.csv"
    assert source_csv.exists(), f"Missing fixture: {source_csv}"

    stage_dir = tmp_path / "stage_var2"
    stage_dir.mkdir()
    target_csv = stage_dir / "ssc_csr_outcomes.csv"
    target_csv.write_bytes(source_csv.read_bytes())

    res = load_provided_dataset.main(get_session=lambda: db_session, base_dir=stage_dir)
    assert res["loaded"] >= 4
    assert res["rejected"] == 0
    assert "ssc_partner_code" in res["unmapped"]
    assert "csr_sponsor_name" in res["unmapped"]
    assert "audit_status" in res["unmapped"]

    # Verify ProviderOutcome records
    tvs_centre = db_session.query(Centre).filter(
        Centre.name == "TVS Technical Training Academy",
        Centre.source == "msde_provided_2026",
    ).first()
    assert tvs_centre is not None
    assert tvs_centre.is_demo is False

    tvs_po = db_session.query(ProviderOutcome).filter(
        ProviderOutcome.provider_id == tvs_centre.id,
        ProviderOutcome.source == "msde_provided_2026",
    ).first()
    assert tvs_po is not None
    # 3.6 Lakhs/year converted to monthly = 30000.0
    assert tvs_po.earnings_median == 30000.0
    assert tvs_po.cohort_year == 2025
    assert tvs_po.enrolled == 60
    assert tvs_po.certified == 55
    assert tvs_po.placed == 48
    assert tvs_po.is_demo is False

    # Check 2.88 LPA converted to monthly = 24000.0
    infosys_centre = db_session.query(Centre).filter(
        Centre.name == "Infosys BPM Skill Academy"
    ).first()
    assert infosys_centre is not None
    infosys_po = db_session.query(ProviderOutcome).filter(
        ProviderOutcome.provider_id == infosys_centre.id
    ).first()
    assert infosys_po.earnings_median == 24000.0


def test_variant_3_pmkvy_special_ratios_ingestion(tmp_path: Path, db_session: Session) -> None:
    """Variant 3: PMKVY Special Projects export.

    Tests:
    - Decimal ratios converted to 0..100 percentage (0.85 -> 85.0%, 0.10 -> 10.0%).
    - ISO-8601 timestamps ('2025-03-31T18:30:00Z' -> 2025).
    - Apprentice stipends parsed ('₹9,000' -> 9000.0).
    - Extra GPS and monitoring agency columns logged as unmapped.
    - Zero required columns left unmapped.
    """
    _seed_base_reference_records(db_session)
    source_csv = _FIXTURES_DIR / "variant_3_pmkvy_special.csv"
    assert source_csv.exists(), f"Missing fixture: {source_csv}"

    stage_dir = tmp_path / "stage_var3"
    stage_dir.mkdir()
    target_csv = stage_dir / "pmkvy_special_projects.csv"
    target_csv.write_bytes(source_csv.read_bytes())

    res = load_provided_dataset.main(get_session=lambda: db_session, base_dir=stage_dir)
    assert res["loaded"] >= 3
    assert res["rejected"] == 0
    assert "training_center_id" in res["unmapped"]
    assert "pass_rate_ratio" in res["unmapped"]
    assert "gps_latitude" in res["unmapped"]
    assert "gps_longitude" in res["unmapped"]
    assert "monitoring_agency" in res["unmapped"]

    # Verify Solar Technician outcome
    pratham = db_session.query(Centre).filter(
        Centre.name == "Pratham Institute of Vocational Education"
    ).first()
    assert pratham is not None
    assert pratham.district == "Aurangabad"
    assert pratham.state == "Maharashtra"
    assert pratham.is_demo is False

    pratham_po = db_session.query(ProviderOutcome).filter(
        ProviderOutcome.provider_id == pratham.id
    ).first()
    assert pratham_po is not None
    assert pratham_po.placement_rate == 85.0
    assert pratham_po.self_employed_pct == 10.0
    assert pratham_po.apprenticeship_stipend_inr == 9000.0
    assert pratham_po.cohort_year == 2025
    assert pratham_po.earnings_median == 18500.0
    assert pratham_po.is_demo is False


def test_provenance_contract_on_msde_provided_rows(tmp_path: Path, db_session: Session) -> None:
    """Every row ingested from MSDE-provided data MUST have is_demo=False and valid source."""
    _seed_base_reference_records(db_session)
    for variant in ["variant_1_state_dgt.csv", "variant_2_ssc_annual.csv", "variant_3_pmkvy_special.csv"]:
        stage_dir = tmp_path / f"stage_{variant}"
        stage_dir.mkdir()
        src = _FIXTURES_DIR / variant
        (stage_dir / variant).write_bytes(src.read_bytes())
        load_provided_dataset.main(get_session=lambda: db_session, base_dir=stage_dir)

    # Ingest a novel trade definition to exercise Occupation model as well
    stage_dir_occ = tmp_path / "stage_novel_occ"
    stage_dir_occ.mkdir()
    (stage_dir_occ / "novel_trade.csv").write_text("trade,state,avg_salary\nDrone Technician,Karnataka,32000\n", encoding="utf-8")
    load_provided_dataset.main(get_session=lambda: db_session, base_dir=stage_dir_occ)

    # Check contracts on all models touched by provided loader
    for model in [Market, ProviderOutcome, Centre, Occupation]:
        provided_rows = db_session.query(model).filter(
            model.source == "msde_provided_2026"
        ).all()
        assert len(provided_rows) > 0, f"Expected provided rows in {model.__tablename__}"
        for row in provided_rows:
            assert row.is_demo is False, f"Row {row.id} in {model.__tablename__} must have is_demo=False"
            assert row.source == "msde_provided_2026"


def test_custom_mapping_yaml_drill_no_code_change(tmp_path: Path, db_session: Session) -> None:
    """Eval Day Simulation: Given an unseen file with non-standard names, mapping.yaml alone resolves it."""
    _seed_base_reference_records(db_session)
    stage_dir = tmp_path / "stage_eval_day"
    stage_dir.mkdir()

    # Raw file with arbitrary non-standard columns
    unseen_csv = stage_dir / "unseen_eval_day_dataset.csv"
    with unseen_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["col_trade_key", "col_geography", "col_monthly_payout", "col_hiring_pct", "col_internal_code"],
        )
        writer.writeheader()
        writer.writerow({
            "col_trade_key": "Fitter",
            "col_geography": "Punjab",
            "col_monthly_payout": "27500",
            "col_hiring_pct": "89.0",
            "col_internal_code": "AUDIT-99",
        })

    # mapping.yaml provided on eval day without touching .py code
    mapping_yaml = stage_dir / "mapping.yaml"
    mapping_yaml.write_text(
        """
occupation_name_en:
  - col_trade_key
state:
  - col_geography
avg_salary_inr:
  - col_monthly_payout
placement_rate:
  - col_hiring_pct
""",
        encoding="utf-8",
    )

    res = load_provided_dataset.main(get_session=lambda: db_session, base_dir=stage_dir)
    assert res["loaded"] >= 1
    assert res["rejected"] == 0
    assert "col_internal_code" in res["unmapped"]

    punjab_market = db_session.query(Market).join(Occupation).filter(
        Occupation.name_en == "Fitter",
        Market.state == "Punjab",
        Market.source == "msde_provided_2026",
    ).first()
    assert punjab_market is not None
    assert punjab_market.avg_salary_inr == 27500.0
    assert punjab_market.placement_rate == 89.0
    assert punjab_market.is_demo is False
