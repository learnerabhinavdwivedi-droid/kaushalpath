"""Phase 19 Data Foundation Tests.

Covers:
1. Grade policy table-test (12 distinct cases)
2. Alias resolution fixtures (10 Hindi, English, and typo variants of one trade)
3. Reject-path test (entity below 92 threshold and unknown geography)
4. Migration up/down test
5. No-source-no-row test (provenance enforcement)
"""
from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


import resolve_trades  # noqa: E402
from _common import check_provenance  # noqa: E402
from app.models.market import Market  # noqa: E402
from app.services import evidence_svc, geo_svc  # noqa: E402

# ---------------------------------------------------------------------------
# 1. GRADE POLICY TABLE-TEST (12 CASES)
# ---------------------------------------------------------------------------
GRADE_POLICY_CASES = [
    # (description, row_dict, current_year, expected_grade)
    (
        "Case 1: Official verified source, recent (age 1), large n -> Grade A",
        {"source": "onet_interests", "source_year": 2025, "is_demo": False, "n": 1000},
        2026,
        "A",
    ),
    (
        "Case 2: Official source, age > 3 years (age 5) -> drops one grade to Grade B",
        {"source": "onet_interests", "source_year": 2021, "is_demo": False, "n": 500},
        2026,
        "B",
    ),
    (
        "Case 3: Administrative tracer source, recent (age 2), n >= 30 -> Grade B",
        {"source": "dgt_strive", "source_year": 2024, "is_demo": False, "n": 150},
        2026,
        "B",
    ),
    (
        "Case 4: Administrative tracer source, age > 3 years (age 4) -> drops one grade to Grade C",
        {"source": "dgt_strive", "source_year": 2022, "is_demo": False, "n": 120},
        2026,
        "C",
    ),
    (
        "Case 5: Survey-modelled source (PLFS), recent (age 2), n >= 30 -> Grade C",
        {"source": "plfs_microdata", "source_year": 2024, "is_demo": False, "n": 80},
        2026,
        "C",
    ),
    (
        "Case 6: Survey-modelled source, age > 3 years (age 5) -> drops one grade to Grade D",
        {"source": "plfs_microdata", "source_year": 2021, "is_demo": False, "n": 60},
        2026,
        "D",
    ),
    (
        "Case 7: Any source marked is_demo=True -> always Grade D",
        {"source": "onet_interests", "source_year": 2026, "is_demo": True, "n": 1000},
        2026,
        "D",
    ),
    (
        "Case 8: Grade A source but small sample size n=15 (< 30) -> drops to Grade C",
        {"source": "ncvet_qp", "source_year": 2025, "is_demo": False, "n": 15},
        2026,
        "C",
    ),
    (
        "Case 9: Grade B source but small sample size n=20 (< 30) -> drops to Grade C",
        {"source": "dgt_strive", "source_year": 2025, "is_demo": False, "n": 20},
        2026,
        "C",
    ),
    (
        "Case 10: Explicitly declared grade A, recent -> Grade A",
        {
            "source": "custom_official",
            "evidence_grade": "A",
            "source_year": 2025,
            "is_demo": False,
            "n": 100,
        },
        2026,
        "A",
    ),
    (
        "Case 11: Explicitly declared grade B, age > 3 years -> drops to Grade C",
        {
            "source": "custom_tracer",
            "evidence_grade": "B",
            "source_year": 2020,
            "is_demo": False,
            "n": 100,
        },
        2026,
        "C",
    ),
    (
        "Case 12: Default unknown demo source without metadata -> Grade D",
        {"source": "demo_synth_2026", "is_demo": True},
        2026,
        "D",
    ),
]


@pytest.mark.parametrize("desc,row,year,expected", GRADE_POLICY_CASES)
def test_grade_for_table(desc: str, row: dict, year: int, expected: str) -> None:
    grade = evidence_svc.grade_for(row, current_year=year)
    assert grade == expected, f"Failed {desc}: expected {expected}, got {grade}"


