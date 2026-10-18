"""Adaptive test engine (Phase 21 - Assessment v2 — Akinator-style).

A session is a plain, JSON-serialisable dict so it can be persisted on
``assessments.state_json`` and resumed across API calls. The engine is pure:
it never touches the DB or FastAPI — `services/assessment_svc.py` wires it up.

Phases:
1. interest  — adaptive RIASEC with Akinator-style dimension elimination
2. tie_break — up to 2 forced-choice pairs when top-3 are within 1 SEM
3. aptitude  — 4-construct adaptive ladder (3 items per construct, stop early)

Akinator strategy (interest): Instead of asking all 6 dimensions equally,
we seed 1 item per dimension, then focus on dimensions whose rank is
uncertain (the "boundary" between top-3 and bottom-3). Dimensions that
are confidently in the top-3 or confidently in the bottom-3 are
"eliminated" — we stop asking about them, just like Akinator eliminates
impossible characters. This cuts interest questions from ~24 to ~12-15.

Stop rules (interest): >=1 item seeded per dimension, then keep asking the
dimension that most sharpens the top-3 ordering until ordering confidence
>= 0.92, or 12 items asked, or the 18-item hard cap.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.ml.assessment import scoring

RIASEC_DIMS = scoring.RIASEC_DIMS
APTITUDE_DIMS = scoring.APTITUDE_DIMS

# --- Akinator-tuned parameters -----------------------------------------------
SEED_PER_DIM = 1  # just 1 item per dimension to seed (was 2)
TARGET_ITEMS = 12  # soft target for interest phase (was 24)
HARD_CAP = 18  # never ask more than this for interest + tie-breaks (was 30)
CONF_STOP = 0.92  # ordering-confidence threshold (was 0.95, relaxed slightly)
MAX_TIE_BREAKS = 2  # maximum forced-choice tie-break pairs (was 3)
_EPS = 1e-6

_BANK_DIR = Path(__file__).parent
_PRIOR_SD = 0.5  # assumed spread before we see item-to-item variance
_EVIDENCE_FULL = 3  # items per dimension at which evidence is considered complete (was 4)

# Dimension elimination thresholds
_ELIM_CONF = 0.88  # confidence that a dim is NOT in top-3 to eliminate it
_MIN_ITEMS_BEFORE_ELIM = 2  # need at least 2 answers before eliminating a dim

# Aptitude adaptive parameters
MAX_APTITUDE_PER_CONSTRUCT = 3  # reduced from 5
MAX_APTITUDE_SERVED = MAX_APTITUDE_PER_CONSTRUCT * len(APTITUDE_DIMS)  # 12 items (was 20)


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
        "eliminated_dims": [],  # Akinator-style: dims confidently NOT in top-3
    }


# --- interest aggregates -----------------------------------------------------
def _aggregates(state: dict, bank: list[dict]) -> dict[str, dict[str, float]]:
    """Per-dimension running count, mean (signed [-1,1]) and standard error."""
    xs: dict[str, list[float]] = {d: [] for d in RIASEC_DIMS}
    for item in bank:
        value = state["interest_responses"].get(item["id"])
        if value is not None and isinstance(value, int | float):
            xs[item["dimension"]].append(scoring.signed(value, item.get("reverse", False)))
    agg: dict[str, dict[str, float]] = {}
    pair_adj = state.get("pair_adjustments", {})
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


# --- Akinator-style dimension elimination ------------------------------------
def _update_eliminated(state: dict, bank: list[dict]) -> None:
    """Mark dimensions that are confidently NOT in the top-3 — stop asking them.

    Like Akinator eliminates impossible characters, we eliminate dimensions
    that cannot realistically enter the top-3 code, so we never waste
    questions on them again.
    """
    agg = _aggregates(state, bank)
    order = sorted(RIASEC_DIMS, key=lambda d: (-agg[d]["mean"], d))
    eliminated = list(state.get("eliminated_dims", []))

    for dim in order[3:]:  # only bottom-3 candidates for elimination
        if dim in eliminated:
            continue
        if agg[dim]["n"] < _MIN_ITEMS_BEFORE_ELIM:
            continue
        # Check: is this dim confidently below ALL current top-3?
        probs = [_pair_prob(agg, top_d, dim) for top_d in order[:3]]
        if all(p >= _ELIM_CONF for p in probs):
            eliminated.append(dim)

    state["eliminated_dims"] = eliminated


def ordering_confidence(state: dict, bank: list[dict]) -> float:
    """Confidence in the top-3 Holland code."""
    agg = _aggregates(state, bank)
    total = sum(a["n"] for a in agg.values())
    if total < SEED_PER_DIM * len(RIASEC_DIMS) - 1:
        return _clamp(total / (SEED_PER_DIM * len(RIASEC_DIMS)) * 0.5)
    order = sorted(RIASEC_DIMS, key=lambda d: (-agg[d]["mean"], d))

    # set separation: the rank-3 dimension above every dimension outside top-3
    set_conf = min(_pair_prob(agg, order[2], d) for d in order[3:])

    # Evidence factor: how many of the active dims have enough data
    active_dims = [d for d in RIASEC_DIMS if d not in state.get("eliminated_dims", [])]
    evidence = sum(min(1.0, agg[d]["n"] / _EVIDENCE_FULL) for d in active_dims) / max(len(active_dims), 1)

    # Eliminated dims boost: each eliminated dim adds certainty
    elim_bonus = len(state.get("eliminated_dims", [])) * 0.03

    return _clamp(0.80 * set_conf + 0.15 * evidence + 0.05 + elim_bonus)


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


def _information_gain(agg: dict, dim: str, order: list[str]) -> float:
    """Estimate how much asking another item in `dim` would reduce uncertainty.

    Higher = more informative = ask this dimension next. This is the core
    of the Akinator strategy: focus questions where they matter most.
    """
    rank = order.index(dim)

    # Boundary dimensions (rank 2 and 3 — the top-3/bottom-3 boundary) are highest value
    if rank in (2, 3):
        boundary_value = 3.0
    elif rank in (1, 4):
        boundary_value = 1.5
    else:
        boundary_value = 0.5

    # High SE = high uncertainty = high info gain
    se_value = agg[dim]["se"]

    # Fewer items answered = more to learn
    sparsity = 1.0 / (agg[dim]["n"] + 1)

    return boundary_value * se_value * (1.0 + sparsity)


def next_interest_item(state: dict, bank: list[dict]) -> dict | None:
    """Pick the next interest item using Akinator-style elimination + IRT.

    Strategy:
    1. Seed phase: ask 1 item per dimension (6 questions)
    2. Elimination phase: focus on boundary dimensions, skip eliminated ones
    3. Pick the highest-discrimination item closest to current theta
    """
    agg = _aggregates(state, bank)
    eliminated = set(state.get("eliminated_dims", []))

    # Phase 1: Seed — ensure every non-eliminated dim has at least SEED_PER_DIM
    under_seeded = [d for d in RIASEC_DIMS if d not in eliminated and agg[d]["n"] < SEED_PER_DIM]
    if under_seeded:
        dim = min(under_seeded, key=lambda d: (agg[d]["n"], d))
    else:
        # Phase 2: Akinator elimination — focus on the boundary
        order = sorted(RIASEC_DIMS, key=lambda d: (-agg[d]["mean"], d))
        active_dims = [d for d in RIASEC_DIMS if d not in eliminated]

        # Score each active dimension by information gain
        scored: list[tuple[float, str]] = []
        for d in active_dims:
            if not _available(state, bank, d):
                continue
            gain = _information_gain(agg, d, order)
            scored.append((gain, d))

        if not scored:
            # All active dims exhausted
            avail = [d for d in RIASEC_DIMS if _available(state, bank, d)]
            if not avail:
                return None
            dim = max(avail, key=lambda d: (agg[d]["se"], -agg[d]["n"]))
        else:
            # Pick dimension with highest information gain
            scored.sort(key=lambda x: -x[0])
            dim = scored[0][1]

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

    # Akinator step: try to eliminate dimensions after each answer
    _update_eliminated(state, bank)

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
def _aptitude_difficulty(item: dict) -> int:
    """Extract ASER band / difficulty tier (1=easiest, 4=hardest)."""
    return int(item.get("aser_band", item.get("difficulty_tier", 2)))


def _should_stop_construct(state: dict, construct: str, aptitude_bank: list[dict]) -> bool:
    """Adaptive stop: if student got first 2 right → skip 3rd (ceiling).
    If student got first 2 wrong → skip 3rd (floor). Only stop early
    when the first 2 answers are consistent (both right or both wrong).
    """
    answered_items = []
    for it in aptitude_bank:
        c = it.get("construct") or it.get("dimension", "")
        if c == construct and it["id"] in state["aptitude_responses"]:
            answered_items.append(state["aptitude_responses"][it["id"]])

    if len(answered_items) >= 2:
        # If all answers so far agree (all correct or all incorrect), ceiling/floor reached
        if all(answered_items) or not any(answered_items):
            return True
    return False


def next_aptitude_item(state: dict, aptitude_bank: list[dict]) -> dict | None:
    """Serve aptitude ladder items adaptively (up to 3 per construct, with early stop)."""
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
            if answered_per_c.get(c, 0) < MAX_APTITUDE_PER_CONSTRUCT:
                # Adaptive stop: skip this construct if ceiling/floor reached
                if _should_stop_construct(state, c, aptitude_bank):
                    continue
                return item

    # No more items to serve (all constructs either maxed out or stopped early)
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
