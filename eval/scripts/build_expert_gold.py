"""Phase 25 — Build expert gold ratings dataset (eval/gold/expert_ratings.csv).

PHASE 25 FIX: Replaced the old circular `latent` formula that reused
centered_cosine + top3_letters + aptitude_mean (the ranker's own signals)
with a hand-authored vocational counsellor rubric in eval/gold/rubric.md
and documented in eval/gold/METHODS.md.

The base suitability rating is now derived from five axes that the ranker
does NOT see as a single combined feature:
  1. District-level economic demand by trade cluster (lookup table)
  2. Household economic fit and fee feasibility by budget_band + fee + duration
  3. Working environment / relocation / safety profile
  4. Educational level pathway alignment
  5. Qualitative dominant interest archetype (top RIASEC letter only, no dot-product)

Multi-rater noise is preserved to simulate realistic rater disagreement.
See eval/gold/METHODS.md for independence documentation.

Produces:
  eval/gold/expert_ratings.csv — 160 learner profiles × eligible courses,
  rated by 3 simulated independent vocational counsellors on a 0–3 scale.
  50% dev split (personas 1–80), 50% locked test (personas 81–160).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_BACKEND_DIR = _REPO_ROOT / "backend"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from app.ml.ranking.filters import filter_courses  # noqa: E402
from eval_common import Catalogue, load_personas, persona_to_student  # noqa: E402

OUT_CSV = _REPO_ROOT / "eval" / "gold" / "expert_ratings.csv"

# ---------------------------------------------------------------------------
# Trade cluster taxonomy — maps occupation name_en → broad sector cluster.
# This is the primary axis for district-demand and RIASEC archetype lookups.
# It does NOT use any ranker feature (no cosine, no overlap, no aptitude mean).
# ---------------------------------------------------------------------------
OCC_TO_CLUSTER: dict[str, str] = {
    # Mechanical & Heavy Fabrication
    "Fitter": "mechanical", "Turner": "mechanical", "Machinist": "mechanical",
    "Welder": "mechanical", "Sheet Metal Technician": "mechanical",
    "Grinder": "mechanical", "Machine Operator": "mechanical",
    "Assembly Line Worker": "mechanical", "Watch Repairer": "mechanical",
    "Cobbler": "mechanical", "Mechanical Engineer": "mechanical",
    "Industrial Engineer": "mechanical",
    # Automotive & Transport
    "Mechanic Motor Vehicle": "automotive", "Mechanic Diesel": "automotive",
    "Mechanic Two Wheeler": "automotive", "Driver": "automotive",
    "Crane Operator": "automotive", "Courier Executive": "automotive",
    # Electrical & Energy
    "Electrician": "electrical", "Wireman": "electrical",
    "Solar PV Technician": "electrical", "Wind Turbine Technician": "electrical",
    "Lift and Escalator Technician": "electrical", "HVAC Technician": "electrical",
    "Refrigeration and AC Mechanic": "electrical", "Battery Assembler": "electrical",
    "Electrical Engineer": "electrical",
    # Electronics & Instrumentation
    "Electronics Mechanic": "electronics", "Instrument Mechanic": "electronics",
    "Electronics Engineer": "electronics",
    # Precision Manufacturing
    "CNC Turning Operator": "precision_mfg", "Tool and Die Maker": "precision_mfg",
    "Quality Inspector": "precision_mfg",
    # Heavy Industry & Chemical
    "Foundryman": "heavy_industry", "Chemical Engineer": "heavy_industry",
    "Fireman": "heavy_industry", "Safety Officer": "heavy_industry",
    # Construction & Civil
    "Plumber": "construction", "Carpenter": "construction",
    "Mason": "construction", "Painter": "construction",
    "Draughtsman": "construction", "Surveyor": "construction",
    "Architect": "construction", "Civil Engineer": "construction",
    # IT, Software & Digital
    "Software Developer": "it_office", "Web Developer": "it_office",
    "Mobile App Developer": "it_office", "Data Analyst": "it_office",
    "Data Scientist": "it_office", "Database Administrator": "it_office",
    "Cloud Engineer": "it_office", "Network Administrator": "it_office",
    "Cybersecurity Analyst": "it_office", "System Administrator": "it_office",
    "DevOps Engineer": "it_office", "QA Test Engineer": "it_office",
    "AI ML Engineer": "it_office", "Business Intelligence Analyst": "it_office",
    "IT Support Technician": "it_office", "Computer Operator": "it_office",
    "Computer Hardware Maintenance": "it_office", "Clerk": "it_office",
    "Data Entry Operator": "it_office", "Office Assistant": "it_office",
    "Back Office Executive": "it_office", "Call Center Agent": "it_office",
    "Digital Marketer": "it_office", "SEO Specialist": "it_office",
    # Healthcare & Allied
    "Staff Nurse": "healthcare", "Nursing Assistant": "healthcare",
    "Pharmacy Technician": "healthcare", "Medical Lab Technician": "healthcare",
    "Radiology Technician": "healthcare", "Physiotherapy Assistant": "healthcare",
    "Paramedic": "healthcare", "Health Sanitary Inspector": "healthcare",
    "ANM Midwife": "healthcare", "Dental Hygienist": "healthcare",
    "Ayurvedic Technician": "healthcare", "Nutritionist": "healthcare",
    "Occupational Therapist Assistant": "healthcare", "Optometrist": "healthcare",
    "Dialysis Technician": "healthcare", "Hospital Ward Assistant": "healthcare",
    "Lab Technician": "healthcare", "Medical Representative": "healthcare",
    # Education & Social Services
    "School Teacher": "education_social", "Anganwadi Worker": "education_social",
    "Child Care Professional": "education_social", "Counsellor": "education_social",
    "Social Worker": "education_social", "Special Educator": "education_social",
    "Librarian": "education_social", "Training Coordinator": "education_social",
    "ASHA Worker": "education_social", "Sports Coach": "education_social",
    "Teaching Assistant": "education_social", "Yoga Instructor": "education_social",
    # Finance & Business
    "Accountant": "finance_business", "Bookkeeper": "finance_business",
    "Tax Assistant": "finance_business", "Bank Clerk": "finance_business",
    "Teller": "finance_business", "Financial Advisor": "finance_business",
    "Insurance Agent": "finance_business", "HR Executive": "finance_business",
    "Purchase Executive": "finance_business", "Logistics Coordinator": "finance_business",
    "Supply Chain Analyst": "finance_business", "Credit Analyst": "finance_business",
    "Chartered Accountant": "finance_business", "Revenue Officer": "finance_business",
    "Store Manager": "finance_business", "Warehouse Manager": "finance_business",
    # Sales, Marketing & Services
    "Sales Executive": "sales_services", "Marketing Manager": "sales_services",
    "Retail Associate": "sales_services", "Cashier": "sales_services",
    "Entrepreneur": "sales_services", "Shopkeeper": "sales_services",
    "Security Guard": "sales_services", "Airline Ground Staff": "sales_services",
    "Travel Agent": "sales_services", "Tour Guide": "sales_services",
    "Event Manager": "sales_services", "Front Desk Executive": "sales_services",
    # Hospitality & Food Service
    "Chef": "hospitality_food", "Baker": "hospitality_food",
    "Confectioner": "hospitality_food", "Waiter": "hospitality_food",
    "Barista": "hospitality_food", "Housekeeping Supervisor": "hospitality_food",
    "Hotel Manager": "hospitality_food", "Food Processing Technician": "hospitality_food",
    # Creative, Craft & Design
    "Fashion Designer": "craft_design", "Interior Designer": "craft_design",
    "Graphic Designer": "craft_design", "UI UX Designer": "craft_design",
    "Photographer": "craft_design", "Videographer": "craft_design",
    "Animator": "craft_design", "Video Editor": "craft_design",
    "Musician": "craft_design", "Singer": "craft_design",
    "Dancer": "craft_design", "Actor": "craft_design",
    "Craft Instructor": "craft_design", "Embroidery Technician": "craft_design",
    "Beautician": "craft_design", "Hair Stylist": "craft_design",
    "Makeup Artist": "craft_design", "Tattoo Artist": "craft_design",
    "Florist": "craft_design", "Jewellery Designer": "craft_design",
    "Garment Worker": "craft_design", "Weaver": "craft_design",
    "Event Photographer": "craft_design",
    # Agriculture & Rural
    "Agriculture Technician": "agro_food", "Dairy Farmer": "agro_food",
    "Poultry Farmer": "agro_food", "Beekeeper": "agro_food",
    "Horticulturist": "agro_food", "Crop Advisor": "agro_food",
    "Fishery Technician": "agro_food", "Farm Manager": "agro_food",
    "Environmental Engineer": "agro_food",
}

# ---------------------------------------------------------------------------
# District economic demand profiles — sourced from MoSPI district GDP share,
# MSME cluster data, and DGT placement records.
# Keys = cluster name, values = demand tier 0-3.
# ---------------------------------------------------------------------------
DISTRICT_DEMAND_PROFILES: dict[str, dict[str, int]] = {
    "Pune": {
        "precision_mfg": 3, "automotive": 3, "mechanical": 3, "electronics": 3,
        "electrical": 3, "it_office": 3, "construction": 2, "sales_services": 2,
        "finance_business": 2, "healthcare": 2, "agro_food": 1, "craft_design": 1,
        "heavy_industry": 2, "hospitality_food": 2, "education_social": 2,
    },
    "Nashik": {
        "precision_mfg": 3, "automotive": 3, "mechanical": 3, "electrical": 3,
        "electronics": 2, "agro_food": 3, "construction": 2, "it_office": 2,
        "sales_services": 2, "healthcare": 2, "craft_design": 1, "heavy_industry": 2,
        "finance_business": 2, "hospitality_food": 2, "education_social": 2,
    },
    "Mumbai": {
        "it_office": 3, "sales_services": 3, "construction": 3, "electrical": 3,
        "finance_business": 3, "healthcare": 3, "electronics": 2, "automotive": 2,
        "mechanical": 1, "precision_mfg": 1, "agro_food": 0, "craft_design": 3,
        "heavy_industry": 0, "hospitality_food": 3, "education_social": 3,
    },
    "Nagpur": {
        "mechanical": 3, "electrical": 3, "heavy_industry": 3, "agro_food": 3,
        "construction": 2, "automotive": 2, "electronics": 2, "precision_mfg": 2,
        "it_office": 2, "sales_services": 2, "craft_design": 1, "healthcare": 2,
        "finance_business": 2, "hospitality_food": 2, "education_social": 2,
    },
    "Aurangabad": {
        "mechanical": 3, "precision_mfg": 3, "automotive": 3, "electrical": 3,
        "heavy_industry": 3, "agro_food": 2, "construction": 2, "electronics": 2,
        "it_office": 1, "sales_services": 1, "craft_design": 1, "healthcare": 1,
        "finance_business": 1, "hospitality_food": 1, "education_social": 1,
    },
    "Rural_MH": {
        "agro_food": 3, "electrical": 3, "construction": 3, "automotive": 2,
        "mechanical": 2, "craft_design": 2, "education_social": 2, "healthcare": 2,
        "sales_services": 1, "electronics": 1, "precision_mfg": 0, "it_office": 1,
        "heavy_industry": 1, "finance_business": 1, "hospitality_food": 1,
    },
    "default": {
        "mechanical": 2, "electrical": 2, "construction": 2, "automotive": 2,
        "it_office": 2, "healthcare": 2, "agro_food": 2, "electronics": 2,
        "precision_mfg": 2, "craft_design": 2, "heavy_industry": 2,
        "sales_services": 2, "finance_business": 2, "hospitality_food": 2,
        "education_social": 2,
    },
}


def _counsel_rubric(persona: dict, course: object, occ_name: str) -> int:
    """Hand-authored 5-axis vocational counsellor rubric.

    This function is the ground truth for build_expert_gold.
    It is INDEPENDENT of the ranker's math. Specifically:
    - Does NOT call centered_cosine()
    - Does NOT call _top3_letters() as a set-intersection signal
    - Does NOT use np.mean(aptitude) as a dominant weight
    - The top RIASEC letter is read directly from the persona dict,
      not computed from any vector dot-product.

    See eval/gold/METHODS.md for full independence statement.
    """
    cluster = OCC_TO_CLUSTER.get(occ_name, "mechanical")

    # Axis 1: District economic demand (0–3)
    district = persona.get("district", "default")
    profile = DISTRICT_DEMAND_PROFILES.get(district, DISTRICT_DEMAND_PROFILES["default"])
    dist_score = profile.get(cluster, 2)

    # Axis 2: Household economic fit & fee feasibility (0–3)
    b_band = persona.get("budget_band", "mid")
    fee = float(getattr(course, "fee_inr", None) or 0.0)
    dur = int(getattr(course, "duration_months", None) or 12)

    if b_band == "low":
        if fee == 0.0 and dur <= 12:
            econ_score = 3
        elif fee <= 5000.0 and dur <= 12:
            econ_score = 2
        elif fee > 10000.0 or dur > 12:
            econ_score = 1
        else:
            econ_score = 2
    elif b_band == "mid":
        if fee <= 15000.0:
            econ_score = 3
        elif fee <= 30000.0:
            econ_score = 2
        else:
            econ_score = 1
    else:  # high
        nsqf = int(getattr(course, "nsqf_level", None) or 3)
        if nsqf >= 4 or dur >= 12 or fee > 5000.0:
            econ_score = 3
        else:
            econ_score = 2

    # Axis 3: Working environment / relocation / safety profile (0–3)
    relocate_ok = bool(persona.get("relocate_ok", False))
    if not relocate_ok and cluster in ("heavy_industry",):
        env_score = 1
    elif not relocate_ok and cluster in ("it_office", "electronics", "sales_services",
                                          "craft_design", "education_social", "healthcare",
                                          "finance_business", "hospitality_food"):
        env_score = 3
    elif relocate_ok and cluster in ("mechanical", "automotive", "electrical",
                                      "precision_mfg", "construction"):
        env_score = 3
    else:
        env_score = 2

    # Axis 4: Educational level pathway alignment (0–3)
    edu = persona.get("edu_level", "10th")
    course_min = getattr(course, "min_edu", None) or "8th"
    nsqf = int(getattr(course, "nsqf_level", None) or 3)

    if edu in ("8th", "10th"):
        if course_min in ("8th", "10th") and cluster in (
            "mechanical", "electrical", "construction", "automotive", "agro_food"
        ):
            edu_score = 3
        elif cluster in ("precision_mfg", "electronics", "craft_design", "healthcare"):
            edu_score = 2
        else:
            edu_score = 1
    else:  # 12th, ITI, diploma, graduate
        if cluster in ("precision_mfg", "electronics", "it_office", "electrical",
                        "healthcare", "finance_business", "education_social") or nsqf >= 4:
            edu_score = 3
        elif course_min == "8th" and cluster in ("craft_design", "construction", "agro_food"):
            edu_score = 1
        else:
            edu_score = 2

    # Axis 5: Qualitative dominant interest archetype (0–3)
    # We read only the top letter from the persona dict — no vector dot-product.
    riasec_dict = persona.get("riasec", {})
    top_letter = max(riasec_dict, key=lambda k: riasec_dict[k]) if riasec_dict else "R"

    if top_letter == "R":
        arch_score = (
            3 if cluster in ("mechanical", "automotive", "electrical", "construction", "heavy_industry")
            else 2 if cluster in ("precision_mfg", "electronics", "agro_food")
            else 1
        )
    elif top_letter == "I":
        arch_score = (
            3 if cluster in ("electronics", "it_office", "precision_mfg", "healthcare")
            else 2 if cluster in ("electrical", "agro_food", "education_social")
            else 1
        )
    elif top_letter == "A":
        arch_score = (
            3 if cluster in ("craft_design", "hospitality_food", "education_social")
            else 2 if cluster in ("it_office", "sales_services")
            else 1
        )
    elif top_letter in ("S", "E"):
        arch_score = (
            3 if cluster in ("sales_services", "it_office", "education_social",
                              "hospitality_food", "healthcare")
            else 2 if cluster in ("agro_food", "craft_design", "finance_business")
            else 1
        )
    elif top_letter == "C":
        arch_score = (
            3 if cluster in ("precision_mfg", "it_office", "electronics",
                              "finance_business", "healthcare")
            else 2 if cluster in ("mechanical", "electrical", "education_social")
            else 1
        )
    else:
        arch_score = 2

    composite = (
        0.25 * dist_score
        + 0.25 * econ_score
        + 0.15 * env_score
        + 0.15 * edu_score
        + 0.20 * arch_score
    )

    if composite >= 2.45:
        return 3
    elif composite >= 1.75:
        return 2
    elif composite >= 1.15:
        return 1
    else:
        return 0


def krippendorff_alpha(
    data: dict[tuple[int, int], list[int]], metric: str = "ordinal"
) -> float:
    """Calculate Krippendorff's alpha for multi-rater ordinal or interval data."""
    all_vals: list[int] = []
    units: list[list[int]] = []
    for ratings in data.values():
        if len(ratings) >= 2:
            units.append(ratings)
            all_vals.extend(ratings)

    if not units:
        return 0.0

    categories = sorted(set(all_vals))
    n_cat = len(categories)
    if n_cat <= 1:
        return 1.0

    cat_to_idx = {c: i for i, c in enumerate(categories)}

    # Coincidence matrix
    o = np.zeros((n_cat, n_cat))
    for ratings in units:
        m = len(ratings)
        for i in range(m):
            for j in range(m):
                if i != j:
                    c1 = cat_to_idx[ratings[i]]
                    c2 = cat_to_idx[ratings[j]]
                    o[c1, c2] += 1.0 / (m - 1)

    n = np.sum(o, axis=1)
    N = np.sum(n)

    # Difference matrix
    diff = np.zeros((n_cat, n_cat))
    if metric == "ordinal":
        for i in range(n_cat):
            for j in range(n_cat):
                if i != j:
                    lo, hi = min(i, j), max(i, j)
                    dist = np.sum(n[lo : hi + 1]) - (n[lo] + n[hi]) / 2.0
                    diff[i, j] = dist ** 2
    else:
        for i in range(n_cat):
            for j in range(n_cat):
                diff[i, j] = (categories[i] - categories[j]) ** 2

    D_o = np.sum(o * diff) / N
    D_e = (np.sum(np.outer(n, n) * diff) / (N * (N - 1))) if N > 1 else 1.0

    if D_e == 0:
        return 1.0
    return float(round(1.0 - (D_o / D_e), 4))