def test_best_available_precedence_and_geo_fallback() -> None:
    # Precedence: Grade A beats Grade B even if Grade B is local
    rows = [
        {
            "id": 1,
            "source": "dgt_strive",
            "state": "Uttar Pradesh",
            "district": "Varanasi",
            "n": 100,
            "source_year": 2025,
            "is_demo": False,
        },  # Grade B local
        {
            "id": 2,
            "source": "onet_interests",
            "state": "National",
            "district": None,
            "n": 500,
            "source_year": 2025,
            "is_demo": False,
        },  # Grade A national
    ]
    learner_geo = {"state": "Uttar Pradesh", "district": "Varanasi"}
    chosen, level = evidence_svc.best_available(rows, learner_geo)
    assert chosen is not None
    assert chosen["id"] == 2
    assert level == "national"

    # Geo fallback within same grade: provider > district > state > national
    # Geo fallback within same grade: provider > district > state > national
    same_grade_rows = [
        {
            "id": 10,
            "source": "dgt_strive",
            "provider_id": 999,
            "state": "Uttar Pradesh",
            "district": "Varanasi",
            "n": 40,
            "source_year": 2025,
            "is_demo": False,
        },
        {
            "id": 11,
            "source": "dgt_strive",
            "provider_id": 111,
            "state": "Uttar Pradesh",
            "district": "Varanasi",
            "n": 50,
            "source_year": 2025,
            "is_demo": False,
        },
        {
            "id": 12,
            "source": "dgt_strive",
            "state": "Uttar Pradesh",
            "district": None,
            "n": 500,
            "source_year": 2025,
            "is_demo": False,
        },
        {
            "id": 13,
            "source": "dgt_strive",
            "state": "National",
            "district": None,
            "n": 1000,
            "source_year": 2025,
            "is_demo": False,
        },
    ]
    # Provider match
    res, lvl = evidence_svc.best_available(
        same_grade_rows,
        {"provider_id": 999, "district": "Varanasi", "state": "Uttar Pradesh"},
    )
    assert res["id"] == 10 and lvl == "provider"

    # District match when provider does not match
    res, lvl = evidence_svc.best_available(
        same_grade_rows,
        {"provider_id": 888, "district": "Varanasi", "state": "Uttar Pradesh"},
    )
    assert res["id"] == 10 and lvl == "district"

    # State match when district does not match
    res, lvl = evidence_svc.best_available(
        same_grade_rows,
        {"district": "Kanpur", "state": "Uttar Pradesh"},
    )
    assert res["id"] == 12 and lvl == "state"

    # National match when state does not match
    res, lvl = evidence_svc.best_available(
        same_grade_rows,
        {"district": "Jaipur", "state": "Rajasthan"},
    )
    assert res["id"] == 13 and lvl == "national"


def test_best_available_minimum_cell_size_fallback() -> None:
    # District row has n=15 (< 30) so it must NOT be chosen at district level;
    # falls back to state row with n=200
    rows = [
        {
            "id": 21,
            "source": "dgt_strive",
            "state": "Bihar",
            "district": "Patna",
            "n": 15,
            "source_year": 2025,
            "is_demo": False,
        },
        {
            "id": 22,
            "source": "dgt_strive",
            "state": "Bihar",
            "district": None,
            "n": 200,
            "source_year": 2025,
            "is_demo": False,
        },
    ]
    chosen, level = evidence_svc.best_available(rows, {"state": "Bihar", "district": "Patna"})
    assert chosen is not None
    assert chosen["id"] == 22
    assert level == "state"


def test_best_available_no_verified_data() -> None:
    # No rows pass minimum cell size gate
    rows = [
        {
            "id": 31,
            "source": "dgt_strive",
            "state": "Goa",
            "district": "Panaji",
            "n": 10,
            "source_year": 2025,
            "is_demo": False,
        },
    ]
    chosen, level = evidence_svc.best_available(rows, {"state": "Goa", "district": "Panaji"})
    assert chosen is None
    assert level == "no_verified_data"


# ---------------------------------------------------------------------------
# 2. ALIAS RESOLUTION FIXTURES (10 VARIANTS OF ONE TRADE)
# ---------------------------------------------------------------------------
TARGET_TRADE = {
    "trade_id": "TRD_0005",
    "name_en": "Electrician",
    "nco_code": "7411.0100",
    "qp_code": "QP_ELE_05",
    "ncvt_trade_code": "NCVT_005",
    "aliases": ["ITI Electrician", "इलेक्ट्रीशियन", "इलेक्ट्रिशियन"],
}

ALIAS_FIXTURES = [
    # (label, candidate_dict, expected_id, expected_method)
    ("1. Exact English", {"name_en": "Electrician"}, "TRD_0005", "name_match"),
    ("2. ITI prefix", {"name_en": "ITI Electrician"}, "TRD_0005", "name_match"),
    ("3. Roman numerals", {"name_en": "Electrician II"}, "TRD_0005", "name_match"),
    ("4. Case insensitive", {"name_en": "electrician"}, "TRD_0005", "name_match"),
    ("5. Exact Hindi", {"name_en": "इलेक्ट्रीशियन"}, "TRD_0005", "name_match"),
    ("6. Hindi phonetic variant", {"name_en": "इलेक्ट्रिशियन"}, "TRD_0005", "name_match"),
    ("7. Typo in English", {"name_en": "Electrican"}, "TRD_0005", "name_match"),
    ("8. Noise words added", {"name_en": "Electrician Trade General"}, "TRD_0005", "name_match"),
    (
        "9. NCVT code exact",
        {"ncvt_trade_code": "NCVT_005", "name_en": "Unknown Trade"},
        "TRD_0005",
        "official",
    ),
    (
        "10. QP code exact",
        {"qp_code": "QP_ELE_05", "name_en": "Unknown Trade"},
        "TRD_0005",
        "official",
    ),
]


