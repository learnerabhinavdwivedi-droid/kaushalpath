"""CAT engine — Maximum Fisher Information (MFI) item selection, MAP ability estimation (Newton-Raphson, N(0,1) prior), SEM-based early stopping. Targets 15-20 items total (12-18 RIASEC interest + 4-6 adaptive aptitude)."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.ml.assessment import scoring

RIASEC_DIMS = scoring.RIASEC_DIMS
APTITUDE_DIMS = scoring.APTITUDE_DIMS

MIN_ITEMS = 12          # minimum interest items before SEM stop can fire
HARD_CAP = 18           # absolute maximum interest items
SEM_STOP = 0.35         # stop when mean SEM of top-3 dims drops below this
CONF_STOP = 0.70        # Legacy alias for test compatibility
TARGET_ITEMS = 18       # Target interest items count
MAX_APTITUDE = 6        # maximum aptitude items (3 per top-2 dimension)
IRT_A = 1.0             # fixed discrimination for 2PL model
IRT_PRIOR_SD = 1.0      # SD of N(0,1) prior for MAP estimation
SEED_PER_DIM = 1

APTITUDE_TO_RIASEC = {"verbal": "I", "spatial": "R", "num": "C", "mech": "R"}

_BANK_DIR = Path(__file__).parent


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
        "theta": {d: 0.0 for d in RIASEC_DIMS},
        "riasec_posterior": {},
        "item_bs": {d: [] for d in RIASEC_DIMS}
    }


def ensure_state(state: dict[str, Any], bank: list[dict] | None = None) -> dict[str, Any]:
    """Ensure state dict has all required CAT fields, gracefully migrating legacy sessions."""
    defaults = new_state()
    for k, v in defaults.items():
        if k not in state:
            state[k] = v.copy() if isinstance(v, (dict, list)) else v
    if "theta" not in state or not isinstance(state["theta"], dict):
        state["theta"] = {d: 0.0 for d in RIASEC_DIMS}
    else:
        for d in RIASEC_DIMS:
            state["theta"].setdefault(d, 0.0)
    if "item_bs" not in state or not isinstance(state["item_bs"], dict):
        state["item_bs"] = {d: [] for d in RIASEC_DIMS}
    else:
        for d in RIASEC_DIMS:
            state["item_bs"].setdefault(d, [])
    if "interest_responses" not in state:
        state["interest_responses"] = {}
    if "aptitude_responses" not in state:
        state["aptitude_responses"] = {}

    # If state has interest responses but item_bs is unpopulated, reconstruct item_bs and thetas
    if state["interest_responses"] and not any(state["item_bs"].values()) and bank is not None:
        for i_id, i_val in state["interest_responses"].items():
            it = next((x for x in bank if x["id"] == i_id), None)
            if it:
                dim = it["dimension"]
                b = _irt_b(it.get("difficulty", 0.5))
                state["item_bs"][dim].append(b)
        for d in RIASEC_DIMS:
            responses = []
            for i_id, i_val in state["interest_responses"].items():
                it = next((x for x in bank if x["id"] == i_id), None)
                if it and it["dimension"] == d:
                    b = _irt_b(it.get("difficulty", 0.5))
                    is_correct = scoring.signed(i_val, it.get("reverse", False)) > 0
                    responses.append((b, is_correct))
            if responses:
                state["theta"][d] = _map_update(state["theta"][d], responses)
    return state


def _irt_b(difficulty: float) -> float:
    return (difficulty - 0.5) * 6.0


def _irt_p(theta: float, b: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-IRT_A * (theta - b)))
    except OverflowError:
        return 0.0 if (theta - b) < 0 else 1.0


def _fisher(theta: float, b: float) -> float:
    P = _irt_p(theta, b)
    return (IRT_A**2) * P * (1.0 - P)


def _map_update(theta: float, responses: list[tuple[float, bool]]) -> float:
    for _ in range(20):
        L_prime = -theta / (IRT_PRIOR_SD**2)
        L_double_prime = -1.0 / (IRT_PRIOR_SD**2)
        for b, is_correct in responses:
            P = _irt_p(theta, b)
            L_prime += IRT_A * (int(is_correct) - P)
            L_double_prime -= (IRT_A**2) * P * (1.0 - P)
        
        delta = L_prime / L_double_prime
        theta -= delta
        if abs(delta) < 0.001:
            break
    return theta


def _sem(theta: float, item_bs: list[float]) -> float:
    return 1.0 / math.sqrt(sum(_fisher(theta, b) for b in item_bs) + 1e-9)


def ordering_confidence(state: dict, bank: list[dict]) -> float:
    ensure_state(state, bank)
    if not state.get("interest_responses"):
        return 0.0
    order = sorted(RIASEC_DIMS, key=lambda d: state["theta"].get(d, 0.0), reverse=True)
    top3_sem = [_sem(state["theta"].get(d, 0.0), state["item_bs"].get(d, [])) for d in order[:3]]
    mean_sem = sum(top3_sem) / 3 if top3_sem else 1.0
    return max(0.0, min(1.0, 1.0 - mean_sem))


def _available(state: dict, bank: list[dict], dim: str) -> list[dict]:
    return [
        it
        for it in bank
        if it["dimension"] == dim and it["id"] not in state["interest_responses"]
    ]


def next_interest_item(state: dict, bank: list[dict]) -> dict | None:
    ensure_state(state, bank)
    for d in RIASEC_DIMS:
        answered = len(state["item_bs"][d])
        if answered < SEED_PER_DIM:
            avail = _available(state, bank, d)
            if avail:
                theta_d = state["theta"][d]
                return max(avail, key=lambda it: _fisher(theta_d, _irt_b(it.get("difficulty", 0.5))))
    
    best_item = None
    max_info = -1.0
    for d in RIASEC_DIMS:
        avail = _available(state, bank, d)
        theta_d = state["theta"][d]
        for it in avail:
            b = _irt_b(it.get("difficulty", 0.5))
            info = _fisher(theta_d, b)
            if info > max_info:
                max_info = info
                best_item = it
    return best_item


def is_interest_complete(state: dict, bank: list[dict]) -> bool:
    ensure_state(state, bank)
    items_answered = len(state["interest_responses"])
    if items_answered >= HARD_CAP:
        return True
    if next_interest_item(state, bank) is None:
        return True
    if items_answered >= MIN_ITEMS:
        order = sorted(RIASEC_DIMS, key=lambda d: state["theta"][d], reverse=True)
        top3_sem = [_sem(state["theta"][d], state["item_bs"][d]) for d in order[:3]]
        mean_sem = sum(top3_sem) / 3
        if mean_sem < SEM_STOP:
            return True
    return False


def _recompute(state: dict, bank: list[dict], aptitude_bank: list[dict] | None) -> None:
    def sigmoid(x: float) -> float:
        try:
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    state["riasec"] = {d: sigmoid(state["theta"][d]) for d in RIASEC_DIMS}
    
    posterior = {}
    for d in RIASEC_DIMS:
        theta_d = state["theta"][d]
        item_bs_d = state["item_bs"][d]
        posterior[d] = {
            "mean": theta_d,
            "sd": _sem(theta_d, item_bs_d),
            "prob": sigmoid(theta_d)
        }
    state["riasec_posterior"] = posterior

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
    ensure_state(state, bank)
    item = next((it for it in bank if it["id"] == item_id), None)
    if item is None:
        raise ValueError(f"unknown interest item: {item_id}")
    if item_id not in state["interest_responses"]:
        val_int = int(value)
        if not 1 <= val_int <= 5:
            raise ValueError("interest answer must be between 1 and 5")
        state["interest_responses"][item_id] = val_int
        
        dim = item["dimension"]
        b_param = _irt_b(item.get("difficulty", 0.5))
        state["item_bs"][dim].append(b_param)
        
        responses = []
        for i_id, i_val in state["interest_responses"].items():
            it = next(x for x in bank if x["id"] == i_id)
            if it["dimension"] == dim:
                b = _irt_b(it.get("difficulty", 0.5))
                is_correct = scoring.signed(i_val, it.get("reverse", False)) > 0
                responses.append((b, is_correct))
        state["theta"][dim] = _map_update(state["theta"][dim], responses)

    _recompute(state, bank, None)
    if is_interest_complete(state, bank):
        state["phase"] = "aptitude"
    return state


def next_aptitude_item(state: dict, aptitude_bank: list[dict]) -> dict | None:
    ensure_state(state)
    if len(state["aptitude_responses"]) >= MAX_APTITUDE:
        return None
        
    order = sorted(RIASEC_DIMS, key=lambda d: state["theta"].get(d, 0.0), reverse=True)
    target_apt_dims = []
    for d in order:
        for apt, ria in APTITUDE_TO_RIASEC.items():
            if ria == d and apt not in target_apt_dims:
                target_apt_dims.append(apt)
        if len(target_apt_dims) >= 2:
            break
    target_apt_dims = target_apt_dims[:2]
    
    for apt_dim in target_apt_dims:
        items = [it for it in aptitude_bank if it["dimension"] == apt_dim]
        items.sort(key=lambda x: x.get("difficulty", 0.0), reverse=True)
        top3 = items[:3]
        top3.sort(key=lambda x: x.get("difficulty", 0.0))
        for it in top3:
            if it["id"] not in state["aptitude_responses"]:
                return it
    return None


def _is_correct(answer: Any, correct: Any) -> bool:
    return str(answer).strip().casefold() == str(correct).strip().casefold()


def record_aptitude_answer(
    state: dict, bank: list[dict], aptitude_bank: list[dict], item_id: str, answer: Any
) -> dict[str, Any]:
    ensure_state(state, bank)
    item = next((it for it in aptitude_bank if it["id"] == item_id), None)
    if item is None:
        raise ValueError(f"unknown aptitude item: {item_id}")
    if item_id not in state["aptitude_responses"]:
        state["aptitude_responses"][item_id] = _is_correct(answer, item["answer"])
    _recompute(state, bank, aptitude_bank)
    if next_aptitude_item(state, aptitude_bank) is None:
        state["phase"] = "done"
        state["status"] = "completed"
    return state


def next_item(state: dict, bank: list[dict], aptitude_bank: list[dict]) -> dict | None:
    ensure_state(state, bank)
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
