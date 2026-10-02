"""Stage ESCO occupational data into `data/processed/esco_master.csv`.

ESCO (https://ec.europa.eu/esco/portal) offers the occupation concordance and
multilingual prefLabels (including Hindi via the Indic translations) as bulk
downloads under a CC BY-SA licence. Download is manual: place the extracted
CSVs under `backend/app/data/raw/esco/` then run this to normalise them into
`esco_master.csv` (name_en, esco_uri, name_hi) that the occupation master merges.

Expected raw columns (matched on preferred English label):
    preferred_label_en,preferred_label_hi,uri

Machine-translated / non-authoritative Hindi is passed through; the master loader
keeps needs_review=true so it is never presented as vetted.

Run: python scripts/load_esco.py
"""
from __future__ import annotations

import csv

from _common import PROCESSED_DIR, RAW_DIR, read_csv

RAW_ESCO_DIR = RAW_DIR / "esco"


def main() -> None:
    files = sorted(RAW_ESCO_DIR.glob("*.csv")) if RAW_ESCO_DIR.exists() else []
    if not files:
        print(
            "load_esco: TODO no files under backend/app/data/raw/esco/. "
            "Download the ESCO occupation concordance (see docstring). "
            "Hindi names fall back to the curated demo master. Nothing written."
        )
        return

    out_rows: dict[str, dict[str, str]] = {}
    for path in files:
        for row in read_csv(path):
            name_en = (row.get("preferred_label_en") or row.get("name_en") or "").strip()
            if not name_en:
                continue
            out_rows[name_en] = {
                "name_en": name_en,
                "esco_uri": (row.get("uri") or row.get("esco_uri") or "").strip(),
                "name_hi": (row.get("preferred_label_hi") or row.get("name_hi") or "").strip(),
            }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / "esco_master.csv"
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["name_en", "esco_uri", "name_hi"])
        writer.writeheader()
        writer.writerows(out_rows.values())

    print(f"load_esco: wrote {len(out_rows)} rows to {dest.name}")


if __name__ == "__main__":
    main()