@pytest.mark.parametrize("label,candidate,exp_id,exp_method", ALIAS_FIXTURES)
def test_trade_alias_resolution_fixtures(
    label: str, candidate: dict, exp_id: str, exp_method: str
) -> None:
    res = resolve_trades.resolve_candidate(candidate, [TARGET_TRADE], log_review=False)
    assert res is not None, f"Failed {label}: resolution returned None"
    assert res.matched_trade_id == exp_id, (
        f"Failed {label}: expected {exp_id}, got {res.matched_trade_id}"
    )
    assert res.method == exp_method, (
        f"Failed {label}: expected method {exp_method}, got {res.method}"
    )
    if res.method == "official":
        assert res.confidence >= 0.98
        assert not res.needs_review


# ---------------------------------------------------------------------------
# 3. REJECT-PATH TEST (ENTITY & GEOGRAPHY)
# ---------------------------------------------------------------------------
def test_entity_resolution_rejects_below_92() -> None:
    # Unrelated trade with similarity far below 92
    candidate = {"name_en": "Astronaut Aeronautical Spacecraft Pilot", "code": "ASTRO_99"}
    res = resolve_trades.resolve_candidate(candidate, [TARGET_TRADE], log_review=False)
    assert res is None, "Candidate below threshold 92 should NOT be loaded/resolved"


def test_geo_resolution_rejects_unknown() -> None:
    # Unknown state
    res_state = geo_svc.resolve_geo("Atlantis", "Metropolis")
    assert res_state is None

    # Known state but unknown district
    res_dist = geo_svc.resolve_geo("Uttar Pradesh", "Narnia District")
    assert res_dist is None

    # Verify reject logging
    rejects_path = geo_svc.GEO_REJECTS_FILE
    assert rejects_path.exists()
    content = rejects_path.read_text(encoding="utf-8")
    assert "Atlantis" in content or "Narnia" in content


# ---------------------------------------------------------------------------
# 4. MIGRATION UP / DOWN TEST
# ---------------------------------------------------------------------------
def test_alembic_migration_up_and_down() -> None:
    from alembic import command
    from alembic.config import Config

    backend_dir = pathlib.Path(__file__).resolve().parents[2]
    alembic_ini = backend_dir / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(backend_dir / "app" / "db" / "migrations"))

    # Test downgrade to cdbe195361f9
    command.downgrade(cfg, "cdbe195361f9")

    # Test upgrade back to head
    command.upgrade(cfg, "head")


# ---------------------------------------------------------------------------
# 5. NO-SOURCE-NO-ROW TEST
# ---------------------------------------------------------------------------
def test_provenance_enforcement_raises_on_missing_fields() -> None:
    # 1. Missing source raises ValueError
    with pytest.raises(ValueError, match="Missing required provenance field 'source'"):
        check_provenance(
            Market,
            {"occupation_id": 1},
            {"evidence_grade": "D", "retrieved_on": "2026-10-11"},
        )

    # 2. Missing evidence_grade raises ValueError
    with pytest.raises(
        ValueError, match="Missing or invalid required provenance field 'evidence_grade'"
    ):
        check_provenance(
            Market,
            {"occupation_id": 1},
            {"source": "test_src", "retrieved_on": "2026-10-11"},
        )

    # 3. Invalid evidence_grade raises ValueError
    with pytest.raises(
        ValueError, match="Missing or invalid required provenance field 'evidence_grade'"
    ):
        check_provenance(
            Market,
            {"occupation_id": 1},
            {"source": "test_src", "evidence_grade": "X", "retrieved_on": "2026-10-11"},
        )

    # 4. Missing retrieved_on raises ValueError
    with pytest.raises(ValueError, match="Missing required provenance field 'retrieved_on'"):
        check_provenance(
            Market,
            {"occupation_id": 1},
            {"source": "test_src", "evidence_grade": "D"},
        )

    # 5. Valid provenance passes without exception
    check_provenance(
        Market,
        {"occupation_id": 1},
        {"source": "test_src", "evidence_grade": "D", "retrieved_on": "2026-10-11"},
    )

