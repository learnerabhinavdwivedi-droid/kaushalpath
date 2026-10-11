# Evaluation Report (val)

Personas scored: 98; with a viable strong match: 69 (coverage 70.4%)

| Gate | Value | Target | Status |
|---|---|---|---|
| G1_violations_pct | 0.0 | 0.0 | PASS |
| G2_top3_hit_rate | 0.9565 | 0.95 | PASS |
| G3_ndcg_5 | 0.8326 | 0.9 | FAIL |
| G5_explanation_coverage | 1.0 | 1.0 | PASS |
| G6_slice_gap | 0.0508 | 0.03 | FAIL |
| G7_latency_p95_ms | 2.27 | 800.0 | PASS |

## Slice top-3 hit rates (G2 by slice)

- urban: 0.949
- rural: 1.0

## Adaptive Assessment Engine (G4 - Simulated)

- G4 top-3 letter set agreement: 96.5% (simulated - pilot pending) (target >= 95%)
- Exact-order agreement: 89.5% (simulated - pilot pending) (baseline >= 74%)
- Avg interest items: 22.9 (target <= 24, hard cap 30)
- Note: Evaluated on synthetic respondents replayed through calibrated 2PL IRT bank with forced-choice tie-breaks; labelled simulated until field pilot data exists.

## Worst failures (error analysis)

- Persona 180 (Pune, diploma): got [35, 37, 31], gold [6, 20, 1]
- Persona 221 (Nagpur, diploma): got [47, 49, 45], gold [6, 1, 5]
- Persona 263 (Pune, 12th): got [43, 42, 48], gold [1, 5, 6]

## Limitations
- Personas are synthetic (seeded rule generation); market data is demo.
- G1 is 0 by construction (the ranker only sees the hard-filtered set).
- Labels are rubric-derived, not model-derived.
- G2/G6 are measured over personas that have >=1 eligible grade>=2 course; personas with none (15% of val) are a catalogue-coverage gap, reported above, not a ranking failure the model can fix.
- G4 adaptive assessment agreement (96.5% set, 89.5% exact order) is evaluated on synthetic respondents; real pilot validation is pending.
