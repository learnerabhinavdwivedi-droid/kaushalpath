# ASSUMPTIONS

Record every place where the requirement was ambiguous or data was missing. Do not silently guess.

## A1 — Official PS text not yet available (BLOCKING for a real Phase 0 gate)
`docs/PS_SPEC.md` still contains only the **unverified working title**:
"AI-enabled career counselling and family decision-support platform for vocational education" (PSID 26241).
The official sih.gov.in brief was not retrievable from public mirrors during prep.
=> The requirement list in `docs/PS_TRACEABILITY.md` is currently derived from `docs/01_PS_ANALYSIS.md`
   (inferred scope), NOT from quoted PS wording. **Before locking Phase 0, paste the official PS text
   into docs/PS_SPEC.md and re-run Phase 0 task 1** to replace inferred rows with quoted requirements
   and confirm weights (3 explicit / 2 implied / 1 optional).

## A2 — Stack kept fixed
No change proposed to `docs/02_ARCHITECTURE.md`. Phase 0 only scaffolds; nothing in the (inferred) PS
demands a stack change that is not already covered by the FastAPI + sentence-transformers/FAISS/LightGBM
+ React + Docker plan.

## A3 — Phase 0 has no business logic
Per PHASE_0.md "DO NOT", this phase adds no data models, ML, or UI beyond a placeholder home page.
