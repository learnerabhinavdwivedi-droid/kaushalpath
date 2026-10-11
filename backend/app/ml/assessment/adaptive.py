"""Adaptive test engine (Phase 21 - Assessment v2).

A session is a plain, JSON-serialisable dict so it can be persisted on
``assessments.state_json`` and resumed across API calls. The engine is pure:
it never touches the DB or FastAPI — `services/assessment_svc.py` wires it up.

Phases:
1. interest  — adaptive RIASEC selection using calibrated IRT a & b parameters
2. tie_break — up to 3 forced-choice pairs when top-3 are within 1 SEM
3. aptitude  — 4-construct test (10+ items per construct across 4 ASER bands)

Stop rules (interest): >=2 items seeded per dimension, then keep asking the
dimension that most sharpens the top-3 ordering until ordering confidence
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
HARD_CAP = 30  # never ask more than this for interest + tie-breaks
CONF_STOP = 0.95  # ordering-confidence threshold to stop early
MAX_TIE_BREAKS = 3  # maximum forced-choice tie-break pairs
_EPS = 1e-6

_BANK_DIR = Path(__file__).parent
_PRIOR_SD = 0.5  # assumed spread before we see item-to-item variance
_EVIDENCE_FULL = 4  # items per dimension at which evidence is considered complete


def load_interest_bank(path: Path | None = None) -> list[dict]:
    """Load the RIASEC item bank (prefers items_v2 calibrated > items_v2 > legacy)."""
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    v2_cal = _BANK_DIR / "items_v2" / "interest_items.calibrated.json"
    if v2_cal.exists():
        return json.loads(v2_cal.read_text(encoding="utf-8"))
    v2_raw = _BANK_DIR / "items_v2" / "interest_items.json"
    if v2_raw.exists():
        return json.loads(v2_raw.read_text(encoding="utf-8"))
    return json.loads((_BANK_DIR / "riasec_items.json").read_text(encoding="utf-8"))


def load_aptitude_bank(path: Path | None = None) -> list[dict]:
    """Load the aptitude item bank (prefers items_v2 calibrated > items_v2 > legacy)."""
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    v2_cal = _BANK_DIR / "items_v2" / "aptitude_items.calibrated.json"
    if v2_cal.exists():
        return json.loads(v2_cal.read_text(encoding="utf-8"))
    v2_raw = _BANK_DIR / "items_v2" / "aptitude_items.json"
    if v2_raw.exists():
        return json.loads(v2_raw.read_text(encoding="utf-8"))
    return json.loads((_BANK_DIR / "aptitude_items.json").read_text(encoding="utf-8"))


def new_state() -> dict[str, Any]:
    """A fresh, empty interest-first session snapshot (JSON-safe)."""
    return {
        "status": "in_progress",
        "phase": "interest",
        "interest_responses": {},  # item_id -> 1..5 or 1..3 or choice
        "aptitude_responses": {},  # item_id -> bool (correct?)
        "pair_adjustments": {d: 0.0 for d in RIASEC_DIMS},  # signed bonus/penalty from tie breaks
        "tie_breaks_asked": 0,
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
        if value is not None and isinstance(value, (int, float)):
            xs[item["dimension"]].append(scoring.signed(value, item.get("reverse", False)))
    agg: dict[str, dict[str, float]] = {}
    pair_adj = state.get("pair_adjustments", {})
    prior_var = _PRIOR_SD ** 2
    for dim, vals in xs.items():
        n = len(vals)
        base_mean = sum(vals) / n if n else 0.0
        # Add tie-break adjustment to the running mean
        adj = pair_adj.get(dim, 0.0)
        mean = max(-1.0, min(1.0, base_mean + adj))
        if n > 1:
            var = sum((x - base_mean) ** 2 for x in vals) / (n - 1)
            # Use empirical sample SD; if variance is zero (identical answers), floor at 0.15
            sd = math.sqrt(var) if var > 0.001 else 0.15
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
    """Confidence in the top-3 Holland code."""
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


def _item_difficulty_normalized(item: dict) -> float:
    """Extract normalized difficulty in [0, 1] from item.b or item.difficulty."""
    if "difficulty" in item:
        return float(item["difficulty"])
    b_val = float(item.get("b", 0.0))
    # If b is on logit scale [-3, 3] -> map to [0, 1]
    if -4.0 <= b_val <= 4.0:
        return _clamp(0.5 + b_val / 4.0, 0.05, 0.95)
    return _clamp(b_val, 0.0, 1.0)


def _item_discrimination(item: dict) -> float:
    """Extract discrimination parameter a from item."""
    return float(item.get("a", item.get("discrimination", 1.0)))


def next_interest_item(state: dict, bank: list[dict]) -> dict | None:
    """Pick the next interest item using per-item discrimination `a` and difficulty `b`."""
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

    # Sort available items by IRT Fisher information / distance weighted by discrimination a
    def item_key(it: dict) -> tuple[float, str]:
        diff = _item_difficulty_normalized(it)
        disc = _item_discrimination(it)
        # Closer difficulty and higher discrimination gives lowest distance score
        score = abs(diff - theta) / max(0.2, disc)
        return (score, it["id"])

    items.sort(key=item_key)
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


# --- Forced-Choice Tie-Break (Phase 21 Item D) -------------------------------
def find_contested_dimensions(state: dict, bank: list[dict]) -> tuple[str, str] | None:
    """Find two top dimensions within 1 SEM of each other after adaptive phase."""
    agg = _aggregates(state, bank)
    order = sorted(RIASEC_DIMS, key=lambda d: (-agg[d]["mean"], d))

    contested_pairs: list[tuple[float, str, str]] = []
    # Check top-3 pairs (0 vs 1, 1 vs 2) and boundary pair (2 vs 3)
    for i in (0, 1, 2):
        d_a, d_b = order[i], order[i + 1]
        diff = abs(agg[d_a]["mean"] - agg[d_b]["mean"])
        max_se = max(agg[d_a]["se"], agg[d_b]["se"])
        if diff <= max_se:
            # Within 1 SEM: contested! Keyed by diff relative to joint SE
            joint_se = math.sqrt(agg[d_a]["se"] ** 2 + agg[d_b]["se"] ** 2) + _EPS
            contested_pairs.append((diff / joint_se, d_a, d_b))

    if not contested_pairs:
        return None
    contested_pairs.sort(key=lambda x: x[0])
    return contested_pairs[0][1], contested_pairs[0][2]


def next_tie_break_item(state: dict, bank: list[dict]) -> dict | None:
    """Generate a forced-choice paired comparison item between contested dimensions."""
    pair = find_contested_dimensions(state, bank)
    if pair is None:
        return None
    dim_a, dim_b = pair
    tb_count = state.get("tie_breaks_asked", 0) + 1

    # Pick representative activities from dim_a and dim_b
    def pick_item(dim: str) -> dict:
        avail = _available(state, bank, dim)
        if avail:
            return avail[0]
        # If all answered, pick from bank for dim
        matching = [it for it in bank if it["dimension"] == dim]
        return matching[0]

    item_a = pick_item(dim_a)
    item_b = pick_item(dim_b)

    return {
        "id": f"PAIR_{dim_a}_{dim_b}_{tb_count}",
        "section": "interest",
        "item_type": "pair",
        "dim_a": dim_a,
        "dim_b": dim_b,
        "text_en": f"Which activity do you prefer? (A) {item_a['text_en']} OR (B) {item_b['text_en']}",
        "text_hi": f"आप कौन सा काम चुनेंगे? (क) {item_a.get('text_hi', item_a['text_en'])} या (ख) {item_b.get('text_hi', item_b['text_en'])}",
        "option_a": {"id": "A", "label": item_a["text_en"], "text_hi": item_a.get("text_hi", item_a["text_en"]), "dim": dim_a},
        "option_b": {"id": "B", "label": item_b["text_en"], "text_hi": item_b.get("text_hi", item_b["text_en"]), "dim": dim_b},
        "options": ["A", "B"],
    }


def _recompute(state: dict, bank: list[dict], aptitude_bank: list[dict] | None) -> None:
    state["riasec"] = scoring.interest_scores(
        state["interest_responses"], bank, state.get("pair_adjustments")
    )
    state["top3_code"] = scoring.top3_code(state["riasec"])
    state["confidence"] = ordering_confidence(state, bank)
    if aptitude_bank is not None:
        state["aptitude"] = scoring.aptitude_scores(state["aptitude_responses"], aptitude_bank)
    state["items_answered"] = (
        len(state["interest_responses"]) + len(state["aptitude_responses"])
    )


def record_interest_answer(
    state: dict, bank: list[dict], item_id: str, value: Any
) -> dict[str, Any]:
    """Store an interest answer (1..5, 1..3, or pair selection) and advance phase."""
    if item_id.startswith("PAIR_"):
        # Forced-choice tie break response: value can be 'A', 'B', '1', '2', or integer
        parts = item_id.split("_")
        dim_a = parts[1]
        dim_b = parts[2]
        str_val = str(value).strip().upper()
        if str_val in ("B", "2", "DISLIKE"):
            chosen_dim = dim_b
            rejected_dim = dim_a
        else:
            chosen_dim = dim_a
            rejected_dim = dim_b

        if "pair_adjustments" not in state:
            state["pair_adjustments"] = {d: 0.0 for d in RIASEC_DIMS}

        # Shift chosen dimension by +0.20 and rejected by -0.20 on signed scale
        state["pair_adjustments"][chosen_dim] += 0.20
        state["pair_adjustments"][rejected_dim] -= 0.20
        state["tie_breaks_asked"] = state.get("tie_breaks_asked", 0) + 1
        state["interest_responses"][item_id] = str_val
        _recompute(state, bank, None)

        if (
            state.get("tie_breaks_asked", 0) >= MAX_TIE_BREAKS
            or interest_answered_count(state) >= HARD_CAP
            or find_contested_dimensions(state, bank) is None
        ):
            state["phase"] = "aptitude"
        return state


    item = next((it for it in bank if it["id"] == item_id), None)
    if item is None:
        raise ValueError(f"unknown interest item: {item_id}")

    if item_id not in state["interest_responses"]:
        val_int = int(value)
        if not 1 <= val_int <= 5:
            raise ValueError("interest answer must be between 1 and 5 (or 1..3 for likert3)")
        state["interest_responses"][item_id] = val_int

    _recompute(state, bank, None)

    if is_interest_complete(state, bank):
        # Check if tie-break needed before entering aptitude
        if (
            state.get("tie_breaks_asked", 0) < MAX_TIE_BREAKS
            and interest_answered_count(state) < HARD_CAP
            and find_contested_dimensions(state, bank) is not None
        ):
            state["phase"] = "tie_break"
        else:
            state["phase"] = "aptitude"

    return state


# --- aptitude ----------------------------------------------------------------
MAX_APTITUDE_SERVED = 20  # 5 items x 4 constructs


def next_aptitude_item(state: dict, aptitude_bank: list[dict]) -> dict | None:
    """Serve aptitude ladder items (up to 20 items: 5 per construct); None once done."""
    if len(state["aptitude_responses"]) >= MAX_APTITUDE_SERVED:
        return None

    answered_per_c: dict[str, int] = {}
    for it in aptitude_bank:
        if it["id"] in state["aptitude_responses"]:
            c = it.get("construct") or it.get("dimension", "")
            answered_per_c[c] = answered_per_c.get(c, 0) + 1

    for item in aptitude_bank:
        if item["id"] not in state["aptitude_responses"]:
            c = item.get("construct") or item.get("dimension", "")
            if answered_per_c.get(c, 0) < 5:
                return item

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
    correct_key = item.get("correct_answer") or item.get("answer")
    if item_id not in state["aptitude_responses"]:
        state["aptitude_responses"][item_id] = _is_correct(answer, correct_key)
    _recompute(state, bank, aptitude_bank)
    if len(state["aptitude_responses"]) >= MAX_APTITUDE_SERVED or next_aptitude_item(state, aptitude_bank) is None:
        state["phase"] = "done"
        state["status"] = "completed"
    return state



# --- top-level driver --------------------------------------------------------
def next_item(state: dict, bank: list[dict], aptitude_bank: list[dict]) -> dict | None:
    """Return the next item to show (with a `section` marker), or None if finished."""
    if state["phase"] == "interest":
        if not is_interest_complete(state, bank):
            item = next_interest_item(state, bank)
            if item is not None:
                return {**item, "section": "interest", "item_type": item.get("item_type", "likert5")}
        # Check tie-break transition
        if (
            state.get("tie_breaks_asked", 0) < MAX_TIE_BREAKS
            and interest_answered_count(state) < HARD_CAP
            and find_contested_dimensions(state, bank) is not None
        ):
            state["phase"] = "tie_break"
        else:
            state["phase"] = "aptitude"

    if state["phase"] == "tie_break":
        tb_item = next_tie_break_item(state, bank)
        if (
            tb_item is not None
            and state.get("tie_breaks_asked", 0) < MAX_TIE_BREAKS
            and interest_answered_count(state) < HARD_CAP
        ):
            return tb_item
        state["phase"] = "aptitude"

    if state["phase"] == "aptitude":
        item = next_aptitude_item(state, aptitude_bank)
        if item is not None:
            return {**item, "section": "aptitude", "item_type": "mcq"}

    return None
