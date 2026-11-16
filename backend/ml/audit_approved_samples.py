from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import get_connection
from ml.data_collection import (
    ALLOWED_WEAK_CONCEPTS,
    normalize_weak_concept,
    is_environment_failure,
    sanitize_text,
)

with get_connection() as connection:
    rows = connection.execute("""
        SELECT
            id, user_id, language, topic,
            diagnostic_message, code_snippet,
            passed, total, weak_concept
        FROM ml_training_samples
        WHERE label_status = 'approved'
        ORDER BY id
    """).fetchall()

counts = {
    "approved": len(rows),
    "valid": 0,
    "invalid_label": 0,
    "noncanonical_label": 0,
    "missing_text": 0,
    "invalid_test_counts": 0,
    "environment_failure": 0,
    "needs_redaction": 0,
    "duplicate_content": 0,
}

category_stats = {
    label: {"samples": 0, "students": set()}
    for label in ALLOWED_WEAK_CONCEPTS
}

seen = set()

for row in rows:
    item = dict(row)
    problems = []

    try:
        canonical = normalize_weak_concept(item["weak_concept"])
        if item["weak_concept"] != canonical:
            counts["noncanonical_label"] += 1
            problems.append("noncanonical_label")
    except (ValueError, TypeError):
        counts["invalid_label"] += 1
        problems.append("invalid_label")
        canonical = None

    diagnostic = str(item["diagnostic_message"] or "")
    code = str(item["code_snippet"] or "")

    if not diagnostic.strip() or not code.strip() or not str(item["language"] or "").strip():
        counts["missing_text"] += 1
        problems.append("missing_text")

    try:
        passed = int(item["passed"])
        total = int(item["total"])
        if total <= 0 or passed < 0 or passed >= total:
            counts["invalid_test_counts"] += 1
            problems.append("invalid_test_counts")
    except (ValueError, TypeError):
        counts["invalid_test_counts"] += 1
        problems.append("invalid_test_counts")

    if is_environment_failure(diagnostic):
        counts["environment_failure"] += 1
        problems.append("environment_failure")

    if (
        sanitize_text(diagnostic) != diagnostic
        or sanitize_text(code) != code
    ):
        counts["needs_redaction"] += 1
        problems.append("needs_redaction")

    signature = (
        item["language"],
        item["topic"],
        diagnostic,
        code,
        canonical,
    )

    if signature in seen:
        counts["duplicate_content"] += 1
        problems.append("duplicate_content")
    seen.add(signature)

    if not problems and canonical:
        counts["valid"] += 1
        category_stats[canonical]["samples"] += 1
        category_stats[canonical]["students"].add(item["user_id"])

print("\n=== APPROVED DATASET QUALITY AUDIT ===")
for key, value in counts.items():
    print(f"{key}: {value}")

print("\n=== CATEGORY COVERAGE ===")
for label in sorted(category_stats):
    stats = category_stats[label]
    print(
        f"{label}: {stats['samples']} valid samples | "
        f"{len(stats['students'])} distinct students"
    )

print("\nAudit only: no records were modified or deleted.")
print("Training eligibility requires resolving every flagged issue.")
