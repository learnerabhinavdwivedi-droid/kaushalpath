"""Phase 25 — Data Provenance Audit (scripts/data_provenance_audit.py).

Wired into `make check` to enforce that every numeric table in
docs/EVAL_REPORT.md carries a `Data` column, and that any table
containing a SYNTHETIC-sourced row says so in its own caption.

Exit codes:
  0 — All checks passed.
  1 — One or more tables are missing the Data column or contain
      SYNTHETIC numbers without the word SYNTHETIC/SIMULATED in
      their caption.

Usage:
    python scripts/data_provenance_audit.py
    python scripts/data_provenance_audit.py docs/EVAL_REPORT.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = _REPO_ROOT / "docs" / "EVAL_REPORT.md"

# Table sections we require to carry a "Data" column
AUDITED_SECTIONS = [
    "Tier 1",
    "Tier 2",
]

# Words that satisfy the "clearly labeled as simulated" requirement
_SIMULATED_WORDS = re.compile(r"\b(SIMULATED|SYNTHETIC|synthetic|simulated)\b")

# A markdown table row: starts with | and contains | separators
_TABLE_ROW = re.compile(r"^\s*\|")
# A markdown table header separator row (---)
_TABLE_SEP = re.compile(r"^\s*\|[\s\-|:]+\|")

# Regex to find a "Data" column header in a header row
_DATA_COL_HEADER = re.compile(r"\|\s*Data\s*\|", re.IGNORECASE)

# Matches a numeric claim (integer or decimal, possibly preceded by $n=)
_NUMERIC = re.compile(r"\d+\.\d+|\b\d{2,}\b")


def _parse_tables(text: str) -> list[dict]:
    """Extract markdown tables with their surrounding caption context."""
    tables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        # Look for a table header row
        if _TABLE_ROW.match(lines[i]) and not _TABLE_SEP.match(lines[i]):
            start = i
            # Collect preceding caption (up to 5 lines above)
            caption_lines = lines[max(0, i - 5) : i]
            # Collect the table itself
            table_lines = []
            while i < len(lines) and _TABLE_ROW.match(lines[i]):
                table_lines.append(lines[i])
                i += 1
            # Collect following caption (up to 3 lines below)
            footer_lines = lines[i : i + 3]
            context = "\n".join(caption_lines + footer_lines)
            tables.append(
                {
                    "start_line": start + 1,
                    "header": table_lines[0] if table_lines else "",
                    "rows": table_lines[2:] if len(table_lines) > 2 else [],
                    "context": context,
                }
            )
        else:
            i += 1
    return tables


def _in_audited_section(text: str, table_start: int) -> bool:
    """Return True if the table is within a Tier 1 or Tier 2 section."""
    lines = text.splitlines()
    for j in range(min(table_start - 1, len(lines) - 1), max(0, table_start - 40), -1):
        line = lines[j]
        if line.startswith("## Tier"):
            return any(s in line for s in AUDITED_SECTIONS)
        if line.startswith("## ") and not line.startswith("## Tier"):
            # Reached a different section — stop looking upward
            return False
    return False


def audit_report(report_path: Path) -> list[str]:
    """Audit the EVAL_REPORT.md file.

    Returns a list of failure messages.  Empty list = all passed.
    """
    if not report_path.exists():
        return [f"FAIL: {report_path} does not exist."]

    text = report_path.read_text(encoding="utf-8")
    tables = _parse_tables(text)
    failures: list[str] = []

    for tbl in tables:
        # Only audit tables inside Tier 1 / Tier 2 sections
        if not _in_audited_section(text, tbl["start_line"]):
            continue

        header = tbl["header"]
        context = tbl["context"]

        # Check 1: table must have a "Data" column header
        if not _DATA_COL_HEADER.search(header):
            failures.append(
                f"  Line {tbl['start_line']}: Table is missing a 'Data' column.\n"
                f"    Header: {header.strip()[:120]}"
            )
            continue  # Can't check Data values if column is absent

        # Check 2: any row with SYNTHETIC in its Data cell must have
        # SIMULATED or SYNTHETIC in the caption/context
        for row in tbl["rows"]:
            cells = [c.strip() for c in row.split("|")]
            # Find the Data column index from the header
            hcells = [c.strip() for c in header.split("|")]
            try:
                data_idx = next(
                    i for i, c in enumerate(hcells) if c.upper() == "DATA"
                )
            except StopIteration:
                break  # Should not happen given check 1, but guard anyway

            if data_idx < len(cells) and "SYNTHETIC" in cells[data_idx].upper():
                if not _SIMULATED_WORDS.search(context):
                    failures.append(
                        f"  Line {tbl['start_line']}: Table row contains SYNTHETIC data "
                        f"but table caption does not say SIMULATED or SYNTHETIC.\n"
                        f"    Row: {row.strip()[:120]}\n"
                        f"    Context snippet: {context.strip()[:200]}"
                    )

    return failures


def main() -> int:
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT
    print(f"[data_provenance_audit] Auditing: {report_path}")

    failures = audit_report(report_path)

    if failures:
        print("\nFAIL — provenance audit found issues:\n")
        for f in failures:
            print(f)
        print(
            "\n  Fix: add a 'Data' column (REAL|SYNTHETIC) to every Tier 1/Tier 2 table,\n"
            "  and add the word SIMULATED or SYNTHETIC to the caption of any table that\n"
            "  contains SYNTHETIC rows.\n"
        )
        return 1

    print("PASS — all audited tables carry a Data column and synthetic rows are labeled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
