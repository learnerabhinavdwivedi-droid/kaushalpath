# PHASE 8 — Counsellor dashboard + feedback loop

GOAL: Show institution-level impact and let counsellors improve the system.

TASKS:
1. Counsellor pages: Cohort (filter by district/course interest/language), StudentDetail (profile, recommendations, reasons, room status), OverrideDialog (reason required), Analytics.
2. Analytics: distribution of RIASEC types, top recommended trades, drop-off in assessment, rooms created/consensus reached, average items asked, per-district demand vs recommendation mismatch. Use Recharts. Aggregate views must hide groups smaller than 5 students.
3. Feedback loop: students/parents mark "helpful / chosen"; store in feedback table; export script that merges feedback into a retraining dataset (eval/gold stays untouched); show a "model version" in footer and /meta/model-version.
4. Audit log for overrides and data deletions.
5. Role-based route guards in frontend; backend permission tests.
6. Tests for permissions, small-group suppression, feedback export.

ACCEPTANCE: role-based tests pass; dashboard renders with the demo seed; override and audit entries visible.
DO NOT: expose individual student data to non-assigned counsellors.
