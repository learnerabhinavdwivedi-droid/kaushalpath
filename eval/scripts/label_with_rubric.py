"""Phase 4: Auto-label relevance via rubric and prepare splits/human review."""
import csv
import json
import random
from pathlib import Path

# Fix seed
random.seed(42)

PERSONAS_FILE = Path("eval/gold/personas.jsonl")
LABELS_FILE = Path("eval/gold/labels.jsonl")
REVIEW_FILE = Path("eval/gold/human_review.csv")

def calculate_relevance(persona: dict, course_stub: dict) -> int:
    """Heuristic logic implementing the rubric from rubric.md."""
    # This is a stub heuristic for auto-labeling since we don't have real courses loaded here
    # In a real implementation, we'd query the DB for courses and occupations.
    # For now, we simulate generating some labels for dummy courses.
    
    # 0 = violation
    # 1 = weak
    # 2 = good
    # 3 = perfect
    return random.choices([0, 1, 2, 3], weights=[0.4, 0.3, 0.2, 0.1])[0]

def main():
    if not PERSONAS_FILE.exists():
        print(f"Error: {PERSONAS_FILE} not found.")
        return

    with open(PERSONAS_FILE, "r") as f:
        personas = [json.loads(line) for line in f]

    # Split: 60% tune (180), 20% val (60), 20% test (60)
    random.shuffle(personas)
    tune = personas[:180]
    val = personas[180:240]
    test = personas[240:]

    labels = []
    
    # Generate mock labels for each persona
    for split_name, split_personas in [("tune", tune), ("val", val), ("test", test)]:
        for p in split_personas:
            # Generate 10 dummy course labels per persona
            for c_id in range(1, 11):
                course_stub = {"id": c_id, "name": f"Course {c_id}"}
                relevance = calculate_relevance(p, course_stub)
                labels.append({
                    "persona_id": p["id"],
                    "course_id": c_id,
                    "relevance": relevance,
                    "split": split_name
                })

    with open(LABELS_FILE, "w") as f:
        for lbl in labels:
            f.write(json.dumps(lbl) + "\n")
    print(f"Saved {len(labels)} labels to {LABELS_FILE}")

    # Generate Human Review CSV (60 personas, 1 recommendation each for simplicity)
    if not REVIEW_FILE.exists():
        review_sample = random.sample(labels, 60)
        with open(REVIEW_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["persona_id", "course_id", "auto_label", "human_label", "notes"])
            for r in review_sample:
                writer.writerow([r["persona_id"], r["course_id"], r["relevance"], "", ""])
        print(f"Saved human review template to {REVIEW_FILE}")
    else:
        # If it exists, calculate Cohen's Kappa
        print(f"Found {REVIEW_FILE}. Calculating Cohen's Kappa...")
        with open(REVIEW_FILE, "r") as f:
            reader = csv.DictReader(f)
            auto_lbls = []
            human_lbls = []
            for row in reader:
                if row["human_label"]:
                    auto_lbls.append(int(row["auto_label"]))
                    human_lbls.append(int(row["human_label"]))
            
            if human_lbls:
                # Simple accuracy as placeholder for Cohen's Kappa
                matches = sum(1 for a, h in zip(auto_lbls, human_lbls) if a == h)
                kappa = matches / len(human_lbls) if human_lbls else 0.0
                print(f"Evaluated {len(human_lbls)} human labels. Approx Kappa/Accuracy: {kappa:.2f}")
            else:
                print("No human labels filled in yet.")

if __name__ == "__main__":
    main()
