# PHASE 7 — Family Decision Room UI (the differentiator)

GOAL: Parent + student + counsellor decide together with clear, explainable, vernacular UI.

TASKS:
1. Pages (one file each): RoomCreate, RoomJoin (code entry/QR), RoomHome, CompareView, WeightsPanel, VoteView, ConsensusView, RoadmapView.
2. WeightsPanel: sliders with icons for cost, duration, salary, local jobs, distance; each member's weights shown side by side; plain-language helper text in Hindi/English.
3. CompareView: up to 3 careers side by side; table + Recharts radar chart; "why this ranks higher" in one sentence from reason codes; DEMO/real data badges on every number; tooltips with sources.
4. Disagreement highlights: show where student and parent differ most and propose a talking point.
5. VoteView + ConsensusView: 1-5 votes, agreement meter, final suggested choice, "what would change this ranking" what-if (user changes one weight; ranking updates live via /compare).
6. RoadmapView: timeline UI (eligibility -> course -> centre map link -> certification -> job), fees and duration, nearest centres list.
7. Share/export: generate printable PDF (backend WeasyPrint/reportlab or print CSS) in the chosen language, plus a WhatsApp share link with a short text summary.
8. Counsellor mode in the same room: read-only notes + override suggestion.
9. Real-time-ish updates via polling every few seconds (WebSocket optional later).
10. Tests: component tests for compare/weights, e2e for full demo path: student result -> create room -> parent joins -> adjust weights -> vote -> consensus -> PDF.

ACCEPTANCE: e2e demo path green; screen-recordable in <4 minutes; PDF opens correctly in Hindi.
DO NOT: hide data provenance; change backend contracts without updating docs/02_ARCHITECTURE.md and tests.
