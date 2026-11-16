"""Consent-based, privacy-conscious collection of coding-error samples.

Samples are stored as pseudonymous records linked to a local user id only so
that a student can withdraw consent and delete their contributions. The user
id is never included in training exports. Labels are intentionally left NULL
until a human reviewer assigns one.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Iterable

from auth import get_connection

CONSENT_VERSION = "ml-collection-v1"
ALLOWED_WEAK_CONCEPTS = {
    "Syntax & Indentation",
    "Variables & Naming",
    "Data Types & Input Handling",
    "Arrays & Indexing",
    "Loops & Iteration",
    "Recursion",
    "Function Usage",
    "Algorithm Efficiency",
}

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_URL_RE = re.compile(r"https?://\S+", re.I)
_WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\(?:[^\\\r\n]+\\)*[^\\\s\r\n]*")
_UNIX_PATH_RE = re.compile(r"(?<!\w)/(?:[A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_.-]+")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|authorization)\b"
    r"(\s*[:=]\s*)(['\"]?)[^\s,;]+"
)
_LONG_DIGITS_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def ensure_ml_collection_tables() -> None:
    """Create collection tables safely; call during backend startup."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_collection_consent (
                user_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
                consent_version TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_training_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                language TEXT NOT NULL,
                topic TEXT NOT NULL,
                diagnostic_message TEXT NOT NULL,
                code_snippet TEXT NOT NULL,
                passed INTEGER NOT NULL,
                total INTEGER NOT NULL,
                weak_concept TEXT,
                label_status TEXT NOT NULL DEFAULT 'pending_review'
                    CHECK (label_status IN ('pending_review', 'approved', 'rejected')),
                reviewer_note TEXT,
                consent_version TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                CHECK (weak_concept IS NULL OR weak_concept IN (
                    'Syntax & Indentation', 'Variables & Naming',
                    'Data Types & Input Handling', 'Arrays & Indexing',
                    'Loops & Iteration', 'Recursion', 'Function Usage',
                    'Algorithm Efficiency'
                ))
            )
            """
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_ml_samples_review
               ON ml_training_samples(label_status, created_at)"""
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_ml_samples_user
               ON ml_training_samples(user_id, created_at)"""
        )


def sanitize_text(value: str, personal_values: Iterable[str] = (), max_length: int = 3000) -> str:
    """Redact common identifiers/secrets before a candidate is persisted."""
    text = str(value or "")
    text = _CONTROL_RE.sub(" ", text)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(r"\1\2[REDACTED]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _URL_RE.sub("[REDACTED_URL]", text)
    text = _WINDOWS_PATH_RE.sub("[REDACTED_PATH]", text)
    text = _UNIX_PATH_RE.sub("[REDACTED_PATH]", text)
    text = _LONG_DIGITS_RE.sub("[REDACTED_NUMBER]", text)
    for personal_value in personal_values:
        candidate = str(personal_value or "").strip()
        if len(candidate) >= 3:
            text = re.sub(re.escape(candidate), "[REDACTED]", text, flags=re.I)
    return text[:max_length].strip()


def get_ml_consent(user_id: int) -> dict:
    ensure_ml_collection_tables()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT enabled, consent_version, updated_at FROM ml_collection_consent WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return {"enabled": False, "consent_version": CONSENT_VERSION, "updated_at": None}
    return {
        "enabled": bool(row["enabled"]),
        "consent_version": row["consent_version"],
        "updated_at": row["updated_at"],
    }


def set_ml_consent(user_id: int, enabled: bool) -> dict:
    """Record an explicit opt-in/out. Opt-out deletes this user's samples."""
    ensure_ml_collection_tables()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO ml_collection_consent (user_id, enabled, consent_version, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                enabled = excluded.enabled,
                consent_version = excluded.consent_version,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, 1 if enabled else 0, CONSENT_VERSION),
        )
        deleted_samples = 0
        if not enabled:
            cursor = connection.execute(
                "DELETE FROM ml_training_samples WHERE user_id = ?", (user_id,)
            )
            deleted_samples = cursor.rowcount
    return {
        "enabled": bool(enabled),
        "consent_version": CONSENT_VERSION,
        "deleted_samples": deleted_samples,
    }



