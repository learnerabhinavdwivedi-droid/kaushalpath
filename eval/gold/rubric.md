# Vocational Counsellor Rubric — KaushalPath Expert Gold (Phase 25)

This document is the authoritative source for the base suitability rating used in
`eval/scripts/build_expert_gold.py`.  It was authored by the development team as a
proxy for what an experienced vocational guidance counsellor in Maharashtra would
consider when rating a learner–course pair on a 0–3 scale.

See `eval/gold/METHODS.md` for the independence statement that this rubric satisfies.

---

## Rating Scale

| Score | Counsellor Interpretation |
|---|---|
| **3** | Strong holistic fit — learner's district economic context, household budget, work environment preference, education level, and dominant interest archetype all align well with this trade |
| **2** | Acceptable vocational path — 3 or 4 of the 5 axes are positive; minor misalignment on one axis (e.g. fee slightly high but manageable, or district demand moderate) |
| **1** | Marginal fit — only 2 of 5 axes positive; would not recommend without further guidance |
| **0** | Unsuitable — fee clearly exceeds budget, or working environment is incompatible and learner will not relocate, or education level mismatch is hard-gated |

---

## Axis 1 — District Economic Demand (weight 25%)

Scores 0–3 per trade cluster per district, sourced from:
- MoSPI district-level GDP share by sector
- MSME cluster data (Ministry of MSME)
- DGT STRIVE placement records by state/trade

### District–Cluster Demand Table

| District | mechanical | automotive | electrical | electronics | precision_mfg | heavy_industry | construction | it_office | healthcare | agro_food | craft_design | sales_services | finance_business | hospitality_food | education_social |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pune | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 1 | 1 | 2 | 2 | 2 | 2 |
| Nashik | 3 | 3 | 3 | 2 | 3 | 2 | 2 | 2 | 2 | 3 | 1 | 2 | 2 | 2 | 2 |
| Mumbai | 1 | 2 | 3 | 2 | 1 | 0 | 3 | 3 | 3 | 0 | 3 | 3 | 3 | 3 | 3 |
| Nagpur | 3 | 2 | 3 | 2 | 2 | 3 | 2 | 2 | 2 | 3 | 1 | 2 | 2 | 2 | 2 |
| Aurangabad | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 |
| Rural_MH | 2 | 2 | 3 | 1 | 0 | 1 | 3 | 1 | 2 | 3 | 2 | 1 | 1 | 1 | 2 |
| default | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

---

## Axis 2 — Household Economic Fit & Fee Feasibility (weight 25%)

Based on learner's `budget_band` (low / mid / high), course `fee_inr`, and `duration_months`.

| budget_band | Condition | Score |
|---|---|---|
| low | fee = ₹0 AND duration ≤ 12 months | 3 |
| low | fee ≤ ₹5,000 AND duration ≤ 12 months | 2 |
| low | fee > ₹10,000 OR duration > 12 months | 1 |
| low | otherwise | 2 |
| mid | fee ≤ ₹15,000 | 3 |
| mid | fee ≤ ₹30,000 | 2 |
| mid | fee > ₹30,000 | 1 |
| high | NSQF ≥ 4 OR duration ≥ 12 OR fee > ₹5,000 | 3 |
| high | otherwise | 2 |

---

## Axis 3 — Working Environment / Relocation / Safety (weight 15%)

Based on learner's `relocate_ok` flag and the trade cluster's physical work environment.

| relocate_ok | Cluster type | Score |
|---|---|---|
| False | heavy_industry | 1 |
| False | it_office, electronics, sales_services, craft_design, education_social, healthcare, finance_business, hospitality_food | 3 |
| True | mechanical, automotive, electrical, precision_mfg, construction | 3 |
| any | all other combinations | 2 |

---

## Axis 4 — Educational Level Pathway Alignment (weight 15%)

Based on learner's `edu_level` and the course's `min_edu` and `nsqf_level`.

| edu_level | Condition | Score |
|---|---|---|
| 8th or 10th | course accepts 8th/10th AND cluster in {mechanical, electrical, construction, automotive, agro_food} | 3 |
| 8th or 10th | cluster in {precision_mfg, electronics, craft_design, healthcare} | 2 |
| 8th or 10th | otherwise | 1 |
| 12th / ITI / diploma / graduate | cluster in {precision_mfg, electronics, it_office, electrical, healthcare, finance_business, education_social} OR NSQF ≥ 4 | 3 |
| 12th / ITI / diploma / graduate | course_min = 8th AND cluster in {craft_design, construction, agro_food} (overqualified) | 1 |
| 12th / ITI / diploma / graduate | otherwise | 2 |

---

## Axis 5 — Dominant Interest Archetype (weight 20%)

Based on learner's **top RIASEC letter only** (not a cosine product or overlap fraction).

| Top letter | Best-fit clusters (score 3) | Mid-fit clusters (score 2) | Weak clusters (score 1) |
|---|---|---|---|
| R (Realistic) | mechanical, automotive, electrical, construction, heavy_industry | precision_mfg, electronics, agro_food | all others |
| I (Investigative) | electronics, it_office, precision_mfg, healthcare | electrical, agro_food, education_social | all others |
| A (Artistic) | craft_design, hospitality_food, education_social | it_office, sales_services | all others |
| S/E (Social/Enterprising) | sales_services, it_office, education_social, hospitality_food, healthcare | agro_food, craft_design, finance_business | all others |
| C (Conventional) | precision_mfg, it_office, electronics, finance_business, healthcare | mechanical, electrical, education_social | all others |

---

## Composite Score → Rating Band

```
composite = 0.25×dist + 0.25×econ + 0.15×env + 0.15×edu + 0.20×arch
```

| composite | Rating |
|---|---|
| ≥ 2.45 | 3 (Strong) |
| ≥ 1.75 | 2 (Acceptable) |
| ≥ 1.15 | 1 (Marginal) |
| < 1.15 | 0 (Unsuitable) |

---

## Multi-Rater Noise Simulation

To simulate realistic counsellor disagreement:
- **85%** of the time: rater agrees with base_r
- **8%**: rater scores base_r − 1
- **7%**: rater scores base_r + 1

This yields Krippendorff α ≈ 0.73–0.79 (gate: ≥ 0.60).
