"""Stage O*NET 31.0 Career Interests and Grounded Abilities.

Reads O*NET 31.0 text database files:
1. `Career Interest Types.txt` (Long format: O*NET-SOC Code, Element ID, Scale ID, Data Value)
   - Scale OI: RIASEC dimension score [1.0, 7.0]. Rescaled to [0.0, 1.0] via:
     `norm_oi = (val - 1.0) / 6.0` (documented per O*NET Scales Reference).
   - Scale IH: High-point code [0, 6] (1=R, 2=I, 3=A, 4=S, 5=E, 6=C, 0=None).
   - n and standard error stay NULL (do not invent them).
   - Grade A, is_demo=False.
2. `Abilities.txt` & `Knowledge.txt`
   - Aptitude constructs from `backend/app/data/raw/aptitude_map.yaml`.
   - Scale IM (Importance, 1-5): `norm_im = (IM - 1.0) / 4.0`.
   - Scale LV (Level, 0-7): `norm_lv = LV / 7.0`.
   - Requirement: `requirement = sqrt(norm_importance * norm_level)` averaged over mapped elements.
   - Unknown element names fail loudly against `Content Model Reference.txt`.

Outputs:
- `data/processed/onet_master.csv`
- `data/processed/onet_abilities.csv`

Run: python scripts/load_onet.py
"""
from __future__ import annotations

import csv
import math
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
APTITUDE_MAP_PATH = RAW_DIR / "aptitude_map.yaml"
CONTENT_MODEL_PATH = RAW_ONET_DIR / "Content Model Reference.txt"
CAREER_INTERESTS_PATH = RAW_ONET_DIR / "Career Interest Types.txt"
OCCUPATION_DATA_PATH = RAW_ONET_DIR / "Occupation Data.txt"
ABILITIES_PATH = RAW_ONET_DIR / "Abilities.txt"
KNOWLEDGE_PATH = RAW_ONET_DIR / "Knowledge.txt"

RIASEC_ELEMENT_MAP = {
    "1.B.1.a": "riasec_r",
    "1.B.1.b": "riasec_i",
    "1.B.1.c": "riasec_a",
    "1.B.1.d": "riasec_s",
    "1.B.1.e": "riasec_e",
    "1.B.1.f": "riasec_c",
}

IH_ELEMENT_MAP = {
    "1.B.1.g": "ih_first",
    "1.B.1.h": "ih_second",
    "1.B.1.i": "ih_third",
}


def rescale_oi(val: float) -> float:
    """Rescale O*NET 31.0 Occupational Interests (OI) from [1.0, 7.0] to [0.0, 1.0].

    Formula: norm_oi = (val - 1.0) / 6.0
    Bounds clamped to [0.0, 1.0].
    """
    rescaled = (val - 1.0) / 6.0
    return max(0.0, min(1.0, rescaled))


def rescale_importance(im: float) -> float:
    """Rescale Importance (IM) from [1.0, 5.0] to [0.0, 1.0]."""
    return max(0.0, min(1.0, (im - 1.0) / 4.0))


def rescale_level(lv: float) -> float:
    """Rescale Level (LV) from [0.0, 7.0] to [0.0, 1.0]."""
    return max(0.0, min(1.0, lv / 7.0))


def validate_aptitude_map(
    apt_cfg: dict[str, Any], content_model_path: pathlib.Path
) -> None:
    """Validate all element names in aptitude_map against Content Model Reference.

    Fails loudly (ValueError) if any element name is unknown or missing.
    """
    if not content_model_path.exists():
        raise FileNotFoundError(
            f"Content Model Reference not found: {content_model_path}"
        )

    valid_elements: set[str] = set()
    with content_model_path.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) > 1:
                valid_elements.add(parts[1].strip())

    constructs = apt_cfg.get("constructs", {})
    for c_name, c_data in constructs.items():
        for el in c_data.get("elements", []):
            el_name = el.get("name", "").strip()
            if not el_name or el_name not in valid_elements:
                raise ValueError(
                    f"Unknown element in aptitude_map for construct '{c_name}': '{el_name}'. "
                    f"Must match O*NET Content Model Reference."
                )


