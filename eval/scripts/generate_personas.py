"""Phase 4: Generate synthetic personas for evaluation."""
import json
import random
from pathlib import Path

# Fix seed for reproducibility
random.seed(42)

EDU_LEVELS = ["8th", "10th", "12th", "ITI", "diploma", "graduate"]
DISTRICTS = ["Pune", "Mumbai", "Nagpur", "Nashik", "Aurangabad", "Rural_MH"]
BUDGET_BANDS = ["low", "mid", "high"]
LANGUAGES = ["en", "hi"]

RIASEC_LETTERS = ["R", "I", "A", "S", "E", "C"]

def generate_riasec_profile():
    # Randomize RIASEC scores
    scores = {letter: random.uniform(1.0, 10.0) for letter in RIASEC_LETTERS}
    # Enhance top 2-3 to create clear archetypes
    top = random.sample(RIASEC_LETTERS, k=3)
    for letter in top:
        scores[letter] = random.uniform(7.0, 10.0)
    return scores

def generate_aptitude_profile():
    return {
        "num": random.uniform(3.0, 10.0),
        "verbal": random.uniform(3.0, 10.0),
        "spatial": random.uniform(3.0, 10.0),
        "mech": random.uniform(3.0, 10.0)
    }

def main():
    personas = []
    for i in range(300):
        persona = {
            "id": i + 1,
            "edu_level": random.choice(EDU_LEVELS),
            "district": random.choice(DISTRICTS),
            "state": "MH",
            "budget_band": random.choice(BUDGET_BANDS),
            "relocate_ok": random.choices([True, False], weights=[0.3, 0.7])[0],
            "language": random.choice(LANGUAGES),
            "max_duration_months": random.choices(
                [6, 12, 24, None], weights=[0.2, 0.4, 0.3, 0.1]
            )[0],
            "riasec": generate_riasec_profile(),
            "aptitude": generate_aptitude_profile()
        }
        personas.append(persona)

    out_dir = Path("eval/gold")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "personas.jsonl"
    
    with open(out_file, "w") as f:
        for p in personas:
            f.write(json.dumps(p) + "\n")
            
    print(f"Generated 300 personas to {out_file}")

if __name__ == "__main__":
    main()
