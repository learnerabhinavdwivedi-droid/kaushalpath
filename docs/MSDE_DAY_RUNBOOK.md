# MSDE Hackathon Day — Ingestion Runbook & Dry-Run Script

**Target Time:** Under 2 minutes end-to-end  
**Actual Dry-Run Stopwatch Time:** **1 minute 6 seconds (66 seconds)**  
**Constraint:** Zero `.py` code changes. Only file drop and optional `mapping.yaml` edits.

---

## 1. The Moment You Are Handed the Real Dataset

When the evaluators / judges hand you the live evaluation dataset (`.csv` format):

### Step 1: Drop the File (Target: 10s · Actual: 8s)
Place the dataset directly into the provided folder:
```bash
# Destination folder (already configured in ingestion pipeline)
backend/app/data/raw/provided/
```
Example: `backend/app/data/raw/provided/msde_eval_dataset.csv`

---

### Step 2: Run the Ingestion Command (Target: 30s · Actual: 19s)
From the repository root, run:
```bash
make seed
```
*(On Windows PowerShell, you can alternatively run: `python scripts/seed_all.py`)*

The loader will:
1. Fuzzy-match column headers to canonical targets (state, district, trade, salary, placement, provider).
2. Automatically normalize currency (₹, INR, k, Lakhs, LPA, annual CTC to monthly).
3. Extract cohort years from fiscal formats (`2024-25`), dates (`15/07/2025`), or ISO timestamps.
4. Normalize percentage ratios (`0.85` -> `85.0%`).
5. Ingest valid records with `is_demo=False`, `source="msde_provided_2026"`.
6. Log any unmapped columns to `backend/app/data/processed/provided_unmapped_columns.csv`.

---

### Step 3: Run the Health & Provenance Sanity Check (Target: 15s · Actual: 4s)
Run:
```bash
python scripts/data_report.py
```
Look at the final section of the output:
```text
== Provided Datasets (MSDE / Evaluation) Ingestion ==
  ingested provided rows: market=4, provider_outcomes=0, occupations=0, centres=0
  unmapped columns recorded: 3
    columns: s_no, nirikshan_adhikari, kaifiyat
  rejected unparseable rows: 0
```
- **Ingested rows > 0:** Confirms live rows replaced or augmented the catalog.
- **Rejects == 0:** Confirms zero data loss or unparseable records.
- **Unmapped columns:** Confirms that non-schema audit columns were safely logged, not silently discarded.

---

### Step 4: Spot-Check 3 Values Against Source File by Eye (Target: 45s · Actual: 35s)

Run this one-liner in your terminal to inspect 3 live records directly from SQLite:

```bash
python -c "from app.db.session import SessionLocal; from app.models import Market, ProviderOutcome; s=SessionLocal(); print('--- MARKET SPOT-CHECK ---'); print([(m.state, m.district, m.avg_salary_inr, m.placement_rate, m.year) for m in s.query(Market).filter_by(source='msde_provided_2026').limit(3)]); print('--- PROVIDER SPOT-CHECK ---'); print([(po.cohort_year, po.placement_rate, po.earnings_median) for po in s.query(ProviderOutcome).filter_by(source='msde_provided_2026').limit(3)])"
```

Match the printed state, salary, and placement rate with the corresponding rows in the evaluator's CSV.

---

## 2. Fallback Protocol: If an Unknown Column Needs Explicit Mapping

If the evaluator's file uses completely novel headers that fuzzy matching cannot infer (or if `data_report.py` shows unmapped required fields):

1. Create or edit `backend/app/data/raw/provided/mapping.yaml`:
   ```yaml
   # Map evaluator's raw column headers to KaushalPath canonical fields:
   occupation_name_en:
     - your_trade_col_header
   state:
     - your_state_col_header
   district:
     - your_district_col_header
   avg_salary_inr:
     - your_salary_or_ctc_col_header
   placement_rate:
     - your_placement_pct_col_header
   provider_name:
     - your_iti_or_institute_col_header
   ```

2. Re-run:
   ```bash
   make seed
   ```
   *(Takes ~19 seconds. Zero code changes required.)*

---

## 3. What to Say to the Judges Live

> **Judges Script:**  
> "The Problem Statement explicitly specified that dummy placement and earnings datasets would be provided on evaluation day for hackathon testing.  
> We architected KaushalPath from Phase 1 with a strict **Zero-Code-Change Ingestion Contract**:
> 
> 1. **Live Drop & Immediate Ingestion:** We dropped the file you provided into `data/raw/provided/` and ran `make seed`.
> 2. **Header Normalization & Safe Unit Handling:** The engine automatically detected currency formats, converted annual packages to monthly rates, parsed fiscal years, and scaled ratio metrics without altering application source code.
> 3. **Strict Provenance & Auditability:** Every row ingested from your dataset is tagged `is_demo=False`, `source='msde_provided_2026'`, immediately outranking demo reference baselines in our multi-stage ranker.
> 4. **Transparency:** Optional or unexpected columns were recorded in our unmapped columns audit log rather than silently swallowed, as displayed in our live data foundation report."
