# PHASE 3 — Recommendation engine (filter -> retrieve -> rank -> explain)

GOAL: Given a student profile, return top-k (default 3, max 10) occupations/courses with scores, reasons and sources.

PIPELINE (each stage in its own module):
1. ml/ranking/filters.py — HARD constraints: min education vs course.min_edu, age limits, NSQF level reachable, budget band vs fee, district/state reachability (distance via centres or relocate_ok), max duration. Return the eligible set + a `rejected` list with reason (for transparency).
2. ml/retrieval — embedder.py (multilingual sentence-transformers, model name from config), index_builder.py (FAISS index over occupation text: name+description+skills; versioned file in data/processed), searcher.py (query text built from RIASEC top-3 descriptors + stated interests + aptitude).
3. ml/ranking/features.py — features per (student, occupation): riasec_cosine, top3_code_overlap, aptitude_fit per dimension, nsqf_gap, fee_ratio, duration_fit, local_demand_index, distance_km, retrieval_score, salary_percentile (if market not demo). No protected attributes.
4. ml/ranking/ranker.py — LightGBM LambdaRank loaded from file; if missing/untrained, fall back to a transparent weighted scorer (weights in config). train.py trains on eval/gold train split ONLY and writes model + metadata (version, train date, metrics).
5. ml/explain — reason_codes.py produce >=2 codes per recommendation (e.g. INTEREST_MATCH(R,I), APTITUDE_STRONG(spatial), WITHIN_BUDGET, NEARBY_CENTRE(12km), HIGH_LOCAL_DEMAND) with numeric evidence and source badges; templates_hi_en.json for text; optional LLM paraphrase behind a flag with template fallback and a check that the paraphrase contains no new facts.
6. services/recommend_svc.py orchestrates and stores to recommendations table; POST /recommend.

TESTS: filter tests (every constraint), property test "no recommendation violates hard constraints" on 1000 random profiles, ranker fallback test, reason-code coverage test, latency test.
ACCEPTANCE: `pytest -k recommend` passes; POST /recommend returns top-3 with reasons for a sample profile; violation test = 0 failures.
DO NOT: let the LLM choose or reorder careers. Do not hide rejected-because info.
