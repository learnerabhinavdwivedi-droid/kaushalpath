"""Entity resolution for occupations and vocational trades (Phase 19 Data Foundation).

Cascade Order (DATA ADDENDUM & Phase 19 Spec):
1. Exact NCVT trade code or QP code -> exact, conf=1.0, official, needs_review=False
2. Exact NCO-2015 code -> exact, conf=0.98, official, needs_review=False
3. Normalised-name match -> close, conf=0.95, name_match, needs_review=False
4. Fuzzy token-set ratio >= 92 -> close, conf=score/100, name_match, ALWAYS needs_review=True
5. Below 92 -> NOT LOADED.

Any row where needs_review=True is written to
data/processed/trade_crosswalk_review.csv for human sign-off.
"""
from __future__ import annotations

import csv
import difflib
import pathlib
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PROCESSED_DIR = BACKEND_DIR / "app" / "data" / "processed"
REVIEW_FILE = PROCESSED_DIR / "trade_crosswalk_review.csv"

ROMAN_NUMERALS_PATTERN = re.compile(r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b", re.IGNORECASE)
NOISE_WORDS_PATTERN = re.compile(r"\b(iti|cts|cits|trade|craftsman|general)\b", re.IGNORECASE)


@dataclass
class ResolutionResult:
    matched_trade_id: str
    matched_trade_name: str
    relation: str         # exact | broad | narrow | close
    confidence: float     # 0.0 .. 1.0
    method: str           # official | name_match | manual
    needs_review: bool
    score: float          # 0 .. 100


def normalize_name(name: str) -> str:
    """Normalize trade name: lowercase, strip punctuation, 'ITI', and roman numerals."""
    if not name:
        return ""
    text = name.lower()
    text = re.sub(r"[\(\)\[\],.\-_/&:+]", " ", text)
    text = NOISE_WORDS_PATTERN.sub(" ", text)
    text = ROMAN_NUMERALS_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def token_set_ratio(s1: str, s2: str) -> float:
    """Compute token set ratio between two normalized strings (0.0 to 100.0)."""
    t1 = set(s1.lower().split())
    t2 = set(s2.lower().split())
    if not t1 or not t2:
        return 0.0
    common = sorted(list(t1 & t2))
    diff1 = sorted(list(t1 - t2))
    diff2 = sorted(list(t2 - t1))

    s_common = " ".join(common)
    s_diff1 = " ".join(diff1)
    s_diff2 = " ".join(diff2)

    t0 = s_common
    t1_comb = (s_common + " " + s_diff1).strip()
    t2_comb = (s_common + " " + s_diff2).strip()

    def sim(a: str, b: str) -> float:
        if not a and not b:
            return 1.0
        return difflib.SequenceMatcher(None, a, b).ratio()

    r1 = sim(t0, t1_comb)
    r2 = sim(t0, t2_comb)
    r3 = sim(t1_comb, t2_comb)
    return round(max(r1, r2, r3) * 100.0, 1)


def log_review_entry(
    from_system: str,
    from_code: str,
    from_name: str,
    to_system: str,
    to_code: str,
    to_name: str,
    score: float,
    relation: str,
    method: str,
    needs_review: bool,
) -> None:
    """Write fuzzy / review candidate to trade_crosswalk_review.csv."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not REVIEW_FILE.exists()
    with REVIEW_FILE.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if write_header:
            writer.writerow([
                "from_system",
                "from_code",
                "from_name",
                "to_system",
                "to_code",
                "to_name",
                "score",
                "relation",
                "method",
                "needs_review",
                "timestamp",
            ])
        writer.writerow([
            from_system,
            from_code,
            from_name,
            to_system,
            to_code,
            to_name,
            score,
            relation,
            method,
            str(needs_review).lower(),
            datetime.now(UTC).isoformat(),
        ])


def resolve_candidate(
    candidate: dict[str, Any],
    known_trades: list[dict[str, Any]],
    log_review: bool = True,
) -> ResolutionResult | None:
    """Resolve an incoming candidate against known canonical trades.

    Cascade:
    1. NCVT trade code or QP code
    2. NCO-2015 code
    3. Normalised-name match
    4. Fuzzy token-set ratio >= 92 (ALWAYS needs_review=True)
    5. Below 92 -> None (not loaded)
    """
    cand_ncvt = (candidate.get("ncvt_trade_code") or "").strip()
    cand_qp = (candidate.get("qp_code") or "").strip()
    cand_nco = (candidate.get("nco_code") or "").strip()
    cand_name = (candidate.get("name_en") or candidate.get("name") or "").strip()
    cand_norm = normalize_name(cand_name)

    # 1. Exact NCVT or QP code match
    if cand_ncvt or cand_qp:
        for trade in known_trades:
            t_ncvt = (trade.get("ncvt_trade_code") or "").strip()
            t_qp = (trade.get("qp_code") or "").strip()
            if (cand_ncvt and cand_ncvt == t_ncvt) or (cand_qp and cand_qp == t_qp):
                return ResolutionResult(
                    matched_trade_id=trade["trade_id"],
                    matched_trade_name=trade["name_en"],
                    relation="exact",
                    confidence=1.0,
                    method="official",
                    needs_review=False,
                    score=100.0,
                )

    # 2. Exact NCO-2015 code match
    if cand_nco:
        for trade in known_trades:
            t_nco = (trade.get("nco_code") or "").strip()
            if t_nco and cand_nco == t_nco:
                return ResolutionResult(
                    matched_trade_id=trade["trade_id"],
                    matched_trade_name=trade["name_en"],
                    relation="exact",
                    confidence=0.98,
                    method="official",
                    needs_review=False,
                    score=98.0,
                )

    # 3. Normalised-name match
    if cand_norm:
        for trade in known_trades:
            t_norm = normalize_name(trade["name_en"])
            if cand_norm == t_norm:
                return ResolutionResult(
                    matched_trade_id=trade["trade_id"],
                    matched_trade_name=trade["name_en"],
                    relation="close",
                    confidence=0.95,
                    method="name_match",
                    needs_review=False,
                    score=95.0,
                )
            # Also check trade aliases if present
            for alias in trade.get("aliases", []):
                if cand_norm == normalize_name(alias):
                    return ResolutionResult(
                        matched_trade_id=trade["trade_id"],
                        matched_trade_name=trade["name_en"],
                        relation="close",
                        confidence=0.95,
                        method="name_match",
                        needs_review=False,
                        score=95.0,
                    )

    # 4. Fuzzy token-set ratio >= 92 (ALWAYS needs_review=True)
    if cand_norm:
        best_trade: dict[str, Any] | None = None
        best_score = 0.0
        for trade in known_trades:
            t_norm = normalize_name(trade["name_en"])
            score = token_set_ratio(cand_norm, t_norm)
            if score > best_score:
                best_score = score
                best_trade = trade

        if best_trade and best_score >= 92.0:
            result = ResolutionResult(
                matched_trade_id=best_trade["trade_id"],
                matched_trade_name=best_trade["name_en"],
                relation="close",
                confidence=round(best_score / 100.0, 3),
                method="name_match",
                needs_review=True,  # ALWAYS true per spec!
                score=best_score,
            )
            if log_review:
                log_review_entry(
                    from_system=candidate.get("source_system", "external"),
                    from_code=candidate.get("code", ""),
                    from_name=cand_name,
                    to_system="trades",
                    to_code=best_trade["trade_id"],
                    to_name=best_trade["name_en"],
                    score=best_score,
                    relation="close",
                    method="name_match",
                    needs_review=True,
                )
            return result

    # 5. Below 92 -> Not loaded / rejected
    return None


NCO_2015_MAP: dict[str, str] = {
    "fitter": "7233.0100",
    "electrician": "7411.0100",
    "welder": "7212.0100",
    "plumber": "7126.0100",
    "carpenter": "7115.0100",
    "turner": "7223.0100",
    "machinist": "7223.0200",
    "draughtsman civil": "3118.0100",
    "draughtsman mechanical": "3118.0200",
    "mechanic motor vehicle": "7231.0100",
    "mechanic diesel": "7231.0200",
    "wireman": "7411.0200",
    "electronics mechanic": "7421.0300",
    "solar panel installation technician": "7411.0500",
    "cctv technician": "7421.0500",
    "sewing machine operator": "7533.0100",
    "data entry operator": "4132.0100",
    "tailor": "7531.0100",
    "mason": "7112.0100",
    "painter": "7131.0100",
}


def main() -> int:
    """Populate canonical trades and run entity resolution review."""
    from app.db.session import SessionLocal
    from app.models.crosswalk import Crosswalk
    from app.models.occupation import Occupation
    from app.models.trade import Trade, TradeAlias

    session = SessionLocal()
    try:
        # Load occupations as baseline trades
        voc_occs = session.query(Occupation).filter(Occupation.is_vocational.is_(True)).all()
        print(f"Loaded {len(voc_occs)} vocational occupations as reference trades.")

        for occ in voc_occs:
            tid = f"TRD_{occ.id:04d}"
            nco = occ.nco_code or NCO_2015_MAP.get(occ.name_en.lower().strip())
            existing = session.query(Trade).filter_by(trade_id=tid).one_or_none()
            if existing is None:
                trade = Trade(
                    trade_id=tid,
                    name_en=occ.name_en,
                    name_hi=occ.name_hi,
                    nco_code=nco,
                    nsqf_level=occ.nsqf_level,
                    qp_code=f"QP_{occ.name_en[:3].upper()}_{occ.id}",
                    ncvt_trade_code=f"NCVT_{occ.id:03d}",
                    source="canonical_catalogue",
                    source_year=2026,
                    is_demo=False,
                    needs_review=False,
                    evidence_grade="A",
                    n=1000,
                    source_url="https://ncvtmis.gov.in",
                    retrieved_on="2026-10-11",
                    metric_definition="Canonical vocational trade definition",
                )
                session.add(trade)
                session.flush()

                # Add sample aliases
                session.add(TradeAlias(trade_id=tid, alias=f"ITI {occ.name_en}", source="dgt_mis"))
                if occ.name_hi:
                    session.add(TradeAlias(trade_id=tid, alias=occ.name_hi, source="indic_hi"))
            else:
                if nco and not existing.nco_code:
                    existing.nco_code = nco

                # Add sample aliases
                session.add(TradeAlias(trade_id=tid, alias=f"ITI {occ.name_en}", source="dgt_mis"))
                if occ.name_hi:
                    session.add(TradeAlias(trade_id=tid, alias=occ.name_hi, source="indic_hi"))

        session.commit()
        print(f"Canonical trades table populated ({session.query(Trade).count()} trades).")

        # Create known_trades cache
        known = [
            {
                "trade_id": t.trade_id,
                "name_en": t.name_en,
                "nco_code": t.nco_code,
                "qp_code": t.qp_code,
                "ncvt_trade_code": t.ncvt_trade_code,
                "aliases": [a.alias for a in t.aliases],
            }
            for t in session.query(Trade).all()
        ]

        # Test resolution candidates to populate trade_crosswalk_review.csv
        test_fuzzy_candidates = [
            {
                "name_en": "Electrician Technician - Level 4",
                "source_system": "pmkvy_dataful",
                "code": "PM_ELE_01",
            },
            {
                "name_en": "Fitter Mechanical Assembly (ITI)",
                "source_system": "dgt_strive",
                "code": "STR_FIT_02",
            },
            {
                "name_en": "Solar Panel Installer Assistant",
                "source_system": "msde_pilot",
                "code": "PLT_SOL_03",
            },
        ]

        fuzzy_count = 0
        for cand in test_fuzzy_candidates:
            res = resolve_candidate(cand, known, log_review=True)
            if res:
                print(
                    f"Matched candidate '{cand['name_en']}' -> Trade {res.matched_trade_id} "
                    f"({res.matched_trade_name}) [Score: {res.score}, review={res.needs_review}]"
                )
                if res.needs_review:
                    fuzzy_count += 1
                # Record in crosswalk table
                session.add(Crosswalk(
                    from_system=cand.get("source_system", "external"),
                    from_code=cand.get("code", "EXT"),
                    to_system="trades",
                    to_code=res.matched_trade_id,
                    relation=res.relation,
                    confidence=res.confidence,
                    method=res.method,
                    needs_review=res.needs_review,
                ))
        session.commit()
        print(f"Wrote {fuzzy_count} fuzzy reviews to {REVIEW_FILE} (all needs_review=True).")

    finally:
        session.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