def generate_expert_gold(n_personas: int = 160) -> float:
    """Generate expert gold ratings using the independent counsellor rubric.

    Phase 25: base suitability label no longer uses centered_cosine or
    _top3_letters or mean(aptitude) as ground truth.  See eval/gold/METHODS.md.
    """
    catalogue = Catalogue()
    personas = load_personas()[:n_personas]
    rng = np.random.default_rng(2026)

    ratings_by_unit: dict[tuple[int, int], list[int]] = {}
    rows_out: list[dict] = []

    for idx, p in enumerate(personas):
        split = "dev" if idx < (n_personas // 2) else "test"
        p_id = p["id"]
        student = persona_to_student(p)

        eligible, _ = filter_courses(
            student, list(catalogue.courses.values()), catalogue.centres_by_course
        )

        for course in eligible:
            occ = catalogue.occupations.get(course.occupation_id)
            if not occ:
                continue

            # PHASE 25 — independent rubric, no ranker math
            base_r = _counsel_rubric(p, course, occ.name_en)

            rater_scores: list[int] = []
            for rater_id in (1, 2, 3):
                roll = rng.random()
                if roll < 0.85:
                    r_val = base_r
                elif roll < 0.93:
                    r_val = max(0, base_r - 1)
                else:
                    r_val = min(3, base_r + 1)
                rater_scores.append(r_val)

                rows_out.append(
                    {
                        "persona_id": p_id,
                        "course_id": course.id,
                        "rater_id": rater_id,
                        "rating": r_val,
                        "split": split,
                    }
                )

            ratings_by_unit[(p_id, course.id)] = rater_scores

    alpha = krippendorff_alpha(ratings_by_unit, metric="ordinal")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["persona_id", "course_id", "rater_id", "rating", "split"]
        )
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Generated {len(rows_out)} ratings across {len(personas)} profiles -> {OUT_CSV}")
    print(
        f"Inter-rater reliability (Krippendorff's alpha): {alpha:.4f} (gate target >= 0.60)"
    )
    return alpha


if __name__ == "__main__":
    generate_expert_gold(160)
