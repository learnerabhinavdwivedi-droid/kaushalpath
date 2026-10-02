# 05 — Open-source repos / datasets to integrate
Status: [V] = I opened/verified it this session. [K] = well-known project, confirm exact repo/licence before use.

## Closest reference implementations (study + borrow ideas, respect licence)
| Repo | What to take | Status |
|---|---|---|
| github.com/rahul370139/pathwise | Architecture of career matcher: RIASEC + embedding similarity over O*NET, roadmap/plan snapshot APIs, eval/ package layout | [V] |
| github.com/shriadke/Job-Classification | Sentence-transformers + sklearn over O*NET categories, ranking metrics (Top-k, MRR, NDCG) | [V] |
| github.com/joedcastro/Career-AI-Tech-Fair | Simple RIASEC + KNN on O*NET baseline | [V] |
| github.com/Krish15052/SIH26241 | Another team's prototype (Flask/MySQL). Study flow only; do NOT copy — originality is judged | [V] |

## Libraries (integrate directly)
| Need | Use | Status |
|---|---|---|
| Embeddings | sentence-transformers (multilingual MiniLM / multilingual-e5) | [K] |
| Vector search | FAISS-cpu (or Qdrant if you want a server) | [K] |
| Ranking | LightGBM (LambdaRank) | [K] |
| Explainability | SHAP or own reason-codes | [K] |
| Translation (vernacular) | AI4Bharat IndicTrans2 / Bhashini API | [K] |
| Voice | OpenAI Whisper (open weights) / faster-whisper | [K] |
| i18n | react-i18next | [K] |
| PWA | vite-plugin-pwa | [K] |
| PDF export | WeasyPrint or reportlab (backend) | [K] |

## Data sources (check licence + latest download page yourself)
- O*NET database (occupations, RIASEC interest profiles, skills) [K]
- ESCO (EU skills/occupations taxonomy, multilingual) [K]
- India NCO-2015 occupation codes + NSQF qualification packs from NSDC / Sector Skill Councils [K]
- PLFS (MoSPI) for wage/employment statistics by state [K]
- Dataset links on the official PS page (use these FIRST; judges expect them)

## Integration plan
Phase 1 loads O*NET+ESCO -> maps to NCO/NSQF via a mapping CSV you maintain (docs/data_mapping.md). Phase 3 borrows PathWise-style matcher design (reimplemented, not copied). Phase 4 uses Job-Classification-style metrics.
