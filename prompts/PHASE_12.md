# PHASE 12 — Conversation engine (backend)

**Priority:** P0  
**Effort:** 3-4 days  
**PS rows fixed:** R1, R2, R6  

## Goal

Build the missing core: a conversational API where learner and parent talk in their own language and every factual claim is grounded in the outcome data.

## Prompt

PHASE 12 — CONVERSATION ENGINE (backend). Depends on Phase 11 outcome_svc.

Today the "conversation" is AskBox.tsx: 4 fixed tap-questions with 4 canned answers. Replace it with a real turn-based engine. Do not touch the frontend yet.

1. Alembic: conversations(id, room_id nullable, student_id, lang, status),
   turns(id, conversation_id, speaker, text, lang, intent, topic, sentiment,
   facts_json, created_at). Topics = income | security | social | safety | distance |
   cost | other (extend OBJECTION_TOPICS in models/human.py; migrate Objection too).
2. app/services/conversation/:
   - lang_detect.py: Devanagari -> hi; Latin text with Hindi tokens -> hinglish; else en.
   - intent.py: rule patterns + nearest-neighbour over exemplar utterances using the
     existing embedder (paraphrase-multilingual-MiniLM). Exemplars in
     intent_exemplars.json (>= 8 per topic, hi/en/hinglish). Returns (intent, topic, conf).
   - objection_kb.json: answer templates per topic in hi and en with placeholders such
     as {median_salary} {placement_rate} {provider} {n} {source}. No literal numbers.
   - grounder.py: given trade + family context (state, district, income_band) fetch
     facts via outcome_svc; each fact = {key,label,value,unit,source,source_year,is_demo}.
   - responder.py: build reply from template + facts. If settings.llm_provider != none,
     ask the LLM to rephrase using ONLY the provided facts JSON.
   - validator.py: extract every number from the reply; reject if any is not in facts
     (tolerate small integers in lists). On reject -> use template reply and set
     fallback_used=true.
3. Routes in app/api/routes/conversations.py (auth required; room members only when
   room_id is set). Turn response: {reply, lang, intent, topic, facts[],
   followups[], escalation_suggested, fallback_used}.
4. Settings: LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY (all optional).
5. Tests: unit (lang_detect, intent on 30 labelled lines, validator), integration
   (full turn hi + en), hallucination stub, offline.
6. New files eval/scripts/run_convo_eval.py + eval/gold/convo.jsonl. Gate: make check
   and the eval script prints intent_acc and numeric_faithfulness.

## Gate (acceptance)

- Hallucination test: a stub LLM that returns an invented salary is rejected and the template answer is used.
- `eval/gold/convo.jsonl` intent accuracy >= 0.85, numeric faithfulness = 1.0.
- No API key needed anywhere in tests.
