from __future__ import annotations

import sqlite3


def upsert_user(conn: sqlite3.Connection, user_id: int, email: str) -> None:
    """Store a replicated copy of a user owned by the auth service."""
    conn.execute(
        "INSERT OR REPLACE INTO user_projection (id, email) VALUES (?, ?)",
        (user_id, email),
    )
    conn.commit()


def backfill_users(conn: sqlite3.Connection) -> None:
    """Initial sync of the projection from auth-owned data."""
    conn.execute(
        "INSERT OR REPLACE INTO user_projection (id, email)"
        " SELECT id, email FROM users"
    )
    conn.commit()
