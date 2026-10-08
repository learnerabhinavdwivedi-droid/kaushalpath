# PHASE 15 — Conversational UI for learner and parent (frontend)

**Priority:** P0  
**Effort:** 3-4 days  
**PS rows fixed:** R1, R12  

## Goal

Give families the interface the PS describes: one shared chat, a big Learner / Parent switch, voice in and out, fact cards with source badges, and an always-visible "talk to a human" button.

## Prompt

PHASE 15 — CONVERSATIONAL UI. Depends on Phases 12 and 14 APIs.

Current state: RoomHomePage renders AskBox (4 fixed chips -> 4 canned answers). Parents must register with email + password. Voice is output-only (speechSynthesis).

Build:
1. `src/api/client.ts`: createConversation, sendTurn, getConversation, escalateConversation.
2. `src/components/chat/`: ChatPanel, MessageBubble, SpeakerToggle (two 56px icon buttons, labelled in en/hi), FactCard (value + SourceBadge + is_demo badge), QuickReplies (income, job security, social status, daughter safety, distance, fees), MicButton (SpeechRecognition lang from i18n; hide + show typing hint if unsupported), ReadAloudToggle, EscalateSheet (phone, best time, language).
3. Pages: `/talk` (single-family chat) and embed ChatPanel inside RoomHomePage; keep AskBox chips as QuickReplies. Poll conversation every 5s for counsellor replies and escalation status; queue unsent turns and retry when offline.
4. Guest parent join: backend POST /auth/guest {room_code, name, phone?} returns a scoped parent token (role=parent, room-bound, 24h). RoomJoinPage uses it; no email.
5. Remove `/home` marketing link from Navbar and Footer (keep route); landing CTA goes to assessment or `/talk`.
6. i18n: add keys to en.json + hi.json; `npm run check-i18n` must pass.
7. Tests: vitest for ChatPanel states (loading, error, unsupported mic), axe on ChatPanel, Playwright e2e/talk-hi.spec.ts (Hindi, mocked recognition).

## Gate (acceptance)

- `npm --prefix frontend test`, `npm run build`, `make check` all pass.
- Playwright flow in Hindi: parent joins by code, speaks (mocked) an income objection, sees grounded fact card, taps Talk to a human, status shows Open.
