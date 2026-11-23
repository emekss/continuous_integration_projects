from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sqlite3

from app.errors import ValidationError

ITERATIONS = 200_000
SALT_BYTES = 16


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, ITERATIONS
    )


def create_user(conn: sqlite3.Connection, email: str, password: str) -> int:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValidationError("Invalid email address.")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    salt = secrets.token_bytes(SALT_BYTES)
    stored = base64.b64encode(salt + _hash(password, salt)).decode()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, stored),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValidationError("Email already registered.") from None


def authenticate(
    conn: sqlite3.Connection, email: str, password: str
) -> int | None:
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    if row is None:
        return None
    raw = base64.b64decode(row[1])
    salt, digest = raw[:SALT_BYTES], raw[SALT_BYTES:]
    if not hmac.compare_digest(_hash(password, salt), digest):
        return None
    return row[0]


def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO session (token, user_id) VALUES (?, ?)",
        (token, user_id),
    )
    conn.commit()
    return token


def user_for_token(
    conn: sqlite3.Connection, token: str, user_table: str = "users"
) -> dict | None:
    row = conn.execute(
        f"SELECT u.id, u.email FROM session s"
        f" JOIN {user_table} u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    ).fetchone()
    return {"id": row[0], "email": row[1]} if row else None


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM session WHERE token = ?", (token,))
    conn.commit()
