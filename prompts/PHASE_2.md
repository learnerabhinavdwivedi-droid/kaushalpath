# PHASE 2 — Assessment engine (adaptive interests + aptitude + constraints)

GOAL: Produce a reliable student profile vector from as few questions as possible, in Hindi and English.

SPEC:
- Interest model: Holland RIASEC. Item bank in backend/app/ml/assessment/riasec_items.json (>=60 items, each {id, text_en, text_hi, dimension, reverse:false, difficulty}). Use plain-language, vocational, activity-based items (e.g. "repair a bike chain"), no jargon.
- Adaptive logic (adaptive.py): start with 2 items per dimension; after each answer update dimension score and a confidence value (standard-error style); next item = from the dimension with lowest confidence / closest top-3 ties; stop when top-3 order confidence >= 0.95 or 24 items asked (hard cap 30).
- Aptitude mini-test (numerical, verbal, spatial, mechanical): 5 items each, language-light, image-friendly. Output 0-1 scores.
- Constraints form: edu level (8th/10th/12th/ITI/diploma), age, district, state, budget band, relocate_ok, preferred language, max training duration.
- scoring.py: returns {riasec: {R..C}, top3_code, aptitude, confidence, items_answered}.
- Reference full-test scorer for evaluation (scoring_full.py) using all items.

API: GET /assessment/next, POST /assessment/answer, GET /assessment/result (schemas in schemas/assessment.py). Session state stored in DB, resumable.
TESTS: unit tests for update rule, stop rule, resumability; property test that scores stay within [0,1]; simulation script eval/scripts/sim_assessment.py that replays a RIASEC dataset (document the dataset + licence) and reports G4 agreement (target >=95% top-3 letter agreement).

ACCEPTANCE: pytest for assessment passes; `python eval/scripts/sim_assessment.py` prints G4 number; avg items asked reported (<=24).
DO NOT: use gender/caste in scoring. Do not claim G4 if the simulation dataset is synthetic — label it.
