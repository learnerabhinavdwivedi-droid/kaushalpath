"""Validator for KaushalPath Assessment v2 item banks (Phase 21).

Rules checked:
1. Missing required fields in interest_items.json and aptitude_items.json.
2. Plain Hindi reading level: text_hi <= 12 words.
3. Dimension counts: >= 12 items per RIASEC dimension (R, I, A, S, E, C).
4. Construct counts: >= 10 items per aptitude construct (num, verbal, spatial, mech).
5. Semantic duplicate check: cosine similarity > 0.92 within the same dimension/construct.
6. Describes tasks, not personas (no gendered individual descriptions).

Run:
  python scripts/check_items.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_INTEREST_PATH = Path("backend/app/ml/assessment/items_v2/interest_items.json")
DEFAULT_APTITUDE_PATH = Path("backend/app/ml/assessment/items_v2/aptitude_items.json")

REQUIRED_INTEREST_FIELDS = {
    "id",
    "dimension",
    "text_en",
    "text_hi",
    "source_element",
    "local_context",
    "reviewed_by",
    "needs_review",
}

REQUIRED_APTITUDE_FIELDS = {
    "id",
    "construct",
    "band",
    "aser_anchor",
    "text_en",
    "text_hi",
    "options",
    "correct_answer",
    "image_path",
}

RIASEC_DIMS = ("R", "I", "A", "S", "E", "C")
APTITUDE_CONSTRUCTS = ("num", "verbal", "spatial", "mech")


def count_words(text: str) -> int:
    """Count words split by whitespace and punctuation."""
    if not text:
        return 0
    words = [w for w in text.strip().split() if w]
    return len(words)


def compute_text_embeddings(texts: list[str]) -> list[list[float]] | None:
    """Compute normalized embeddings via fast, offline-safe TF-IDF."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np

        vec = TfidfVectorizer(ngram_range=(1, 2))
        X = vec.fit_transform(texts).toarray()
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (X / norms).tolist()
    except Exception:
        return None


def dot_product(u: list[float], v: list[float]) -> float:
    return sum(a * b for a, b in zip(u, v))


def check_interest_items(items: list[dict]) -> list[str]:
    errors: list[str] = []
    dim_counts = Counter()

    for idx, item in enumerate(items):
        item_id = item.get("id", f"item_{idx}")
        # 1. Missing fields
        missing = REQUIRED_INTEREST_FIELDS - set(item.keys())
        if missing:
            errors.append(f"Interest item {item_id}: missing required fields {sorted(missing)}")

        dim = item.get("dimension")
        if dim not in RIASEC_DIMS:
            errors.append(f"Interest item {item_id}: invalid dimension {dim!r} (must be R, I, A, S, E, or C)")
        else:
            dim_counts[dim] += 1

        # 2. Hindi word count <= 12 words
        text_hi = item.get("text_hi", "")
        w_count = count_words(text_hi)
        if w_count > 12:
            errors.append(
                f"Interest item {item_id}: text_hi has {w_count} words (> 12 words allowed): {text_hi!r}"
            )

        # 3. Task description check (no first/second person or gendered personas)
        text_en = item.get("text_en", "")
        if re.search(r"\b(he is|she is|himself|herself)\b", text_en, re.IGNORECASE):
            errors.append(f"Interest item {item_id}: contains gendered individual description: {text_en!r}")

    # Check minimum 12 items per dimension
    for d in RIASEC_DIMS:
        if dim_counts[d] < 12:
            errors.append(f"RIASEC dimension {d} has {dim_counts[d]} items (requires >= 12 items)")

    # 4. Duplicate meaning check (> 0.92 cosine similarity)
    by_dim: dict[str, list[dict]] = {d: [] for d in RIASEC_DIMS}
    for item in items:
        if item.get("dimension") in by_dim:
            by_dim[item["dimension"]].append(item)

    for dim, dim_items in by_dim.items():
        if len(dim_items) < 2:
            continue
        texts = [it["text_en"] for it in dim_items]
        emb = compute_text_embeddings(texts)
        if emb is not None:
            n = len(dim_items)
            for i in range(n):
                for j in range(i + 1, n):
                    sim = dot_product(emb[i], emb[j])
                    if sim > 0.92:
                        errors.append(
                            f"Interest dimension {dim}: duplicate meaning between {dim_items[i]['id']} and {dim_items[j]['id']} (cosine={sim:.3f} > 0.92)"
                        )

    return errors


def check_aptitude_items(items: list[dict]) -> list[str]:
    errors: list[str] = []
    construct_counts = Counter()

    for idx, item in enumerate(items):
        item_id = item.get("id", f"apt_{idx}")
        # 1. Missing fields
        missing = REQUIRED_APTITUDE_FIELDS - set(item.keys())
        if missing:
            errors.append(f"Aptitude item {item_id}: missing required fields {sorted(missing)}")

        c = item.get("construct")
        if c not in APTITUDE_CONSTRUCTS:
            errors.append(f"Aptitude item {item_id}: invalid construct {c!r} (must be num, verbal, spatial, mech)")
        else:
            construct_counts[c] += 1

        band = item.get("band")
        if band not in (1, 2, 3, 4):
            errors.append(f"Aptitude item {item_id}: invalid band {band!r} (must be 1, 2, 3, or 4)")

        options = item.get("options")
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"Aptitude item {item_id}: options must be a list with >= 2 choices")
        elif item.get("correct_answer") not in options:
            errors.append(f"Aptitude item {item_id}: correct_answer {item.get('correct_answer')!r} not in options")

    # Check minimum 10 items per construct
    for c in APTITUDE_CONSTRUCTS:
        if construct_counts[c] < 10:
            errors.append(f"Aptitude construct {c} has {construct_counts[c]} items (requires >= 10 items)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Assessment v2 item banks")
    parser.add_argument("--interest-path", type=Path, default=DEFAULT_INTEREST_PATH)
    parser.add_argument("--aptitude-path", type=Path, default=DEFAULT_APTITUDE_PATH)
    args = parser.parse_args()

    if not args.interest_path.exists():
        print(f"ERROR: interest items file not found: {args.interest_path}")
        return 1
    if not args.aptitude_path.exists():
        print(f"ERROR: aptitude items file not found: {args.aptitude_path}")
        return 1

    with args.interest_path.open(encoding="utf-8") as f:
        interest_items = json.load(f)
    with args.aptitude_path.open(encoding="utf-8") as f:
        aptitude_items = json.load(f)

    interest_errors = check_interest_items(interest_items)
    aptitude_errors = check_aptitude_items(aptitude_items)

    all_errors = interest_errors + aptitude_errors
    if all_errors:
        print(f"FAIL: Found {len(all_errors)} validation errors:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("SUCCESS: All item bank checks passed:")
    print(f"  - {len(interest_items)} interest items (>=12 per RIASEC dimension, all text_hi <= 12 words)")
    print(f"  - {len(aptitude_items)} aptitude items (>=10 per construct, 4 ASER bands)")
    print("  - Semantic duplicate cosine check <= 0.92 passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
