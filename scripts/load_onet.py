"""Stage O*NET interest codes into `data/processed/onet_master.csv`.

O*NET publishes the "Occupation Data" and "Interest" files (CCS / O*NET-SOC codes
plus Holland RIASEC scores) at https://www.onetcenter.org/database.html . They
require a click-through licence, so download is manual: drop the extracted CSVs
under `backend/app/data/raw/onet/` then run this. If nothing is present the
occupation master falls back to curated demo RIASEC (is_demo=true). No scraping.

Expected raw columns (any subset, matched on occupation title):
    title,onet_code,riasec_r,riasec_i,riasec_a,riasec_s,riasec_e,riasec_c

Run: python scripts/load_onet.py
"""
from __future__ import annotations

import csv

from _common import PROCESSED_DIR, RAW_DIR, read_csv

RAW_ONET_DIR = RAW_DIR / "onet"


def main() -> None:
    files = sorted(RAW_ONET_DIR.glob("*.csv")) if RAW_ONET_DIR.exists() else []
    if not files:
        print(
            "load_onet: TODO no files under backend/app/data/raw/onet/. "
            "Download the O*NET Interest/Occupation CSVs (see docstring). "
            "Falling back to curated demo RIASEC. Nothing written."
        )
        return

    out_rows: dict[str, dict[str, str]] = {}
    for path in files:
        for row in read_csv(path):
            title = (row.get("title") or row.get("name_en") or "").strip()
            if not title:
                continue
            out_rows.setdefault(title, {})
            out_rows[title].update(
                {
                    "name_en": title,
                    "onet_code": (row.get("onet_code") or "").strip(),
                    "riasec_r": (row.get("riasec_r") or "").strip(),
                    "riasec_i": (row.get("riasec_i") or "").strip(),
                    "riasec_a": (row.get("riasec_a") or "").strip(),
                    "riasec_s": (row.get("riasec_s") or "").strip(),
                    "riasec_e": (row.get("riasec_e") or "").strip(),
                    "riasec_c": (row.get("riasec_c") or "").strip(),
                }
            )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / "onet_master.csv"
    fields = ["name_en", "onet_code", "riasec_r", "riasec_i", "riasec_a",
              "riasec_s", "riasec_e", "riasec_c"]
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows.values())

    print(f"load_onet: wrote {len(out_rows)} rows to {dest.relative_to(PROCESSED_DIR.parent)}")


if __name__ == "__main__":
    main()
