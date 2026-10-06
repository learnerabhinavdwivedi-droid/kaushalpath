# PS_SPEC — Official SIH 2026 Problem Statement 26241

Scraped from the live portal https://www.sih.gov.in/sih2026PS on **2026-10-02**.
This is the authoritative wording; it overrides `docs/01_PS_ANALYSIS.md` and any
inferred rows in `docs/PS_TRACEABILITY.md` where they conflict.

> **Verification note (Phase 10):** Cross-checked on title, ministry, category
> and theme against four public SIH26241 repositories. The portal blocks automated
> requests so full word-for-word confirmation is pending. Deadline stated as
> 5 Oct 2026 — re-confirm; other sources list different dates. If the idea
> submission is already in, this plan is for the prototype shown at evaluation.

| Field | Value |
|---|---|
| Problem Statement ID | **26241** (SIH26241) |
| Title | AI-Enabled Career Counselling and Family Decision-Support Platform for Vocational Education |
| Organization | Ministry of Skill Development and Entrepreneurship (MSDE) |
| Department | Ministry of Skill Development and Entrepreneurship (MSDE) |
| Category | Software |
| Theme | Smart Education |
| Competition (ideas) | **8/500** (low — 8 teams as of scrape date) |
| Deadline | 5 October 2026 |
| YouTube link | (none) |
| **Dataset link** | **NA — dummy placement/earnings datasets to be provided for hackathon evaluation** |

## Background of the Problem Statement
Enrolment and retention in vocational training in India is shaped as much by
family perception as by the learner's own interest. Vocational pathways are
frequently seen by parents as a lower-status alternative to academic/degree
routes, and this perception — more than access or affordability alone —
contributes to low enrolment, mid-course dropout, and reluctance to pursue
NSQF-aligned progression. Existing career-guidance tools in the skilling
ecosystem are almost entirely learner-facing; they help a student choose a
course but do little to inform or reassure the parents who often make or veto
that decision, particularly in rural and semi-urban households. There is a need
for a counselling tool that engages both the learner and the family unit
together, addressing parental concerns about earning potential, safety, and
social standing of a trade with credible, localised, data-backed information,
rather than treating career guidance as a purely individual, learner-only
exercise.

## Description of the Problem Statement
The challenge is to build an AI-enabled counselling platform that can:
1. **Engage learners and parents jointly** through a conversational interface in
   regional languages, addressing common parental objections (income potential,
   job security, social perception) with credible local data.
2. **Present verified outcome data** for specific trades and training providers —
   average post-training earnings, placement rates, and progression pathways
   (NSQF level-ups, further education routes).
3. **Offer a structured, low-jargon explainer** of how vocational qualifications
   map to job roles and career growth, tailored to the family's own context
   (location, household income bracket, learner's academic background).
4. **Provide human-escalation options** (connecting to a live counsellor) for
   cases the AI cannot adequately resolve.
5. **Track engagement and sentiment shifts** to help scheme administrators
   identify where parental resistance is concentrated.

## Expected Solutions / Outcomes
1. A working **conversational counselling tool** usable by both learners and
   parents, in **at least one regional language plus English**.
2. A **verified outcome-data backend** (placement rates, earnings ranges) that
   the tool draws on rather than generic content.
3. A **dashboard for scheme administrators** showing where and why family
   resistance is concentrated.
4. Evidence of **design for low-literacy and low-digital-familiarity users**.
5. A **clear escalation path to human counsellors** for unresolved concerns.

## Dataset situation & plan (resolves ASSUMPTIONS A1)
- The PS ships **no downloadable dataset** ("NA"). MSDE will hand out **dummy
  placement/earnings datasets** only at hackathon evaluation.
- Therefore the system must be built to (a) run on clearly-marked demo data now
  (`is_demo=true`, `source=demo_synth_2026`) and (b) **ingest the MSDE dummy file
  with zero code change** when it is provided (drop it in
  `backend/app/data/raw/provided/` → `make seed`).
- Credible public sources to enrich "verified outcome data" (licence-checked,
  bulk download, no scraping of sites that forbid it — see `data/raw/README.md`):
  - **O*NET** Interest + Occupation Data → RIASEC + skill anchors.
  - **ESCO** → multilingual occupation labels (Hindi + regional).
  - **NSQF / NCVET qualification packs + NCO-2015** → level & occupation mapping.
  - **Skill India Digital / PMKVY & Sector Skill Council** placement & earnings
    reports → the closest thing to the "verified outcome data" the PS names.
  - **PLFS (MoSPI)** wage/employment by state → localised earnings ranges.

> Competition is very low (8/500) and the theme fit is strong; the differentiator
> the PS explicitly demands is the **family/parent unit + vernacular conversational
> UI + admin resistance dashboard**, not just a learner recommender.
