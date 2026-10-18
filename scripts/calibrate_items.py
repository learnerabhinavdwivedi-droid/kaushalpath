"""2PL IRT Calibration pipeline for KaushalPath Assessment v2 (Phase 21).

Fits a 2-Parameter Logistic (2PL) Item Response Theory model:
    P(Y_ij = 1 | theta_i, a_j, b_j) = 1 / (1 + exp(-a_j * (theta_i - b_j)))

Using Marginal Maximum Likelihood (MML) via Expectation-Maximization (EM)
with Gauss-Hermite / normal quadrature nodes over theta ~ N(0, 1).

Requirements:
- Pure numpy / scikit-learn / scipy.
- Generates:
    backend/app/ml/assessment/items_v2/interest_items.calibrated.json
    backend/app/ml/assessment/items_v2/aptitude_items.calibrated.json
- Items with n < 300 keep their prior (a=1.0, b=prior_difficulty) and calibrated=False.
- Items with n >= 300 store calibrated a, b, n and calibrated=True.
- Includes a simulation mode for parameter recovery verification (|est - true| <= 0.25).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize

ITEMS_V2_DIR = Path("backend/app/ml/assessment/items_v2")
DEFAULT_INTEREST_IN = ITEMS_V2_DIR / "interest_items.json"
DEFAULT_APTITUDE_IN = ITEMS_V2_DIR / "aptitude_items.json"
DEFAULT_INTEREST_OUT = ITEMS_V2_DIR / "interest_items.calibrated.json"
DEFAULT_APTITUDE_OUT = ITEMS_V2_DIR / "aptitude_items.calibrated.json"

MIN_CALIBRATION_N = 300


def sigmoid(z: np.ndarray) -> np.ndarray:
    z_clipped = np.clip(z, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z_clipped))


class TwoPLCalibrator:
    """Marginal Maximum Likelihood 2PL Item Response Theory Estimator."""

    def __init__(self, n_quad: int = 21, quad_range: float = 3.5):
        # Quadrature nodes and weights approximating N(0, 1)
        self.theta_nodes = np.linspace(-quad_range, quad_range, n_quad)
        densities = np.exp(-0.5 * self.theta_nodes**2) / np.sqrt(2 * np.pi)
        self.weights = densities / np.sum(densities)

    def fit(
        self,
        responses: np.ndarray,
        priors_a: np.ndarray | None = None,
        priors_b: np.ndarray | None = None,
        max_iter: int = 35,
        tol: float = 1e-4,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Fit 2PL parameters (a, b) for J items given an N x J binary response matrix.

        NaN in responses denotes missing / not-administered item.
        Returns:
            a: array of shape (J,) - item discriminations
            b: array of shape (J,) - item difficulties
        """
        N, J = responses.shape
        K = len(self.theta_nodes)

        # Initialize a and b from priors or defaults
        a = np.ones(J, dtype=np.float64) if priors_a is None else np.array(priors_a, dtype=np.float64)
        b = np.zeros(J, dtype=np.float64) if priors_b is None else np.array(priors_b, dtype=np.float64)

        for _iteration in range(max_iter):
            old_params = np.concatenate([a, b])

            # --- E-step: Posterior P(theta_k | Y_i) ---
            # P_jk = P(Y = 1 | theta_k, a_j, b_j) shape (J, K)
            P_jk = sigmoid(a[:, None] * (self.theta_nodes[None, :] - b[:, None]))
            P_jk = np.clip(P_jk, 1e-7, 1.0 - 1e-7)

            # Log-likelihood of responses for each respondent i at node k: shape (N, K)
            log_L = np.zeros((N, K), dtype=np.float64)
            for j in range(J):
                resp_j = responses[:, j]
                mask_obs = ~np.isnan(resp_j)
                if not np.any(mask_obs):
                    continue
                y_obs = resp_j[mask_obs, None]  # shape (N_obs, 1)
                p_obs = P_jk[j, None, :]        # shape (1, K)
                # Likelihood contribution
                term = y_obs * np.log(p_obs) + (1.0 - y_obs) * np.log(1.0 - p_obs)
                log_L[mask_obs, :] += term

            # Posterior posterior_ik = L_ik * w_k / sum_k(L_ik * w_k)
            # Use log-sum-exp trick for numerical stability
            log_post = log_L + np.log(self.weights)[None, :]
            log_post_max = np.max(log_post, axis=1, keepdims=True)
            post_unnorm = np.exp(log_post - log_post_max)
            post_norm = post_unnorm / np.sum(post_unnorm, axis=1, keepdims=True)  # shape (N, K)

            # Expected counts r_jk (positive responses) and n_jk (total responses) at node k
            # For each item j:
            for j in range(J):
                mask_obs = ~np.isnan(responses[:, j])
                n_obs = np.sum(mask_obs)
                if n_obs < 10:
                    continue

                w_obs = post_norm[mask_obs, :]  # shape (N_obs, K)
                y_obs = responses[mask_obs, j][:, None]  # shape (N_obs, 1)

                r_k = np.sum(y_obs * w_obs, axis=0)  # shape (K,)
                f_k = np.sum(w_obs, axis=0)          # shape (K,)

                # --- M-step: Newton / L-BFGS for item j ---
                def neg_log_lik(params, r_k=r_k, f_k=f_k):
                    aj, bj = params
                    p_k = sigmoid(aj * (self.theta_nodes - bj))
                    p_k = np.clip(p_k, 1e-7, 1.0 - 1e-7)
                    ll = np.sum(r_k * np.log(p_k) + (f_k - r_k) * np.log(1.0 - p_k))
                    # Weak regularisation priors to stabilize estimates
                    prior_a = -0.5 * ((aj - 1.0) / 0.5) ** 2
                    prior_b = -0.5 * (bj / 1.5) ** 2
                    return -(ll + prior_a + prior_b)

                res = minimize(
                    neg_log_lik,
                    x0=[a[j], b[j]],
                    bounds=[(0.3, 3.0), (-3.0, 3.0)],
                    method="L-BFGS-B",
                )
                if res.success:
                    a[j], b[j] = res.x

            new_params = np.concatenate([a, b])
            diff = np.max(np.abs(new_params - old_params))
            if diff < tol:
                break

        return a, b


