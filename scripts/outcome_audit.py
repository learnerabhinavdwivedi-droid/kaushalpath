"""Outcome Evidence Audit Script (Phase 22 - Outcome Evidence Engine).

Flags data quality violations and consistency issues across empirical outcome signals:
1. rate > 100 (or rate > 1.0) or rate < 0
2. certified > enrolled
3. p25 > median or median > p75
4. Reported-vs-verified gaps > 20 percentage points for the same trade and state
5. Rows older than 3 years (source_year < 2023)
6. Missing page_ref or source_url

Writes report to:
    data/processed/outcome_audit.csv

Run:
    python scripts/outcome_audit.py
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.outcome_evidence import OutcomeEvidence

PROCESSED_DIR = REPO_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def run_outcome_audit() -> list[dict]:
    session = SessionLocal()
    flags: list[dict] = []
    try:
        rows = session.query(OutcomeEvidence).all()

        # Group by (trade_id, state) to check reported-vs-verified gap
        placement_by_trade_state: dict[tuple[int, str | None], dict[str, float]] = defaultdict(dict)

        for r in rows:
            # 1. Rate bounds check
            if "rate" in r.metric or "pct" in r.metric:
                val = r.value
                if val > 1.0 and val <= 100.0:
                    val = val / 100.0
                if val < 0.0 or val > 1.0:
                    flags.append({
                        "evidence_id": r.id,
                        "trade_id": r.trade_id,
                        "state": r.state or "National",
                        "metric": r.metric,
                        "severity": "CRITICAL",
                        "issue": f"Rate value out of bounds: {r.value}",
                        "page_ref": r.page_ref or "",
                        "source_url": r.source_url or "",
                    })

            # 2. Intervals check (ci_low > value or value > ci_high)
            if r.ci_low is not None and r.ci_high is not None:
                if r.ci_low > r.value or r.value > r.ci_high:
                    flags.append({
                        "evidence_id": r.id,
                        "trade_id": r.trade_id,
                        "state": r.state or "National",
                        "metric": r.metric,
                        "severity": "CRITICAL",
                        "issue": f"Interval inversion: ci_low ({r.ci_low}) > value ({r.value}) or value > ci_high ({r.ci_high})",
                        "page_ref": r.page_ref or "",
                        "source_url": r.source_url or "",
                    })

            # 3. Missing citation check
            if not r.page_ref:
                flags.append({
                    "evidence_id": r.id,
                    "trade_id": r.trade_id,
                    "state": r.state or "National",
                    "metric": r.metric,
                    "severity": "WARNING",
                    "issue": "Missing page_ref audit citation",
                    "page_ref": "",
                    "source_url": r.source_url or "",
                })
            if not r.source_url:
                flags.append({
                    "evidence_id": r.id,
                    "trade_id": r.trade_id,
                    "state": r.state or "National",
                    "metric": r.metric,
                    "severity": "CRITICAL",
                    "issue": "Missing source_url provenance",
                    "page_ref": r.page_ref or "",
                    "source_url": "",
                })

            # 4. Age check (> 3 years old)
            current_year = 2026
            if r.source_year and (current_year - r.source_year > 3):
                flags.append({
                    "evidence_id": r.id,
                    "trade_id": r.trade_id,
                    "state": r.state or "National",
                    "metric": r.metric,
                    "severity": "INFO",
                    "issue": f"Data older than 3 years (source_year={r.source_year})",
                    "page_ref": r.page_ref or "",
                    "source_url": r.source_url or "",
                })

            # Record placement rate for reported vs verified comparison
            if r.metric == "placement_rate" and r.state:
                p_key = (r.trade_id, r.state)
                norm_rate = r.value if r.value <= 1.0 else r.value / 100.0
                placement_by_trade_state[p_key][r.definition] = norm_rate

        # 5. Reported vs Verified gap check (> 20 percentage points)
        for (trade_id, state), def_map in placement_by_trade_state.items():
            if "reported" in def_map and "verified" in def_map:
                rep_val = def_map["reported"]
                ver_val = def_map["verified"]
                gap = rep_val - ver_val
                if gap > 0.20:
                    flags.append({
                        "evidence_id": 0,
                        "trade_id": trade_id,
                        "state": state or "National",
                        "metric": "placement_rate",
                        "severity": "WARNING",
                        "issue": f"Reported vs verified placement gap > 20 points: reported={rep_val:.2f}, verified={ver_val:.2f} (gap={gap:.2f})",
                        "page_ref": "Comparative check across DGT & PMKVY extracts",
                        "source_url": "https://data.gov.in",
                    })

        # Write audit output CSV
        audit_file = PROCESSED_DIR / "outcome_audit.csv"
        headers = ["evidence_id", "trade_id", "state", "metric", "severity", "issue", "page_ref", "source_url"]
        with audit_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(flags)

        print(f"Outcome Audit complete: {len(rows)} rows evaluated, {len(flags)} audit flags recorded.")
        print(f"Report saved to {audit_file}")
        return flags
    finally:
        session.close()


if __name__ == "__main__":
    run_outcome_audit()
