# PHASE 13 — Sentiment, resistance score and admin analytics API

**Priority:** P1  
**Effort:** 2 days  
**PS rows fixed:** R9, R10  

## Goal

Replace manual topic taps with automatic per-turn sentiment, track how sentiment shifts during a session, and expose where and why resistance is concentrated.

## Prompt

PHASE 13 — SENTIMENT + RESISTANCE ANALYTICS. Depends on Phase 12.

Today feedback.sentiment and objection.sentiment are tapped by the user; nothing
tracks change over time and resistance is only a district x topic count scoped to a
counsellor's assigned students.

1. services/sentiment.py: lexicon-based hi/en/hinglish sentiment (negative / neutral /
   positive) + intensity markers (never, bilkul nahi, kabhi nahi, absolutely not).
   Call it inside the Phase 12 turn pipeline and store on turns.sentiment, turns.intensity.
2. services/resistance.py: rs = w1*topic_weight + w2*intensity - w3*consensus_delta,
   clipped to [0,1]. Weights + topic_weights in Settings (documented). consensus_delta
   uses positive-sentiment parent turns and room votes (existing consensus_svc logic).
   Persist rs_snapshots(conversation_id, turn_id, rs).
3. Shift label per conversation (first third vs last third mean sentiment).
4. Add role "scheme_admin" (migration on ck_user_role); update RequireRole + deps.
5. Routes under /admin: resistance?group_by=district|trade|topic&from&to,
   resistance/timeseries, resistance/map (district lat/lon from centres), resistance/export.csv.
   Reuse _suppress (k>=5). Return n, share_high_resistance, avg_rs, top_topics,
   shift_counts.
6. scripts/seed_demo_conversations.py: 300 synthetic is_demo conversations, 12 districts.
7. Tests: suppression, role scoping, Rs bounds, shift label, CSV export.

## Gate (acceptance)

- `make check` is green.
- One `/admin/resistance` JSON sample printed.
- Seeded conversations allow testing suppression (<5 suppressed) and scheme_admin broad visibility.