_ENVIRONMENT_FAILURE_RE = re.compile(
    r"Docker API|Docker Desktop|Docker daemon|Docker engine|"
    r"failed to connect to the docker|dockerDesktopLinuxEngine|"
    r"npipe://|OCI runtime create failed|containerd|"
    r"pull access denied|no such image|manifest unknown|"
    r"error during connect|daemon is not running",
    re.I,
)


def is_environment_failure(message: str) -> bool:
    """Identify infrastructure failures, not student coding mistakes."""
    return bool(_ENVIRONMENT_FAILURE_RE.search(str(message or "")))


def store_error_candidate(
    *,
    user_id: int,
    question_id: str,
    language: str,
    topic: str,
    diagnostic_messages: Iterable[str],
    code_snippet: str,
    passed: int,
    total: int,
    personal_values: Iterable[str] = (),
) -> int | None:
    """Store a de-identified candidate only after explicit consent.

    The classifier's own prediction is deliberately not accepted as a label.
    Every row starts as pending_review with weak_concept=NULL.
    """
    ensure_ml_collection_tables()
    consent = get_ml_consent(user_id)
    if not consent["enabled"] or total <= 0 or passed >= total:
        return None

    diagnostic_items = [str(item) for item in diagnostic_messages if item]

    # Infrastructure failures must never enter the student-error dataset.
    if any(is_environment_failure(item) for item in diagnostic_items):
        return None

    raw_diagnostic = "\n".join(diagnostic_items)
    if not raw_diagnostic.strip():
        raw_diagnostic = f"Program failed evaluation: {passed} of {total} test cases passed."

    safe_diagnostic = sanitize_text(raw_diagnostic, personal_values, max_length=3000)
    safe_code = sanitize_text(code_snippet, personal_values, max_length=5000)
    if not safe_diagnostic or not safe_code:
        return None

    with get_connection() as connection:
        # Re-check consent in the same write transaction to avoid collecting
        # after a concurrent opt-out.
        row = connection.execute(
            "SELECT enabled, consent_version FROM ml_collection_consent WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None or not bool(row["enabled"]):
            return None
        cursor = connection.execute(
            """
            INSERT INTO ml_training_samples (
                user_id, question_id, language, topic, diagnostic_message,
                code_snippet, passed, total, weak_concept, label_status,
                consent_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'pending_review', ?)
            """,
            (
                user_id,
                str(question_id)[:100],
                str(language)[:30],
                str(topic)[:100],
                safe_diagnostic,
                safe_code,
                int(passed),
                int(total),
                row["consent_version"],
            ),
        )
        return int(cursor.lastrowid)

def list_pending_samples() -> list[dict]:
    """Return pending samples without exposing internal user IDs."""
    ensure_ml_collection_tables()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                question_id,
                language,
                topic,
                diagnostic_message,
                code_snippet,
                passed,
                total,
                label_status,
                created_at
            FROM ml_training_samples
            WHERE label_status = 'pending_review'
            ORDER BY created_at ASC
            LIMIT 100
            """
        ).fetchall()

    return [dict(row) for row in rows]


def reject_sample(
    sample_id: int,
    reviewer_note: str = ""
) -> None:
    """Reject a reviewed sample without assigning a training label."""
    ensure_ml_collection_tables()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE ml_training_samples
            SET
                label_status = 'rejected',
                weak_concept = NULL,
                reviewer_note = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND label_status = 'pending_review'
            """,
            (sanitize_text(reviewer_note, max_length=1000), sample_id),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Pending sample not found or already reviewed."
            )



def normalize_weak_concept(label: str) -> str:
    """Normalize spacing and case, returning an exact canonical label."""
    import re

    candidate = re.sub(r"\s*&\s*", " & ", str(label or ""))
    candidate = re.sub(r"\s+", " ", candidate).strip().casefold()

    for canonical in ALLOWED_WEAK_CONCEPTS:
        normalized = re.sub(r"\s*&\s*", " & ", canonical)
        normalized = re.sub(r"\s+", " ", normalized).strip().casefold()

        if candidate == normalized:
            return canonical

    raise ValueError(
        "Label is not one of the supported weak-concept categories."
    )




