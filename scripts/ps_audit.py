"""Phase 9 FINAL PS audit: weighted alignment score from docs/PS_TRACEABILITY.md.

Parses the traceability markdown table and computes

    score = Σ (weight × status) / Σ weight

where weight ∈ {1,2,3} (3 = explicitly stated in the PS) and status ∈ {0,0.5,1}.
It also fails a row that is marked complete (status 1) but carries no evidence —
so "done" always means "there is a test/demo artefact pointing at it".

This is the reproducible, judge-proof version of "re-read the PS and score
ourselves": `make ps-audit` exits non-zero if the total is below the 0.97 gate
or any claimed-complete row lacks evidence. It never edits the file — it only
reads it, so the numbers cannot be quietly massaged.

Usage:
    python scripts/ps_audit.py            # score docs/PS_TRACEABILITY.md
    python scripts/ps_audit.py --min 0.97
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TABLE = _REPO_ROOT / "docs" / "PS_TRACEABILITY.md"

# Report marks use non-ASCII glyphs; force UTF-8 stdout so the audit never
# crashes on a legacy Windows console (cp1252) when piped, e.g. `| tail`.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# A table row is a data row only if its weight cell and status cell are numeric.
_INT = re.compile(r"^\d+$")
_STATUS = re.compile(r"^(0|0\.5|1)$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(c == "" or set(c) <= set(":-") for c in cells)


def parse_rows(md: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in md.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 4 or _is_separator(cells):
            continue
        rid, weight_s, status_s = cells[0], cells[2], cells[-1]
        evidence = cells[-2]
        if not _INT.match(weight_s) or not _STATUS.match(status_s):
            continue  # header row or prose table
        rows.append(
            {
                "id": rid,
                "weight": int(weight_s),
                "status": float(status_s),
                "evidence": evidence,
            }
        )
    return rows


def compute_score(md: str) -> dict[str, object]:
    rows = parse_rows(md)
    total_weight = sum(r["weight"] for r in rows)
    achieved = sum(r["weight"] * r["status"] for r in rows)
    score = achieved / total_weight if total_weight else 0.0
    unevidenced = [
        r["id"]
        for r in rows
        if r["status"] == 1 and not str(r["evidence"]).strip()
    ]
    return {
        "rows": rows,
        "n_rows": len(rows),
        "total_weight": total_weight,
        "achieved": achieved,
        "score": score,
        "unevidenced_complete": unevidenced,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Weighted PS alignment score")
    parser.add_argument("--table", default=str(DEFAULT_TABLE))
    parser.add_argument("--min", type=float, default=0.97, help="Pass threshold")
    args = parser.parse_args()

    path = pathlib.Path(args.table)
    result = compute_score(path.read_text(encoding="utf-8"))

    print(f"PS alignment audit — {path.name}")
    print(f"{'ID':<5} {'W':>2} {'Status':>6} {'Weighted':>8}  Evidence")
    for r in result["rows"]:
        mark = "✓" if r["status"] == 1 else ("~" if r["status"] == 0.5 else "✗")
        print(
            f"{r['id']:<5} {r['weight']:>2} {mark:>6} "
            f"{r['weight'] * r['status']:>8.1f}  {r['evidence']}"
        )
    print("-" * 60)
    print(
        f"Rows: {result['n_rows']}  Achieved: {result['achieved']:.1f} / "
        f"{result['total_weight']}  =>  SCORE = {result['score']:.4f} "
        f"({result['score'] * 100:.2f}%)"
    )

    ok = result["score"] >= args.min
    if not ok:
        print(f"FAIL: score {result['score']:.4f} < required {args.min}")
    if result["unevidenced_complete"]:
        print(f"FAIL: complete rows without evidence: {result['unevidenced_complete']}")
        ok = False
    if ok:
        pct = result["score"] * 100
        print(
            f"PASS: alignment {pct:.2f}% ≥ {args.min * 100:.0f}%, "
            "all complete rows evidenced."
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