def simulate_data(
    n_respondents: int,
    true_a: np.ndarray,
    true_b: np.ndarray,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate response matrix from known 2PL parameters and standard normal thetas."""
    rng = np.random.default_rng(seed)
    thetas = rng.normal(0.0, 1.0, size=n_respondents)
    J = len(true_a)
    probs = sigmoid(true_a[None, :] * (thetas[:, None] - true_b[None, :]))
    responses = (rng.uniform(0.0, 1.0, size=(n_respondents, J)) < probs).astype(np.float64)
    return responses, thetas


def run_parameter_recovery_test(n_respondents: int = 2000, seed: int = 2026) -> dict[str, Any]:
    """Verify that 2PL calibration recovers known a and b parameters within +/- 0.25."""
    rng = np.random.default_rng(seed)
    J = 12
    # Known realistic ground-truth parameters
    true_a = np.round(rng.uniform(0.8, 1.5, size=J), 2)
    true_b = np.round(rng.uniform(-1.0, 1.0, size=J), 2)

    responses, _ = simulate_data(n_respondents, true_a, true_b, seed=seed)

    calibrator = TwoPLCalibrator(n_quad=25)
    est_a, est_b = calibrator.fit(responses, priors_a=np.ones(J), priors_b=np.zeros(J))

    max_err_a = float(np.max(np.abs(est_a - true_a)))
    max_err_b = float(np.max(np.abs(est_b - true_b)))
    passed = max_err_a <= 0.25 and max_err_b <= 0.25

    return {
        "passed": passed,
        "n_respondents": n_respondents,
        "max_err_a": round(max_err_a, 4),
        "max_err_b": round(max_err_b, 4),
        "true_a": true_a.tolist(),
        "est_a": np.round(est_a, 2).tolist(),
        "true_b": true_b.tolist(),
        "est_b": np.round(est_b, 2).tolist(),
    }


def calibrate_item_bank(
    input_path: Path,
    output_path: Path,
    response_data: dict[str, list[int]] | None = None,
) -> None:
    """Calibrate an item bank and write to *.calibrated.json."""
    with input_path.open(encoding="utf-8") as f:
        items = json.load(f)

    calibrated_items = []
    for item in items:
        item_id = item["id"]
        prior_b = item.get("difficulty", 0.5)
        # Map [0, 1] difficulty onto IRT logit scale [-2, 2]
        prior_b_logit = (prior_b - 0.5) * 4.0
        prior_a = item.get("discrimination", 1.0)

        # Check empirical responses if available
        resp_list = response_data.get(item_id, []) if response_data else []
        n_resp = len(resp_list)

        if n_resp >= MIN_CALIBRATION_N:
            # Fit single-item MML against empirical data
            y_arr = np.array(resp_list, dtype=np.float64).reshape(-1, 1)
            calibrator = TwoPLCalibrator()
            fit_a, fit_b = calibrator.fit(y_arr, priors_a=np.array([prior_a]), priors_b=np.array([prior_b_logit]))
            est_a = float(round(fit_a[0], 3))
            est_b = float(round(fit_b[0], 3))
            is_calibrated = True
        else:
            est_a = float(round(prior_a, 3))
            est_b = float(round(prior_b_logit, 3))
            is_calibrated = False

        cal_item = dict(item)
        cal_item["a"] = est_a
        cal_item["b"] = est_b
        cal_item["n"] = n_resp
        cal_item["calibrated"] = is_calibrated
        calibrated_items.append(cal_item)

    output_path.write_text(json.dumps(calibrated_items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote calibrated bank ({len(calibrated_items)} items) -> {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate Assessment v2 Item Banks")
    parser.add_argument("--simulate", action="store_true", help="Run 2,000 respondent parameter recovery test")
    parser.add_argument("--interest-in", type=Path, default=DEFAULT_INTEREST_IN)
    parser.add_argument("--aptitude-in", type=Path, default=DEFAULT_APTITUDE_IN)
    parser.add_argument("--interest-out", type=Path, default=DEFAULT_INTEREST_OUT)
    parser.add_argument("--aptitude-out", type=Path, default=DEFAULT_APTITUDE_OUT)
    args = parser.parse_args()

    if args.simulate:
        print("Running parameter recovery simulation (N=2,000 respondents)...")
        res = run_parameter_recovery_test()
        print(f"Parameter recovery passed: {res['passed']}")
        print(f"Max error in discrimination (a): {res['max_err_a']} (target <= 0.25)")
        print(f"Max error in difficulty (b):     {res['max_err_b']} (target <= 0.25)")
        return 0 if res["passed"] else 1

    calibrate_item_bank(args.interest_in, args.interest_out)
    calibrate_item_bank(args.aptitude_in, args.aptitude_out)
    print("SUCCESS: Calibration pipeline executed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