def validate_candidate_for_approval(sample: dict) -> list[str]:
    """Return quality issues that prevent a candidate from being approved."""
    issues = []

    diagnostic = str(sample["diagnostic_message"] or "")
    code = str(sample["code_snippet"] or "")

    if not str(sample["question_id"] or "").strip():
        issues.append("missing_question_id")

    if not str(sample["language"] or "").strip():
        issues.append("missing_language")

    if not str(sample["topic"] or "").strip():
        issues.append("missing_topic")

    if not diagnostic.strip():
        issues.append("missing_diagnostic")

    if not code.strip():
        issues.append("missing_code")

    try:
        passed = int(sample["passed"])
        total = int(sample["total"])

        if total <= 0 or passed < 0 or passed >= total:
            issues.append("invalid_test_counts")
    except (TypeError, ValueError):
        issues.append("invalid_test_counts")

    if is_environment_failure(diagnostic):
        issues.append("environment_failure")

    if sanitize_text(diagnostic, max_length=3000) != diagnostic:
        issues.append("diagnostic_requires_redaction")

    if sanitize_text(code, max_length=5000) != code:
        issues.append("code_requires_redaction")

    return issues


def review_sample(sample_id: int, label: str, reviewer_note: str = "") -> None:
    """Approve only a valid sample with active student consent."""
    canonical_label = normalize_weak_concept(label)
    ensure_ml_collection_tables()

    with get_connection() as connection:
        sample = connection.execute(
            """
            SELECT *
            FROM ml_training_samples
            WHERE id = ? AND label_status = 'pending_review'
            """,
            (sample_id,)
        ).fetchone()

        if sample is None:
            raise ValueError("Pending sample not found or already reviewed.")

        consent = connection.execute(
            """
            SELECT enabled
            FROM ml_collection_consent
            WHERE user_id = ?
            """,
            (sample["user_id"],)
        ).fetchone()

        if consent is None or not bool(consent["enabled"]):
            raise ValueError("Student consent is not active. Sample cannot be approved.")

        issues = validate_candidate_for_approval(dict(sample))

        if issues:
            raise ValueError(
                "Sample failed quality checks: " + ", ".join(issues)
            )

        cursor = connection.execute(
            """
            UPDATE ml_training_samples
            SET weak_concept = ?,
                label_status = 'approved',
                reviewer_note = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND label_status = 'pending_review'
              AND EXISTS (
                  SELECT 1
                  FROM ml_collection_consent c
                  WHERE c.user_id = ml_training_samples.user_id
                    AND c.enabled = 1
              )
            """,
            (
                canonical_label,
                sanitize_text(reviewer_note, max_length=1000),
                sample_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Sample could not be approved. Check its review status and consent."
            )




def load_approved_samples_for_training() -> list[dict]:
    """
    Internal training loader.
    user_id is retained only in memory for student-group splitting.
    It is never included in model features or public exports.
    """
    ensure_ml_collection_tables()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                s.user_id,
                s.question_id,
                s.language,
                s.topic,
                s.diagnostic_message,
                s.code_snippet,
                s.passed,
                s.total,
                s.weak_concept
            FROM ml_training_samples s
            INNER JOIN ml_collection_consent c
                ON c.user_id = s.user_id
               AND c.enabled = 1
            WHERE s.label_status = 'approved'
              AND s.weak_concept IS NOT NULL
            ORDER BY s.id
            """
        ).fetchall()

    accepted = []
    seen = set()

    for row in rows:
        sample = dict(row)

        try:
            canonical_label = normalize_weak_concept(
                sample["weak_concept"]
            )
        except (ValueError, TypeError):
            continue

        issues = validate_candidate_for_approval(sample)
        if issues:
            continue

        signature = (
            sample["language"],
            sample["topic"],
            sample["diagnostic_message"],
            sample["code_snippet"],
            canonical_label,
        )

        # Keep only one copy of identical training content.
        if signature in seen:
            continue

        seen.add(signature)
        sample["weak_concept"] = canonical_label
        accepted.append(sample)

    return accepted


def export_approved_samples() -> list[dict]:
    """Public reviewer export; never exposes user IDs or internal grouping."""
    training_rows = load_approved_samples_for_training()

    public_fields = (
        "language",
        "topic",
        "diagnostic_message",
        "code_snippet",
        "weak_concept",
    )

    return [
        {field: sample[field] for field in public_fields}
        for sample in training_rows
    ]
