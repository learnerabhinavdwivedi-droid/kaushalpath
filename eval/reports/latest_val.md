# Evaluation Report (val)

Personas scored: 98; with a viable strong match: 69 (coverage 70.4%)

| Gate | Value | Target | Status |
|---|---|---|---|
| G1_violations_pct | 0.0 | 0.0 | PASS |
| G2_top3_hit_rate | 0.971 | 0.95 | PASS |
| G3_ndcg_5 | 0.8656 | 0.9 | FAIL |
| G5_explanation_coverage | 1.0 | 1.0 | PASS |
| G6_slice_gap | 0.0831 | 0.03 | FAIL |
| G7_latency_p95_ms | 0.93 | 800.0 | PASS |

## Slice top-3 hit rates (G2 by slice)

- urban: 0.983
- rural: 0.9

## Worst failures (error analysis)

- Persona 154 (Rural_MH, 12th): got [1, 6, 20], gold [14]
- Persona 268 (Nagpur, graduate): got [13, 4, 21], gold [14, 37, 1]

## Limitations
- Personas are synthetic (seeded rule generation); market data is demo.
- G1 is 0 by construction (the ranker only sees the hard-filtered set).
- Labels are rubric-derived, not model-derived.
- G2/G6 are measured over personas that have >=1 eligible grade>=2 course; personas with none (15% of val) are a catalogue-coverage gap, reported above, not a ranking failure the model can fix.
