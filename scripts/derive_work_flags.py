"""Derive work flags from O*NET 31.0 Work Context (Phase 20).

Reads:
- `backend/app/data/raw/onet/Work Context.txt`
- `backend/app/data/raw/work_flags.yaml`

Evaluates:
- `outdoor`: Exposed to weather conditions or under cover
- `hazard`: Exposed to hazardous conditions, equipment, high places, infections
- `physical_effort`: Standing, bending, kneeling/stooping, walking/running
- `customer_contact`: Contact with others, dealing with external customers or difficult people

Flags drive family-facing safety questions and optional SOFT learner preferences.
They are NEVER a hard filter and NEVER gated by gender (DATA ADDENDUM Rules 9, 10).

Outputs:
- `data/processed/onet_work_flags.csv`

Run: python scripts/derive_work_flags.py
"""
from __future__ import annotations

import csv
import pathlib
import sys
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from _common import PROCESSED_DIR, RAW_DIR  # noqa: E402

RAW_ONET_DIR = RAW_DIR / "onet"
WORK_CONTEXT_PATH = RAW_ONET_DIR / "Work Context.txt"
OCCUPATION_DATA_PATH = RAW_ONET_DIR / "Occupation Data.txt"
WORK_FLAGS_CONFIG = RAW_DIR / "work_flags.yaml"


def normalize_context_score(raw_val: float, scale_id: str) -> float:
    """Normalize Work Context score to 0.0 - 100.0 range.

    - Scale CX (Context Rating 1-5): (CX - 1.0) / 4.0 * 100.0
    - Scale CXP (Context Percentage 0-100): raw_val directly
    """
    if scale_id == "CX":
        return max(0.0, min(100.0, (raw_val - 1.0) / 4.0 * 100.0))
    elif scale_id == "CXP":
        return max(0.0, min(100.0, raw_val))
    return max(0.0, min(100.0, raw_val))


def derive_flags_for_all(
    wc_path: pathlib.Path, cfg: dict[str, Any]
) -> dict[str, dict[str, bool]]:
    """Evaluate work flags for each O*NET occupation code."""
    flags_cfg = cfg.get("flags", {})

    # Map: element_name -> list of (flag_name, threshold)
    element_to_flags: dict[str, list[tuple[str, float]]] = {}
    for flag_name, flag_data in flags_cfg.items():
        thresh = float(flag_data.get("threshold", 50.0))
        for el in flag_data.get("elements", []):
            element_to_flags.setdefault(el.strip(), []).append((flag_name, thresh))

    # soc_code -> {element_name: max_score}
    soc_element_scores: dict[str, dict[str, float]] = {}

    with wc_path.open(encoding="utf-8") as fh:
        fh.readline()  # header
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) < 6:
                continue
            soc_code = parts[0].strip()
            el_name = parts[2].strip()
            scale_id = parts[3].strip()
            try:
                data_val = float(parts[5].strip())
            except ValueError:
                continue

            if el_name in element_to_flags:
                score = normalize_context_score(data_val, scale_id)
                current = soc_element_scores.setdefault(soc_code, {}).get(el_name, 0.0)
                if score > current:
                    soc_element_scores[soc_code][el_name] = score

    results: dict[str, dict[str, bool]] = {}
    for soc_code, el_scores in soc_element_scores.items():
        occ_flags: dict[str, bool] = {fn: False for fn in flags_cfg}
        for el_name, score in el_scores.items():
            for fn, thresh in element_to_flags.get(el_name, []):
                if score >= thresh:
                    occ_flags[fn] = True
        results[soc_code] = occ_flags

    return results


def main() -> None:
    if not WORK_CONTEXT_PATH.exists() or not WORK_FLAGS_CONFIG.exists():
        print(
            "derive_work_flags: Required files not found. "
            f"Context: {WORK_CONTEXT_PATH.exists()}, Config: {WORK_FLAGS_CONFIG.exists()}"
        )
        return

    cfg = yaml.safe_load(WORK_FLAGS_CONFIG.read_text(encoding="utf-8"))
    flags_data = derive_flags_for_all(WORK_CONTEXT_PATH, cfg)

    # Titles lookup
    titles: dict[str, str] = {}
    if OCCUPATION_DATA_PATH.exists():
        with OCCUPATION_DATA_PATH.open(encoding="utf-8") as fh:
            fh.readline()
            for line in fh:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    titles[parts[0].strip()] = parts[1].strip()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    root_proc_dir = REPO_ROOT / "data" / "processed"
    root_proc_dir.mkdir(parents=True, exist_ok=True)

    dest = PROCESSED_DIR / "onet_work_flags.csv"
    fields = [
        "onet_code",
        "name_en",
        "outdoor",
        "hazard",
        "physical_effort",
        "customer_contact",
    ]

    rows_to_write = []
    for soc_code, fl in flags_data.items():
        rows_to_write.append(
            {
                "onet_code": soc_code,
                "name_en": titles.get(soc_code, soc_code),
                "outdoor": fl.get("outdoor", False),
                "hazard": fl.get("hazard", False),
                "physical_effort": fl.get("physical_effort", False),
                "customer_contact": fl.get("customer_contact", False),
            }
        )

    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_to_write)

    (root_proc_dir / "onet_work_flags.csv").write_text(
        dest.read_text(encoding="utf-8"), encoding="utf-8"
    )

    print(
        f"derive_work_flags: wrote {len(rows_to_write)} occupations work flags to "
        f"{dest.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
