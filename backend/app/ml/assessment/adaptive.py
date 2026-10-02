"""Adaptive test engine (PHASE_2.md).

A session is a plain, JSON-serialisable dict so it can be persisted on
``assessments.state_json`` and resumed across API calls. The engine is pure:
it never touches the DB or FastAPI — `services/assessment_svc.py` wires it up.

Two phases:
1. interest  — adaptive RIASEC selection (the part G4 measures)
2. aptitude  — a fixed mini-test (5 items x 4 dimensions) served after interest

Stop rules (interest): >=2 items seeded per dimension, then keep asking the
dimension that most sharpens the top-3 ordering until *ordering confidence*
>= 0.95, or 24 items asked, or the 30-item hard cap.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.ml.assessment import scoring

RIASEC_DIMS = scoring.RIASEC_DIMS
APTITUDE_DIMS = scoring.APTITUDE_DIMS

SEED_PER_DIM = 2  # minimum items per dimension before adaptivity kicks in
TARGET_ITEMS = 24  # soft target (spec: avg <= 24)
HARD_CAP = 30  # never ask more than this for interest
CONF_STOP = 0.95  # ordering-confidence threshold to stop early
_EPS = 1e-6

_BANK_DIR = Path(__file__).parent
_PRIOR_SD = 0.5  # assumed spread before we see item-to-item variance
_EVIDENCE_FULL = 4  # items per dimension at which evidence is considered complete


def load_interest_bank(path: Path | None = None) -> list[dict]:
    """Load the RIASEC item bank (default: riasec_items.json next to this file)."""
    return json.loads((path or _BANK_DIR / "riasec_items.json").read_text(encoding="utf-8"))


def load_aptitude_bank(path: Path | None = None) -> list[dict]:
    """Load the aptitude item bank."""
    return json.loads((path or _BANK_DIR / "aptitude_items.json").read_text(encoding="utf-8"))


def new_state() -> dict[str, Any]:
    """A fresh, empty interest-first session snapshot (JSON-safe)."""
    return {
        "status": "in_progress",
        "phase": "interest",
        "interest_responses": {},  # item_id -> 1..5
        "aptitude_responses": {},  # item_id -> bool (correct?)
        "riasec": {d: 0.5 for d in RIASEC_DIMS},
        "top3_code": "",
        "aptitude": {d: 0.0 for d in APTITUDE_DIMS},
        "confidence": 0.0,
        "items_answered": 0,
    }


# --- interest aggregates -----------------------------------------------------
def _aggregates(state: dict, bank: list[dict]) -> dict[str, dict[str, float]]:
    """Per-dimension running count, mean (signed [-1,1]) and standard error."""
    xs: dict[str, list[float]] = {d: [] for d in RIASEC_DIMS}
    for item in bank:
        value = state["interest_responses"].get(item["id"])
        if value is not None:
            xs[item["dimension"]].append(scoring.signed(value, item.get("reverse", False)))
    agg: dict[str, dict[str, float]] = {}
    for dim, vals in xs.items():
        n = len(vals)
        mean = sum(vals) / n if n else 0.0
        if n > 1:
            var = sum((x - mean) ** 2 for x in vals) / (n - 1)
            sd = math.sqrt(var)
        else:
            sd = _PRIOR_SD
        agg[dim] = {"n": n, "mean": mean, "se": sd / math.sqrt(max(n, 1))}
    return agg


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _pair_prob(agg: dict, dim_a: str, dim_b: str) -> float:
    """P(score_a > score_b) via a normal approximation of the mean difference."""
    a, b = agg[dim_a], agg[dim_b]
    margin = a["mean"] - b["mean"]
    se = math.sqrt(a["se"] ** 2 + b["se"] ** 2) + _EPS
    return _phi(margin / se)


def ordering_confidence(state: dict, bank: list[dict]) -> float:
    """Confidence in the top-3 Holland code.

    Driven by *set membership*: how clearly the third-ranked dimension sits
    above everything outside the top-3 (the rank3-vs-rank4 boundary that decides
    which three letters appear). The fine order of the three letters is only
    loosely determined when latents are close, so it is *not* a stop gate here
    (it is reported separately as an order-agreement metric in the eval). A
    count-based evidence term (saturating at ``_EVIDENCE_FULL`` items/dim)
    prevents the first couple of answers from triggering a premature stop.
    """
    agg = _aggregates(state, bank)
    total = sum(a["n"] for a in agg.values())
    if total < SEED_PER_DIM * len(RIASEC_DIMS) - 2:
        return _clamp(total / (SEED_PER_DIM * len(RIASEC_DIMS)) * 0.5)
    order = sorted(RIASEC_DIMS, key=lambda d: (-agg[d]["mean"], d))

    # set separation: the rank-3 dimension above every dimension outside top-3
    set_conf = min(_pair_prob(agg, order[2], d) for d in order[3:])
    evidence = sum(min(1.0, agg[d]["n"] / _EVIDENCE_FULL) for d in RIASEC_DIMS) / len(RIASEC_DIMS)
    return _clamp(0.85 * set_conf + 0.15 * evidence)


def _available(state: dict, bank: list[dict], dim: str) -> list[dict]:
    return [
        it
        for it in bank
        if it["dimension"] == dim and it["id"] not in state["interest_responses"]
    ]


def next_interest_item(state: dict, bank: list[dict]) -> dict | None:
    """Pick the next interest item, or None if the bank is exhausted."""
    agg = _aggregates(state, bank)

    under_seeded = [d for d in RIASEC_DIMS if agg[d]["n"] < SEED_PER_DIM]
    if under_seeded:
        dim = min(under_seeded, key=lambda d: (agg[d]["n"], d))
    else:
        order = sorted(RIASEC_DIMS, key=lambda d: (-agg[d]["mean"], d))
        candidate: str | None = None
        best_key: tuple[float, float, float] | None = None
        for i in (0, 1, 2):
            pair_p = _pair_prob(agg, order[i], order[i + 1])
            for idx in (i, i + 1):
                d = order[idx]
                if not _available(state, bank, d):
                    continue
                key = (pair_p, -agg[d]["se"], agg[d]["n"])
                if best_key is None or key < best_key:
                    best_key, candidate = key, d
        if candidate is None:
            avail = [d for d in RIASEC_DIMS if _available(state, bank, d)]
            if not avail:
                return None
            candidate = max(avail, key=lambda d: (agg[d]["se"], -agg[d]["n"]))
        dim = candidate

    items = _available(state, bank, dim)
    if not items:
        return None
    theta = (agg[dim]["mean"] + 1) / 2  # current normalised score for this dimension
    items.sort(key=lambda it: (abs(it.get("difficulty", 0.5) - theta), it["id"]))
    return items[0]


def interest_answered_count(state: dict) -> int:
    return len(state["interest_responses"])


def is_interest_complete(state: dict, bank: list[dict]) -> bool:
    """Stop the adaptive section on confidence, target, hard cap, or exhaustion."""
    n = interest_answered_count(state)
    if n >= HARD_CAP or n >= TARGET_ITEMS:
        return True
    if next_interest_item(state, bank) is None:
        return True
    return ordering_confidence(state, bank) >= CONF_STOP


def _recompute(state: dict, bank: list[dict], aptitude_bank: list[dict] | None) -> None:
    state["riasec"] = scoring.interest_scores(state["interest_responses"], bank)
    state["top3_code"] = scoring.top3_code(state["riasec"])
    state["confidence"] = ordering_confidence(state, bank)
    if aptitude_bank is not None:
        state["aptitude"] = scoring.aptitude_scores(state["aptitude_responses"], aptitude_bank)
    state["items_answered"] = (
        len(state["interest_responses"]) + len(state["aptitude_responses"])
    )


def record_interest_answer(
    state: dict, bank: list[dict], item_id: str, value: int
) -> dict[str, Any]:
    """Store a 1..5 interest answer (idempotent), recompute scores and advance phase."""
    item = next((it for it in bank if it["id"] == item_id), None)
    if item is None:
        raise ValueError(f"unknown interest item: {item_id}")
    if item_id not in state["interest_responses"]:
        if not 1 <= int(value) <= 5:
            raise ValueError("interest answer must be between 1 and 5")
        state["interest_responses"][item_id] = int(value)
    _recompute(state, bank, None)
    if is_interest_complete(state, bank):
        state["phase"] = "aptitude"
    return state


# --- aptitude ----------------------------------------------------------------
def next_aptitude_item(state: dict, aptitude_bank: list[dict]) -> dict | None:
    """Serve the aptitude items in fixed order; None once all are answered."""
    for item in aptitude_bank:
        if item["id"] not in state["aptitude_responses"]:
            return item
    return None


def _is_correct(answer: Any, correct: Any) -> bool:
    return str(answer).strip().casefold() == str(correct).strip().casefold()


def record_aptitude_answer(
    state: dict, bank: list[dict], aptitude_bank: list[dict], item_id: str, answer: Any
) -> dict[str, Any]:
    """Score one aptitude answer against the key and complete the session at the end."""
    item = next((it for it in aptitude_bank if it["id"] == item_id), None)
    if item is None:
        raise ValueError(f"unknown aptitude item: {item_id}")
    if item_id not in state["aptitude_responses"]:
        state["aptitude_responses"][item_id] = _is_correct(answer, item["answer"])
    _recompute(state, bank, aptitude_bank)
    if len(state["aptitude_responses"]) >= len(aptitude_bank):
        state["phase"] = "done"
        state["status"] = "completed"
    return state


# --- top-level driver --------------------------------------------------------
def next_item(state: dict, bank: list[dict], aptitude_bank: list[dict]) -> dict | None:
    """Return the next item to show (with a `section` marker), or None if finished."""
    if state["phase"] == "interest" and not is_interest_complete(state, bank):
        item = next_interest_item(state, bank)
        if item is not None:
            return {**item, "section": "interest"}
        state["phase"] = "aptitude"
    if state["phase"] == "aptitude":
        item = next_aptitude_item(state, aptitude_bank)
        if item is not None:
            return {**item, "section": "aptitude"}
    return None
