# KaushalPath — 4-Minute Judge Demo Script (rev. Phase 29)

A timed, judge-facing walkthrough structured strictly around the core problem statement
(SIH PSID 26241: AI career counselling + family decision support for vocational education).

> **Scope Discipline Rule (Phase 29):**
> Do **not** navigate to `/home` (SparkLab marketing shell) or `/styleguide` during the demo.
> The judging panel evaluates the **family unit collaboration**, **vernacular grounding**,
> **counsellor escalation**, and **administrative resistance intelligence**.
> Keep the live screen focused entirely on the 8 beats below.

---

## 1. Pre-Demo Setup (< 60s)

```bash
# Terminal 1 — Start Backend
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Start Frontend
cd frontend && npm run dev    # http://localhost:5173

# Terminal 3 (Optional) — Verify Pre-flight (<15s)
python scripts/demo_preflight.py
```

- **Browser Window 1 (Learner Profile):** Open [http://localhost:5173](http://localhost:5173).
- **Browser Window 2 (Incognito / Guest — Parent Profile):** Ready at [http://localhost:5173/room/join](http://localhost:5173/room/join).
- **Fallback Verification:** Keep a secondary tab open with `http://127.0.0.1:8000/health/ready` (`{"status":"ready","db":"up"}`).

---

## 2. Timed Beat Sheet (Total Budget: 240 Seconds / 4 Minutes)

```
0:00        0:35        1:05        1:35        2:05        2:30        2:55        3:25        3:55  4:00
|-- Beat 1 --|-- Beat 2 --|-- Beat 3 --|-- Beat 4 --|-- Beat 5 --|-- Beat 6 --|-- Beat 7 --|-- Beat 8 --| End |
  Assessment   Room Join   Hindi Obj.   FactCard     Rs Shift    Escalation   Counsellor   Admin Heat   Audit
    (35s)        (30s)       (30s)       (30s)        (25s)        (25s)        (30s)        (30s)     (5s)
```

---

### Beat 1 (0:00–0:35, 35s): Adaptive Assessment & Recommendations
*PS Rows: R7, R11, R12, R13*

1. **Intake & Consent:**
   - On Window 1 (`/register`), register as a student. Point to the **bilingual consent screen** (plain English + Hindi, explicit DPDP compliance, zero-dependency account erasure).
   - Set Profile: District (e.g., Kanpur Nagar), Prior Education (10th Pass), and **Household Income Band** (e.g., `low` / ₹10,000–25,000/mo).
2. **Adaptive Engine:**
   - Open `/assessment`. Show adaptive question selection stopping in **$\le 24$ items**.
   - Tap the **Read-Aloud (🔊)** icon: *"Low-literacy learners can listen to every item in clear vernacular Hindi/English."*
3. **Transparent Results:**
   - View top-3 recommended trades (e.g., Electrician, Solar Technician, CNC Operator).
   - Point out the **reason codes** (skills match, local wage viability, budget fit) and the yellow **`DEMO` provenance badge** on all outcome figures (*"Every number is honest about its origin"*).

---

### Beat 2 (0:35–1:05, 30s): Family Room Creation & Parent Join
*PS Rows: R1, R2, R18*

1. **Create Room:**
   - On Window 1, click **"Create Family Room"** (`/room/new`). The screen generates a clean 6-character room code (e.g., `KP8821`).
2. **Parent Joins as Guest:**
   - Switch to Window 2 (Incognito/Guest profile) at `/room/join`.
   - Enter the room code and select **हिन्दी** as language.
   - **Say to Judge:** *"Notice the parent requires NO account creation, app installation, or complex password. Zero friction for rural and hesitant parents."*

---

### Beat 3 (1:05–1:35, 30s): Hindi-Language Parental Objection
*PS Rows: R2, R18, R19*

1. **Open Conversation:**
   - Both learner and parent enter the collaborative talk space (`/talk`).
2. **Submit Realistic Vernacular Objection:**
   - On Window 2 (Parent), type or paste a genuine parent objection:
     > **"पहले महीने में कितनी कमाई होगी? क्या नौकरी पक्की मिलेगी या पैसा डूब जाएगा?"**
   - Point out that this is **free-form natural text**, not a scripted dropdown or rigid multi-choice chip.

---

### Beat 4 (1:35–2:05, 30s): Grounded FactCard Reply with Provenance
*PS Rows: R3, R13, R18*

1. **Grounded Retrieval:**
   - The conversation engine classifies the intent (`income_query` + `job_security`).
   - Generates an immediate vernacular Hindi response accompanied by a verified **FactCard**.
2. **Inspect the FactCard:**
   - Highlights: **Median Earnings (₹18,500/mo)**, **p25–p75 Range (₹15,000–₹22,000)**, **Placement Rate (78%)**, and **Course Fee (₹0 / PMKVY 100% Subsidy)**.
   - Point to the card footer: **Source: `demo_synth_2026`**, **Reporting Year: `2026`**, and the yellow **`DEMO`** badge.
   - **Say to Judge:** *"Our numeric-faithfulness validator is 1.0. The system strictly refuses to hallucinate earnings; it only speaks numbers verified from our schema."*

---

### Beat 5 (2:05–2:30, 25s): Visible Resistance Score (Rs) Shift
*PS Rows: R9, R19*

1. **Second Parental Probe:**
   - Parent enters a follow-up query: *"अगर कानपुर के बाहर जाना पड़ा तो रहने का खर्चा कौन देगा?"*
2. **Observe Rs Meter:**
   - Point to the live **Resistance Meter (Rs)** on the screen.
   - As the engine surfaces hostel accommodation subsidies and nearby training centres in Kanpur Nagar, the parent's concern is directly addressed.
   - Show the dynamic **Rs score shift** (sentiment transitions from *Hesitant/Hardened* to *Informed/Softened*).

---

### Beat 6 (2:30–2:55, 25s): Escalation Hand-off & Case Pack Assembly
*PS Rows: R8, R20*

1. **Trigger Escalation:**
   - Click the 1-tap **"बात करें काउंसलर से" (Talk to a Human Counsellor)** button.
2. **Inspect Structured Case Pack:**
   - The system instantly bundles the conversation into an immutable, structured **Case Pack**:
     - Complete conversation transcript (learner + parent turns).
     - Extracted objection topics (`financial_risk`, `relocation`).
     - Real-time Resistance score snapshot ($R_s = 0.42$).
     - Student profile, verified income band (`low`), and shortlisted NSQF trades.
   - **Say to Judge:** *"When AI reaches its boundary, it never traps the family in an automated loop. It hands off to a human with complete clinical context."*

---

### Beat 7 (2:55–3:25, 30s): Counsellor Claims from Pool & Resolves
*PS Rows: R8, R20*

1. **Counsellor Queue:**
   - Switch to Counsellor portal (`/counsellor`).
   - The newly escalated case appears in the cohort queue (auto-routed by lowest active load).
2. **Claim & Lifecycle Progression:**
   - Click **Claim Case** (atomic claim prevents double-booking across counsellors).
   - Walk through the progression: **Open $\to$ Assigned $\to$ Contacted $\to$ Resolved**.
   - Counsellor types a note: *"Explained District Skill Committee hostel stipend to father; scheduled phone call for Tuesday."*
   - Note syncs back into the family thread.

---

### Beat 8 (3:25–3:55, 30s): Admin Live Resistance Heat Matrix
*PS Rows: R9, R10, R16*

1. **Open Scheme Admin Dashboard:**
   - Navigate to `/admin/resistance`.
2. **Live Intelligence Highlights:**
   - **District Bubble Map:** Geographic concentration of vocational resistance across UP districts.
   - **District / Concern $\times$ Trade Heat Matrix:** Shows real-time intensity (e.g., Electrician $\times$ Placement Fear in Kanpur Nagar) updating live from the session.
   - **Resistance Shift Trend:** Visualizes cohort shifts (families softened vs hardened over the last 30 days).
   - **Privacy Suppression:** Point to the privacy note: *"Any cell with $<5$ students is automatically masked to prevent deanonymization (k-anonymity guarantee)."*

---

### Wrap-Up (3:55–4:00, 5s): PS Traceability & Audit Gate
*PS Rows: All (100% PS Coverage)*

1. **Closing Punchline:**
   - *"KaushalPath is completely offline-reliable (`llm_provider=none`), 100% compliant with PSID 26241 across all 57 criteria, and ingests live MSDE datasets with zero code changes."*
   - Terminal verification: `python scripts/ps_audit.py` shows **57.0 / 57.0 (100.0%)**.

---

## 3. Emergency Fallback Commands

If browser state hangs or network port conflicts occur during evaluation:

```bash
# 1. Instant End-to-End API Preflight (<15s)
python scripts/demo_preflight.py

# 2. Live PS Traceability Audit (100% check)
python scripts/ps_audit.py

# 3. Data Provenance & Ingestion Integrity Verification
python scripts/data_provenance_audit.py

# 4. Service Liveness & Readiness Probe
curl -s http://127.0.0.1:8000/health/ready
```
