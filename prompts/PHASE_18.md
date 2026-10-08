# PHASE 18 — Evaluation, honest audit and demo

**Priority:** P0  
**Effort:** 1-2 days  
**PS rows fixed:** All (evidence + audit)  

## Goal

Prove the new capabilities with numbers, re-score the PS alignment honestly, and rehearse a demo that follows the PS story.

## Prompt

PHASE 18 — EVALUATION + FINAL AUDIT.

1. Extend `eval/scripts/run_convo_eval.py` to >= 120 utterances (new file `eval/gold/convo.jsonl`; never edit existing gold). Report intent macro-F1 per language, numeric faithfulness (must be 1.0), refusal rate when outcome data is missing, escalation recall on high-resistance scripts. Write `eval/reports/convo_latest.md`.
2. Update `docs/EVAL_REPORT.md` with the conversation section and honest limitations (synthetic utterances, demo outcome data, lexicon sentiment).
3. Re-score `docs/PS_TRACEABILITY.md`. Every 1 must link to a test or demo step. Keep rows that are still partial at 0.5 and say why.
4. Delete-my-data must also delete conversations, turns, escalations (extend `DELETE /students/me` + audit entry + test). Update `docs/PRIVACY.md`.
5. Rewrite `docs/DEMO_SCRIPT.md` as the 4-minute story: Hindi parent objection -> grounded provider facts -> Rs rises -> escalation -> counsellor claims -> admin map.
6. Update `docs/QA_ANSWERS.md` for likely judge questions (data source, hallucination, privacy, scalability, what is demo vs real).
7. Fresh-clone rehearsal: follow README on a clean checkout and fix any broken step.

## Gate (acceptance)

- `make check && make eval-final && make ps-audit` all pass.
- Fresh-clone test: install and demo work cleanly.
