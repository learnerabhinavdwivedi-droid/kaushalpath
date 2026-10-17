# PHASE 27 — LLM-wiring decision + demo reliability hardening

**Priority:** P1
**Effort:** 0.5 day
**PS rows touched:** R1, R18 (conversational interface quality/reliability)

## Why this phase exists

`backend/app/core/config.py` currently defaults `llm_provider` to `"none"` — the whole
conversation runs on the deterministic template path with no external API call. That's a good
reliability default (zero hallucination risk, works with no internet on a judge's wifi), but
it's currently an unexamined default rather than a deliberate, documented, tested decision. Make
the choice explicit, prove the fallback is bulletproof, and give yourself a one-command
pre-flight check before you ever present live.

## Prompt

PHASE 27 — LLM DECISION + DEMO HARDENING.

1. Add an entry to `docs/ASSUMPTIONS.md`: "A-LLM — the demo runs with `llm_provider=none` by
   default: fully offline, deterministic, zero hallucination risk. An optional
   `llm_provider=openai_compat|gemini` path exists for more natural phrasing but is never
   required, and on any timeout or error in `responder.py:_call_llm_api` it falls back silently
   to the template path — the family-facing reply is never blocked by an external API."
2. Add `backend/tests/unit/test_phase27_llm_fallback.py` that mocks a failing/timing-out LLM
   call and asserts the conversation endpoint still returns a valid, grounded, correctly-numbered
   reply — never an empty or broken response.
3. Confirm (add a test if one doesn't already exist) that `validator.py`'s number-validation
   runs on LLM-paraphrased replies too, so a wired-in LLM provider cannot alter the grounded
   facts it's asked to verbalise — this is the hallucination-proofing the README already claims;
   prove it with a test that intentionally feeds the validator a paraphrase containing a wrong
   number and asserts it is rejected/corrected.
4. Add a one-line toggle note to `.env.example` and the README showing exactly how to flip
   `llm_provider` on for a "richer phrasing" demo mode, with the caveat from step 1 stated next
   to it.
5. Add `scripts/demo_preflight.py`: a single script that runs migrate + seed, hits `/health`,
   fires one assessment flow, one chat turn in English and one in Hindi, one escalation, and one
   admin-dashboard query end-to-end, printing a clear PASS/FAIL per step. This is meant to be run
   in under 60 seconds right before walking on stage.

## Gate (acceptance)

- `make demo && python scripts/demo_preflight.py` exits 0 with all steps PASS.
- `pytest backend/tests/unit/test_phase27_llm_fallback.py` passes.
- README contains the one-paragraph LLM decision note from step 1, and `.env.example` documents
  the toggle from step 4.
