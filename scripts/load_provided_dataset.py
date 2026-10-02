"""Stage the problem-statement-provided datasets into `provided_master.csv`.

docs/PS_SPEC.md lists the datasets the organisers provide (occupation/course
lists, market or salary data). Until those official files are added to the repo
(see docs/ASSUMPTIONS.md A1), this is a passthrough: drop the provided CSVs under
`backend/app/data/raw/provided/` and run this to normalise the columns the
occupation master understands. If nothing is present it is a no-op and the demo
seed remains the source.

Recognised optional columns per row:
    name_en,name_hi,nco_code,esco_uri,nsqf_level,description,source,source_year,is_demo

Run: python scripts/load_provided_dataset.py
"""
from __future__ import annotations

import csv

from _common import PROCESSED_DIR, RAW_DIR, read_csv

RAW_PROVIDED_DIR = RAW_DIR / "provided"
FIELDS = ["name_en", "name_hi", "nco_code", "esco_uri", "nsqf_level",
          "description", "source", "source_year", "is_demo"]


def main() -> None:
    files = sorted(RAW_PROVIDED_DIR.glob("*.csv")) if RAW_PROVIDED_DIR.exists() else []
    if not files:
        print(
            "load_provided_dataset: TODO no files under backend/app/data/raw/provided/. "
            "Add the PS-provided datasets listed in docs/PS_SPEC.md (see docs/ASSUMPTIONS.md "
            "A1). Using demo seed only. Nothing written."
        )
        return

    out_rows: dict[str, dict[str, str]] = {}
    for path in files:
        for row in read_csv(path):
            name_en = (row.get("name_en") or "").strip()
            if not name_en:
                continue
            merged = out_rows.setdefault(name_en, {"name_en": name_en})
            merged.update({k: (row.get(k) or "").strip() for k in FIELDS if row.get(k)})

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / "provided_master.csv"
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows.values())

    print(f"load_provided_dataset: wrote {len(out_rows)} rows to {dest.name}")


if __name__ == "__main__":
    main()
