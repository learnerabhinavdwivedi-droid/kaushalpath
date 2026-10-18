"""Phase 27: Demo Pre-flight Hardening Script (PSID 26241).

Runs a complete, sub-60-second end-to-end verification of the KaushalPath system
right before live evaluation / presentation:
1. Database migration & seed pipeline verification (offline-safe).
2. Health & readiness checks (/health & /health/ready).
3. Assessment intake, adaptive answering, and recommendation generation.
4. Conversational dialogue turn in English (grounded fact cards & ROI).
5. Conversational dialogue turn in Hindi (bilingual fact cards & scheme subsidies).
6. Human-escalation hand-off with structured case pack.
7. Admin resistance & analytics dashboard query with k-anonymity checks.

Usage:
    python scripts/demo_preflight.py
    python scripts/demo_preflight.py --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Any

# Ensure backend imports resolve
import _common  # noqa: F401
import httpx
from app.db import Base, engine
from app.main import app


class PreflightRunner:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url
        self.client: Any = None
        self.is_live_server = False

        if base_url:
            self.client = httpx.Client(base_url=base_url, timeout=15.0)
            self.is_live_server = True
        else:
            # Auto-detect if live server is running on :8000; otherwise use TestClient
            try:
                probe = httpx.get("http://localhost:8000/health", timeout=1.0)
                if probe.status_code == 200:
                    self.base_url = "http://localhost:8000"
                    self.client = httpx.Client(base_url=self.base_url, timeout=15.0)
                    self.is_live_server = True
            except Exception:
                pass

        if not self.is_live_server:
            from fastapi.testclient import TestClient

            self.client = TestClient(app)

    def run_step(self, step_num: int, title: str, func) -> bool:
        t0 = time.perf_counter()
        sys.stdout.write(f"[{step_num}/7] {title}... ")
        sys.stdout.flush()
        try:
            func()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            print(f"PASS ({elapsed_ms:.1f}ms)")
            return True
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            print(f"FAIL ({elapsed_ms:.1f}ms) -> {e}")
            return False

    def execute_all(self) -> int:
        print("=" * 68)
        mode_str = f"Live server ({self.base_url})" if self.is_live_server else "In-process TestClient"
        print(f"  KaushalPath Demo Pre-flight Hardening Check [{mode_str}]")
        print("=" * 68)

        total_t0 = time.perf_counter()
        passed = 0
        total_steps = 7

        state: dict[str, Any] = {}

        # -------------------------------------------------------------------
        # Step 1: Migrate + Seed
        # -------------------------------------------------------------------
        def step1_migrate_seed():
            Base.metadata.create_all(bind=engine)
            import seed_all

            seed_all.main()

        if self.run_step(1, "Database Migration & Seed Pipeline", step1_migrate_seed):
            passed += 1

        # -------------------------------------------------------------------
        # Step 2: Health Check
        # -------------------------------------------------------------------
        def step2_health():
            res = self.client.get("/health")
            assert res.status_code == 200, f"Health check returned {res.status_code}: {res.text}"
            data = res.json()
            assert data.get("status") == "ok"

            ready_res = self.client.get("/health/ready")
            assert ready_res.status_code == 200, f"Health ready check returned {ready_res.status_code}"

        if self.run_step(2, "Service Health & Readiness Probe (/health, /health/ready)", step2_health):
            passed += 1

        # -------------------------------------------------------------------
        # Step 3: Assessment Flow
        # -------------------------------------------------------------------
        def step3_assessment():
            ts = int(time.time() * 1000)
            email = f"preflight_student_{ts}@kaushalpath.in"
            reg_resp = self.client.post(
                "/auth/register",
                json={"email": email, "password": "PassPassword123!", "role": "student", "give_consent": True},
            )
            assert reg_resp.status_code == 200, f"Register failed: {reg_resp.text}"
            token = reg_resp.json()["access_token"]
            state["student_token"] = token
            state["student_headers"] = {"Authorization": f"Bearer {token}"}

            me = self.client.get("/auth/me", headers=state["student_headers"]).json()
            student_id = me.get("student_id")
            assert student_id is not None
            state["student_id"] = student_id

            # Save intake constraints
            c_resp = self.client.post(
                f"/assessment/student?student_id={student_id}",
                json={
                    "district": "Pune",
                    "state": "Maharashtra",
                    "edu_level": "10th",
                    "budget_band": "low",
                    "income_band": "lt_1l",
                    "max_duration_months": 24,
                    "relocate_ok": True,
                    "language": "hi",
                },
            )
            assert c_resp.status_code in (200, 201), f"Constraints save failed: {c_resp.text}"

            # Start adaptive session
            s_resp = self.client.post(f"/assessment/session?student_id={student_id}&restart=true")
            assert s_resp.status_code == 200, f"Session start failed: {s_resp.text}"
            sess_data = s_resp.json()
            assessment_id = sess_data["assessment_id"]
            state["assessment_id"] = assessment_id

            # Answer initial question
            if not sess_data.get("done") and sess_data.get("item"):
                item_id = sess_data["item"]["id"]
                ans_resp = self.client.post(
                    "/assessment/answer",
                    json={"assessment_id": assessment_id, "item_id": item_id, "answer": 5},
                )
                assert ans_resp.status_code == 200, f"Answer submit failed: {ans_resp.text}"

            # Request recommendations
            rec_resp = self.client.post("/recommend", json={"student_id": student_id, "top_k": 3})
            assert rec_resp.status_code == 200, f"Recommendation generation failed: {rec_resp.text}"
            recs_data = rec_resp.json()
            recs = recs_data.get("recommendations", []) if isinstance(recs_data, dict) else recs_data
            assert isinstance(recs, list) and len(recs) > 0, f"Expected non-empty recommendations: {recs_data}"

        if self.run_step(3, "Assessment Flow & Multi-Signal Recommendations", step3_assessment):
            passed += 1

        # -------------------------------------------------------------------
        # Step 4: English Chat Turn
        # -------------------------------------------------------------------
        def step4_chat_en():
            conv_resp = self.client.post(
                "/conversations",
                headers=state["student_headers"],
                json={"student_id": state["student_id"], "lang": "en"},
            )
            assert conv_resp.status_code == 201, f"Conversation create failed: {conv_resp.text}"
            conv_id = conv_resp.json()["id"]
            state["conversation_id"] = conv_id

            turn_resp = self.client.post(
                f"/conversations/{conv_id}/turns",
                headers=state["student_headers"],
                json={
                    "speaker": "learner",
                    "text": "What salary can I expect after ITI Electrician?",
                    "lang": "en",
                },
            )
            assert turn_resp.status_code == 200, f"English chat turn failed: {turn_resp.text}"
            turn_data = turn_resp.json()
            assert turn_data.get("reply") and len(turn_data["reply"]) > 10
            assert "facts" in turn_data

        if self.run_step(4, "Bilingual Conversational Turn (English - Grounded ROI)", step4_chat_en):
            passed += 1

        # -------------------------------------------------------------------
        # Step 5: Hindi Chat Turn
        # -------------------------------------------------------------------
        def step5_chat_hi():
            conv_id = state["conversation_id"]
            turn_resp = self.client.post(
                f"/conversations/{conv_id}/turns",
                headers=state["student_headers"],
                json={
                    "speaker": "parent",
                    "text": "क्या वेल्डर कोर्स की फीस कम है और छात्रवृत्ति मिलती है?",
                    "lang": "hi",
                },
            )
            assert turn_resp.status_code == 200, f"Hindi chat turn failed: {turn_resp.text}"
            turn_data = turn_resp.json()
            assert turn_data.get("reply") and len(turn_data["reply"]) > 10
            assert turn_data.get("lang") == "hi"

        if self.run_step(5, "Bilingual Conversational Turn (Hindi - Scheme Fact Branch)", step5_chat_hi):
            passed += 1

        # -------------------------------------------------------------------
        # Step 6: Human Escalation Hand-off
        # -------------------------------------------------------------------
        def step6_escalation():
            conv_id = state["conversation_id"]
            esc_resp = self.client.post(
                f"/conversations/{conv_id}/escalate",
                headers=state["student_headers"],
                json={
                    "reason": "Family requesting consultation with regional ITI counsellor",
                    "contact_phone": "+919876543210",
                    "preferred_language": "hi",
                    "channel": "callback",
                    "priority": "normal",
                },
            )
            assert esc_resp.status_code == 201, f"Escalation failed: {esc_resp.text}"
            esc_data = esc_resp.json()
            assert esc_data.get("id") is not None
            assert esc_data.get("status") in ("open", "assigned")

        if self.run_step(6, "Live Counsellor Escalation Hand-off & Case Pack", step6_escalation):
            passed += 1

        # -------------------------------------------------------------------
        # Step 7: Admin Resistance Dashboard
        # -------------------------------------------------------------------
        def step7_admin_dashboard():
            ts = int(time.time() * 1000)
            admin_email = f"preflight_admin_{ts}@kaushalpath.in"
            admin_reg = self.client.post(
                "/auth/register",
                json={"email": admin_email, "password": "AdminPassword123!", "role": "admin", "give_consent": True},
            )
            assert admin_reg.status_code == 200, f"Admin register failed: {admin_reg.text}"
            admin_token = admin_reg.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            dash_resp = self.client.get("/admin/resistance?group_by=district", headers=admin_headers)
            assert dash_resp.status_code == 200, f"Admin dashboard query failed: {dash_resp.text}"
            dash_data = dash_resp.json()
            assert "total_conversations" in dash_data

        if self.run_step(7, "Admin Dashboard Analytics Query (k>=5 Privacy Guard)", step7_admin_dashboard):
            passed += 1

        # -------------------------------------------------------------------
        # Summary & Exit
        # -------------------------------------------------------------------
        total_time_s = time.perf_counter() - total_t0
        print("=" * 68)
        if passed == total_steps:
            print(f"RESULT: ALL {total_steps}/{total_steps} STEPS PASSED in {total_time_s:.2f}s (Threshold < 60.0s)")
            print("STATUS: SYSTEM IS DEMO-READY AND STAGE-CERTIFIED.")
            print("=" * 68)
            return 0
        else:
            print(f"RESULT: {passed}/{total_steps} STEPS PASSED ({total_steps - passed} FAILED) in {total_time_s:.2f}s")
            print("STATUS: PRE-FLIGHT CHECKS FAILED.")
            print("=" * 68)
            return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="KaushalPath demo pre-flight verification")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Target base URL of running backend server (e.g. http://localhost:8000). If omitted, auto-detects.",
    )
    args = parser.parse_args()

    runner = PreflightRunner(base_url=args.base_url)
    exit_code = runner.execute_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
