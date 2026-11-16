from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import get_connection

WEAK_CONCEPTS = [
    "Syntax & Indentation",
    "Variables & Naming",
    "Data Types & Input Handling",
    "Arrays & Indexing",
    "Loops & Iteration",
    "Recursion",
    "Function Usage",
    "Algorithm Efficiency",
]

with get_connection() as connection:
    status_rows = connection.execute("""
        SELECT label_status, COUNT(*) AS total
        FROM ml_training_samples
        GROUP BY label_status
    """).fetchall()

    category_rows = connection.execute("""
        SELECT weak_concept,
               COUNT(*) AS samples,
               COUNT(DISTINCT user_id) AS students
        FROM ml_training_samples
        WHERE label_status = 'approved'
        GROUP BY weak_concept
    """).fetchall()

status_counts = {row["label_status"]: row["total"] for row in status_rows}
category_counts = {row["weak_concept"]: row for row in category_rows}

print("\n=== REAL ML DATASET READINESS ===")
print("Pending review:", status_counts.get("pending_review", 0))
print("Approved:", status_counts.get("approved", 0))
print("Rejected:", status_counts.get("rejected", 0))

print("\n=== HUMAN-APPROVED SAMPLES BY CATEGORY ===")
for concept in WEAK_CONCEPTS:
    row = category_counts.get(concept)
    samples = row["samples"] if row else 0
    students = row["students"] if row else 0
    print(f"{concept}: {samples} samples | {students} students")

print("\nInitial pilot target: 30 samples per category from at least 5 students.")
print("This is a starting target, not proof of production readiness.")
