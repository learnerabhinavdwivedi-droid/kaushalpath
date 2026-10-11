# Recommender Version Comparison Report: v0.1 vs v0.2

- **Sample**: 103 gold personas evaluated
- **Mean Kendall Tau (Top-10)**: `0.6622`
- **Top-3 Slot Changes**: 115 / 271 (42.44%)

## Dominant Drivers Behind Top-3 Rank Shifts

| Dominant Feature | Count of Slot Changes | Share (%) |
| --- | ---: | ---: |
| aptitude_fit_occ (trade ability alignment) | 115 | 100.0% |

## Key Architectural Differences
1. **Missing Data Neutrality**: v0.1 filled missing features with arbitrary 0.5 constants; v0.2 dynamically renormalises weights over available features.
2. **Real Empirical Evidence**: Replaced bogus 'top 100%' salary percentile with empirical Bayes shrunk placement rates and trade-level earnings percentiles from DGT tracer studies and PLFS microdata.
3. **Trade-Grounded Aptitude Fit**: Replaced constant aptitude fit with Phase 21 IRT shortfall-only matching against O*NET 31.0 ability requirements.
4. **Net Cost with Schemes**: Budget adherence now factors in household income band subsidies and uncapped ratio for transparent explanations.
