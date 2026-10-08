# PHASE 14 — Human escalation to a live counsellor

**Priority:** P1  
**Effort:** 2 days  
**PS rows fixed:** R8  

## Goal

Turn the escalation record into a real hand-off: contact details, case pack, routing, status lifecycle and a way for the counsellor to actually reach the family.

## Prompt

PHASE 14 — HUMAN ESCALATION. Depends on Phases 12-13.

Today POST /rooms/{code}/escalate stores a free-text reason; the counsellor queue
lists only escalations whose assigned_counsellor_id equals the caller, so cases with
no assignment are invisible to counsellors; there is no phone number, slot, status
beyond open|resolved, or case summary.

1. Alembic: escalations add contact_phone (validated, stored minimally), preferred_language,
   preferred_slot, channel (callback|chat|visit), priority (low|normal|high), case_pack_json,
   claimed_at, contacted_at, resolved_at, notes; status check = open|assigned|contacted|
   resolved|unreachable. Keep unique constraint semantics but allow a new case after resolve.
2. services/escalation_svc.py: build_case_pack(conversation_id) (last 10 turns, topics,
   rs, shortlisted trades with facts, family context, language), auto_route(escalation)
   (district + language match, least open load, else pool), should_escalate(conversation)
   (rs >= ESCALATION_RS, explicit request intent, 2 consecutive unresolved turns).
3. Routes: POST /conversations/{id}/escalate, GET /counsellor/escalations?status=&pool=true,
   POST /counsellor/escalations/{id}/claim (atomic UPDATE ... WHERE status='open'),
   /contact, /resolve, /notes. Keep the old /rooms/{code}/escalate as a thin wrapper.
4. Counsellor can post into the same conversation with speaker='counsellor' so the family
   sees the human reply in the chat thread.
5. notifier.py with ConsoleNotifier, SmsStubNotifier, WhatsAppLinkNotifier (selected by env).
6. Tests: pool visibility, atomic claim, auto-trigger rules, case pack contents,
   permission checks (family cannot read other families' cases).

## Gate (acceptance)

- `make check` is green.
- Sample `case_pack_json` printed.
- Atomic claim verified (no race conditions between counsellors).
