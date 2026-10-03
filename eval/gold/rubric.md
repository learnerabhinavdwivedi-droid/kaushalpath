# Relevance Rubric (KaushalPath)

This rubric defines the "gold" standard for grading a recommended course/occupation for a specific student persona. 
The final score is a weighted combination resulting in a **graded relevance** from 0 to 3.

## Weightings
1. **Interest & Aptitude Fit (40%)**: How well the occupation matches the student's top RIASEC profile and aptitudes.
2. **Eligibility Hard Gate (30%)**: **MUST BE MET**. Min education, max duration, budget constraints. If this fails, the overall score is 0.
3. **Market Fit (20%)**: Local demand and placement rate in the student's area (or nearby if `relocate_ok`).
4. **Cost Fit (10%)**: Even if within budget, cheaper or subsidized options score higher here.

## 0-3 Grading Scale
- **3 (Perfect/Strong Match)**: Fits top-1 or top-2 RIASEC interests perfectly. High aptitude match. Passes all eligibility gates. Course fee is well within budget. High local demand.
- **2 (Good/Acceptable Match)**: Fits top-3 interests or adjacent interests. Passes all eligibility gates. Fee is at the edge of the budget. Average local demand.
- **1 (Weak/Poor Match)**: Low interest match but passes eligibility. Lower demand or lower aptitude fit.
- **0 (Irrelevant/Violation)**: Violates ANY hard constraint (e.g. requires 12th pass but student is 8th pass, or fee exceeds budget limit), OR completely misaligned with interests.
