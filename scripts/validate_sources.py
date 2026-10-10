"""Validate raw dataset provenance against SOURCES.yaml (Phase 19).

Enforces Master Data Rules:
1. Every loaded row / source carries provenance: id, owner, url, licence,
   access_method, refresh_cadence, grain, key_columns, evidence_grade,
   definition_notes, retrieved_on.
2. Every file placed under data/raw/ must be tracked in SOURCES.yaml with
   a valid retrieved_on timestamp.
3. Exits non-zero if any source is invalid or unmapped.
"""
from __future__ import annotations

import pathlib
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "backend" / "app" / "data" / "raw"
SOURCES_FILE = RAW_DIR / "SOURCES.yaml"

REQUIRED_FIELDS = {
    "id",
    "owner",
    "url",
    "licence",
    "access_method",
    "refresh_cadence",
    "grain",
    "key_columns",
    "evidence_grade",
    "definition_notes",
    "retrieved_on",
}
VALID_GRADES = {"A", "B", "C", "D"}
IGNORED_FILES = {"README.md", "SOURCES.yaml", ".gitkeep", ".gitignore"}


def validate_registry() -> tuple[dict[str, dict], list[str]]:
    errors: list[str] = []
    if not SOURCES_FILE.exists():
        return {}, [f"Registry file not found: {SOURCES_FILE}"]

    try:
        data = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {}, [f"YAML parsing error in {SOURCES_FILE}: {e}"]

    sources_list = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources_list, list):
        return {}, ["SOURCES.yaml must contain a top-level 'sources' list."]

    registry: dict[str, dict] = {}
    for idx, entry in enumerate(sources_list):
        if not isinstance(entry, dict):
            errors.append(f"Entry #{idx} is not a dictionary.")
            continue

        sid = entry.get("id")
        if not sid:
            errors.append(f"Entry #{idx} is missing 'id'.")
            continue
        if sid in registry:
            errors.append(f"Duplicate source id: {sid}")

        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            errors.append(f"Source '{sid}' is missing required fields: {sorted(missing)}")

        grade = entry.get("evidence_grade")
        if grade not in VALID_GRADES:
            errors.append(
                f"Source '{sid}' has invalid evidence_grade '{grade}'. Must be in {VALID_GRADES}"
            )

        retrieved_on = entry.get("retrieved_on")
        if not retrieved_on or not str(retrieved_on).strip():
            errors.append(f"Source '{sid}' is missing or has empty 'retrieved_on'.")

        key_cols = entry.get("key_columns")
        if not isinstance(key_cols, list) or len(key_cols) == 0:
            errors.append(f"Source '{sid}' key_columns must be a non-empty list.")

        registry[sid] = entry

    return registry, errors


def validate_raw_files(registry: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    if not RAW_DIR.exists():
        return errors

    # Check for unmapped raw files
    known_subdirs = {
        "onet": ["onet_interests", "onet_abilities", "onet_work_context"],
        "aser": ["aser_2023"],
        "provided": ["sih_eval_or_pilot"],
        "nco_nsqf": ["nco_crosswalk", "ncvet_qp"],
        "dgt": ["dgt_iti_grading", "dgt_strive"],
        "labour": ["plfs_microdata"],
        "pmkvy": ["pmkvy_placement"],
        "schemes": ["scheme_guidelines"],
    }

    for path in RAW_DIR.rglob("*"):
        if path.is_file():
            rel = path.relative_to(RAW_DIR)
            if rel.name in IGNORED_FILES:
                continue

            # Check if file has an association in registry or known subdirs
            parent_key = rel.parts[0] if len(rel.parts) > 1 else rel.stem
            matched = False
            for sid, _entry in registry.items():
                if sid == parent_key or sid in known_subdirs.get(parent_key, []):
                    matched = True
                    break
            if not matched:
                errors.append(f"Unregistered file under data/raw/: {rel}")

    return errors


def main() -> int:
    registry, reg_errors = validate_registry()
    file_errors = validate_raw_files(registry)
    all_errors = reg_errors + file_errors

    if all_errors:
        print("ERROR: Source validation failed:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"PASS: Source registry validated successfully ({len(registry)} sources registered).")
    for sid, entry in registry.items():
        print(f"  - [{entry['evidence_grade']}] {sid:<20} retrieved_on: {entry['retrieved_on']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