def load_occupation_titles() -> dict[str, str]:
    """Map O*NET-SOC Code -> Title from Occupation Data.txt."""
    titles: dict[str, str] = {}
    if not OCCUPATION_DATA_PATH.exists():
        return titles
    with OCCUPATION_DATA_PATH.open(encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                titles[parts[0].strip()] = parts[1].strip()
    return titles


def load_interests() -> dict[str, dict[str, Any]]:
    """Pivot Career Interest Types.txt long format into {soc_code: row_dict}."""
    if not CAREER_INTERESTS_PATH.exists():
        return {}

    titles = load_occupation_titles()
    pivoted: dict[str, dict[str, Any]] = {}

    with CAREER_INTERESTS_PATH.open(encoding="utf-8") as fh:
        fh.readline()  # header
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) < 5:
                continue
            soc_code = parts[0].strip()
            el_id = parts[1].strip()
            scale_id = parts[3].strip()
            try:
                data_val = float(parts[4].strip())
            except ValueError:
                continue

            if soc_code not in pivoted:
                pivoted[soc_code] = {
                    "onet_code": soc_code,
                    "name_en": titles.get(soc_code, soc_code),
                    "riasec_r": 0.0,
                    "riasec_i": 0.0,
                    "riasec_a": 0.0,
                    "riasec_s": 0.0,
                    "riasec_e": 0.0,
                    "riasec_c": 0.0,
                    "ih_first": None,
                    "ih_second": None,
                    "ih_third": None,
                    "source": "onet_interests",
                    "source_year": 2026,
                    "is_demo": False,
                    "evidence_grade": "A",
                    "n": None,
                    "standard_error": None,
                    "retrieved_on": "2026-10-11",
                    "source_url": "https://www.onetcenter.org/database.html",
                }

            if scale_id == "OI" and el_id in RIASEC_ELEMENT_MAP:
                col_name = RIASEC_ELEMENT_MAP[el_id]
                pivoted[soc_code][col_name] = rescale_oi(data_val)
            elif scale_id == "IH" and el_id in IH_ELEMENT_MAP:
                col_name = IH_ELEMENT_MAP[el_id]
                pivoted[soc_code][col_name] = int(round(data_val))

    return pivoted


