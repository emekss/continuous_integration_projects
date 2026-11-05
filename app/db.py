import os
import sqlite3

DEFAULT_DB_PATH = "booking.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS apartment (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    address TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS booking (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL REFERENCES apartment(id),
    date_from    TEXT NOT NULL,
    date_to      TEXT NOT NULL,
    CHECK (date_from < date_to)
);
"""


def get_db_path() -> str:
    return os.environ.get("BOOKING_DB", DEFAULT_DB_PATH)


def connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
