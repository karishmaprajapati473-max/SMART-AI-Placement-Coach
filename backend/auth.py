from contextlib import contextmanager
import sqlite3
from pathlib import Path
from pwdlib import PasswordHash
import hashlib
import secrets
import time
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "users.db"

password_hash = PasswordHash.recommended()


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
role TEXT NOT NULL DEFAULT 'student'
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        user_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "role" not in user_columns:
            connection.execute("""
                ALTER TABLE users
                ADD COLUMN role TEXT NOT NULL DEFAULT 'student'
            """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS coding_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                topic TEXT,
                language TEXT NOT NULL,
                passed INTEGER NOT NULL,
                total INTEGER NOT NULL,
                weak_concept TEXT,
                confidence TEXT,
                diagnosis_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_attempts_user_date
            ON coding_attempts(user_id, created_at)
        """)

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(coding_attempts)"
            ).fetchall()
        }

        if "revised_concept" not in columns:
            connection.execute("""
                ALTER TABLE coding_attempts
                ADD COLUMN revised_concept TEXT
            """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS revision_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                weak_concept TEXT NOT NULL,
                question_id TEXT NOT NULL,
                topic TEXT,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_revision_user_date
            ON revision_events(user_id, created_at)
        """)
        revision_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(revision_events)"
            ).fetchall()
        }

        if "event_key" not in revision_columns:
            connection.execute("""
                ALTER TABLE revision_events
                ADD COLUMN event_key TEXT
            """)

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_revision_user_event_key
            ON revision_events(user_id, event_key)
        """)


def create_user(name: str, email: str, password: str):
    name = name.strip()
    email = email.strip().lower()

    if not name or not email or not password:
        raise ValueError("Name, email and password are required.")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    hashed_password = password_hash.hash(password)

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            raise ValueError("An account with this email already exists.")

        cursor = connection.execute(
            """INSERT INTO users (name, email, password_hash)
               VALUES (?, ?, ?)""",
            (name, email, hashed_password),
        )

        return {
            "id": cursor.lastrowid,
            "name": name,
            "email": email,
        }


def verify_user(email: str, password: str):
    email = email.strip().lower()

    with get_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

    if user is None:
        return None

    if not password_hash.verify(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }

def create_session(user_id: int):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = int(time.time())

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (now,)
        )

        connection.execute(
            """INSERT INTO sessions
               (token_hash, user_id, expires_at, created_at)
               VALUES (?, ?, ?, ?)""",
            (token_hash, user_id, now + 86400, now)
        )

    return token


def get_user_by_session(token: str):
    if not token:
        return None

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT users.id, users.name, users.email, users.role
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
              AND sessions.expires_at > ?
            """,
            (token_hash, int(time.time()))
        ).fetchone()

    return dict(user) if user else None


def revoke_session(token: str):
    if not token:
        return

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_hash,)
        )


def save_coding_attempt(
    user_id: int,
    question_id: str,
    topic: str,
    language: str,
    passed: int,
    total: int,
    diagnosis: dict,
    revised_concept: str | None = None,
):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO coding_attempts (
                user_id,
                question_id,
                topic,
                language,
                passed,
                total,
                weak_concept,
                confidence,
                diagnosis_method,
                revised_concept
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                question_id,
                topic,
                language,
                passed,
                total,
                diagnosis.get("weak_concept"),
                str(diagnosis.get("confidence", "")),
                diagnosis.get("method", "unknown"),
                revised_concept,
            )
        )

        return cursor.lastrowid