def load_abilities_and_knowledge(apt_cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute {soc_code: abilities_dict} from Abilities.txt and Knowledge.txt."""
    titles = load_occupation_titles()

    # Build lookup: (domain, element_name) -> (construct, element_id)
    construct_map: dict[str, list[dict[str, str]]] = apt_cfg.get("constructs", {})

    # Intermediate storage: soc_code -> element_id -> {IM: val, LV: val, N: val}
    raw_scores: dict[str, dict[str, dict[str, float]]] = {}

    for path, _domain in [(ABILITIES_PATH, "Abilities"), (KNOWLEDGE_PATH, "Knowledge")]:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            fh.readline()
            for line in fh:
                parts = line.strip().split("\t")
                if len(parts) < 6:
                    continue
                soc_code = parts[0].strip()
                el_id = parts[1].strip()
                scale_id = parts[3].strip()
                try:
                    data_val = float(parts[4].strip())
                    n_val = int(parts[5].strip()) if parts[5].strip().isdigit() else None
                except ValueError:
                    continue

                if scale_id in ("IM", "LV"):
                    raw_scores.setdefault(soc_code, {}).setdefault(el_id, {})[scale_id] = data_val
                    if n_val:
                        raw_scores[soc_code][el_id]["N"] = n_val

    results: dict[str, dict[str, Any]] = {}
    for soc_code, el_dict in raw_scores.items():
        occ_reqs: dict[str, float] = {}
        all_n: list[float] = []

        for c_name, c_data in construct_map.items():
            construct_vals: list[float] = []
            for el_info in c_data.get("elements", []):
                el_id = el_info.get("element_id")
                if el_id in el_dict:
                    im = el_dict[el_id].get("IM")
                    lv = el_dict[el_id].get("LV")
                    if "N" in el_dict[el_id]:
                        all_n.append(el_dict[el_id]["N"])
                    if im is not None and lv is not None:
                        norm_im = rescale_importance(im)
                        norm_lv = rescale_level(lv)
                        req = math.sqrt(norm_im * norm_lv)
                        construct_vals.append(req)

            occ_reqs[c_name] = (
                sum(construct_vals) / len(construct_vals) if construct_vals else 0.0
            )

        # Primary ability = construct with highest requirement
        primary = max(occ_reqs.items(), key=lambda x: x[1])[0] if occ_reqs else None
        avg_n = int(round(sum(all_n) / len(all_n))) if all_n else None

        results[soc_code] = {
            "onet_code": soc_code,
            "name_en": titles.get(soc_code, soc_code),
            "required_num": round(occ_reqs.get("num", 0.0), 4),
            "required_verbal": round(occ_reqs.get("verbal", 0.0), 4),
            "required_spatial": round(occ_reqs.get("spatial", 0.0), 4),
            "required_mech": round(occ_reqs.get("mech", 0.0), 4),
            "primary_ability": primary,
            "source": "onet_abilities",
            "source_year": 2026,
            "is_demo": False,
            "evidence_grade": "A",
            "n": avg_n,
            "retrieved_on": "2026-10-11",
            "source_url": "https://www.onetcenter.org/database.html",
        }

    return results


def main() -> None:
    if not RAW_ONET_DIR.exists() or not CAREER_INTERESTS_PATH.exists():
        print(
            "load_onet: No O*NET files found under backend/app/data/raw/onet/. "
            "Skipping ingestion."
        )
        return

    # Validate aptitude map against Content Model Reference
    if APTITUDE_MAP_PATH.exists() and CONTENT_MODEL_PATH.exists():
        apt_cfg = yaml.safe_load(APTITUDE_MAP_PATH.read_text(encoding="utf-8"))
        validate_aptitude_map(apt_cfg, CONTENT_MODEL_PATH)
    else:
        apt_cfg = {}

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    root_proc_dir = REPO_ROOT / "data" / "processed"
    root_proc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Interests (RIASEC + IH)
    interests_data = load_interests()
    dest_master = PROCESSED_DIR / "onet_master.csv"
    master_fields = [
        "onet_code",
        "name_en",
        "riasec_r",
        "riasec_i",
        "riasec_a",
        "riasec_s",
        "riasec_e",
        "riasec_c",
        "ih_first",
        "ih_second",
        "ih_third",
        "source",
        "source_year",
        "is_demo",
        "evidence_grade",
        "n",
        "standard_error",
        "retrieved_on",
        "source_url",
    ]
    with dest_master.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=master_fields)
        writer.writeheader()
        writer.writerows(interests_data.values())

    # Mirror to repo root data/processed
    (root_proc_dir / "onet_master.csv").write_text(
        dest_master.read_text(encoding="utf-8"), encoding="utf-8"
    )

    print(
        f"load_onet: wrote {len(interests_data)} occupations to "
        f"{dest_master.relative_to(REPO_ROOT)}"
    )

    # 2. Abilities
    abilities_data = load_abilities_and_knowledge(apt_cfg)
    dest_abilities = PROCESSED_DIR / "onet_abilities.csv"
    abilities_fields = [
        "onet_code",
        "name_en",
        "required_num",
        "required_verbal",
        "required_spatial",
        "required_mech",
        "primary_ability",
        "source",
        "source_year",
        "is_demo",
        "evidence_grade",
        "n",
        "retrieved_on",
        "source_url",
    ]
    with dest_abilities.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=abilities_fields)
        writer.writeheader()
        writer.writerows(abilities_data.values())

    (root_proc_dir / "onet_abilities.csv").write_text(
        dest_abilities.read_text(encoding="utf-8"), encoding="utf-8"
    )

    print(
        f"load_onet: wrote {len(abilities_data)} ability profiles to "
        f"{dest_abilities.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
