"""Business logic and persistence (SQLite) for apartment bookings.

This module is the documented, GUI-free API. The CLI (booking.py) is just a
thin wrapper around BookingService.

Date rules
----------
* Dates are ISO strings ``YYYY-MM-DD``.
* ``from`` is the check-in day (inclusive), ``to`` is the check-out day
  (exclusive). So 2026-11-01 -> 2026-11-05 is 4 nights, and a booking that
  starts on 2026-11-05 does NOT overlap it.
* Two bookings for the same apartment overlap when
  ``a.from < b.to and b.from < a.to``.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date

DEFAULT_DB = "booking.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS apartments (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    address TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL REFERENCES apartments(id),
    start_date   TEXT NOT NULL,
    end_date     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','cancelled')),
    CHECK (start_date < end_date)
);
CREATE INDEX IF NOT EXISTS idx_bookings_apt ON bookings(apartment_id, status);
"""


class BookingError(Exception):
    """Base class for all expected errors."""


class ValidationError(BookingError):
    """Bad input (empty name, malformed date, end before start, ...)."""


class NotFoundError(BookingError):
    """Apartment or booking does not exist."""


class ConflictError(BookingError):
    """Operation would break a rule (overlapping booking, etc.)."""


def parse_date(value, label="date"):
    """Return an ISO date string, or raise ValidationError."""
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValidationError(f"Invalid {label} '{value}': use YYYY-MM-DD")


def _check_range(start, end):
    start, end = parse_date(start, "from date"), parse_date(end, "to date")
    if start >= end:
        raise ValidationError("'to' date must be after 'from' date")
    return start, end


def _clean(value, label):
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{label} must not be empty")
    return value


class BookingService:
    """Public API. Every method returns plain dicts / lists of dicts."""

    def __init__(self, db_path=None):
        self.db_path = db_path or os.environ.get("BOOKING_DB", DEFAULT_DB)
        con = sqlite3.connect(self.db_path, timeout=10)
        try:
            con.executescript(SCHEMA)  # idempotent (CREATE ... IF NOT EXISTS)
        finally:
            con.close()

    # ---------------------------------------------------------- internals
    @contextmanager
    def _tx(self):
        """One connection + one write transaction per operation.

        BEGIN IMMEDIATE takes the write lock up front so the
        'check for overlap, then insert' sequence can't race with another
        process.
        """
        con = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.execute("COMMIT")
        except BaseException:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    @staticmethod
    def _apartment(con, apartment_id):
        row = con.execute("SELECT * FROM apartments WHERE id = ?",
                          (apartment_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Apartment {apartment_id} not found")
        return row

    @staticmethod
    def _booking(con, booking_id):
        row = con.execute("SELECT * FROM bookings WHERE id = ?",
                          (booking_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Booking {booking_id} not found")
        return row

    @staticmethod
    def _overlaps(con, apartment_id, start, end, ignore_booking_id=None):
        """Active bookings of the apartment that overlap [start, end)."""
        return con.execute(
            """SELECT id, start_date, end_date FROM bookings
               WHERE apartment_id = ? AND status = 'active' AND id != ?
                 AND start_date < ? AND end_date > ?""",
            (apartment_id, ignore_booking_id or -1, end, start)).fetchall()

    @staticmethod
    def _conflict(rows):
        r = rows[0]
        return ConflictError(
            f"Apartment is already booked from {r['start_date']} to "
            f"{r['end_date']} (booking {r['id']})")

    # --------------------------------------------------------- apartments
    def add_apartment(self, name, address):
        name, address = _clean(name, "name"), _clean(address, "address")
        with self._tx() as con:
            cur = con.execute(
                "INSERT INTO apartments (name, address) VALUES (?, ?)",
                (name, address))
            return dict(self._apartment(con, cur.lastrowid))

    def list_apartments(self):
        with self._tx() as con:
            return [dict(r) for r in
                    con.execute("SELECT * FROM apartments ORDER BY id")]

    def update_apartment(self, apartment_id, name=None, address=None):
        if name is None and address is None:
            raise ValidationError("Nothing to update: give --name and/or --address")
        with self._tx() as con:
            row = self._apartment(con, apartment_id)
            new_name = _clean(name, "name") if name is not None else row["name"]
            new_addr = _clean(address, "address") if address is not None else row["address"]
            con.execute("UPDATE apartments SET name = ?, address = ? WHERE id = ?",
                        (new_name, new_addr, apartment_id))
            return dict(self._apartment(con, apartment_id))

    def remove_apartment(self, apartment_id):
        """Refuses if the apartment still has active bookings."""
        with self._tx() as con:
            row = self._apartment(con, apartment_id)
            active = con.execute(
                "SELECT COUNT(*) FROM bookings WHERE apartment_id = ? AND status = 'active'",
                (apartment_id,)).fetchone()[0]
            if active:
                raise ConflictError(
                    f"Apartment {apartment_id} has {active} active booking(s); "
                    "cancel them first")
            con.execute("DELETE FROM bookings WHERE apartment_id = ?", (apartment_id,))
            con.execute("DELETE FROM apartments WHERE id = ?", (apartment_id,))
            return dict(row)

    def search_apartments(self, start, end):
        """Apartments with no active booking overlapping [start, end)."""
        start, end = _check_range(start, end)
        with self._tx() as con:
            rows = con.execute(
                """SELECT * FROM apartments a WHERE NOT EXISTS (
                       SELECT 1 FROM bookings b
                       WHERE b.apartment_id = a.id AND b.status = 'active'
                         AND b.start_date < ? AND b.end_date > ?)
                   ORDER BY a.id""", (end, start)).fetchall()
            return [dict(r) for r in rows]

    # ----------------------------------------------------------- bookings
    def create_booking(self, apartment_id, start, end):
        start, end = _check_range(start, end)
        with self._tx() as con:
            self._apartment(con, apartment_id)
            clash = self._overlaps(con, apartment_id, start, end)
            if clash:
                raise self._conflict(clash)
            cur = con.execute(
                "INSERT INTO bookings (apartment_id, start_date, end_date) VALUES (?, ?, ?)",
                (apartment_id, start, end))
            return dict(self._booking(con, cur.lastrowid))

    def list_bookings(self, include_cancelled=True):
        sql = "SELECT * FROM bookings"
        if not include_cancelled:
            sql += " WHERE status = 'active'"
        with self._tx() as con:
            return [dict(r) for r in con.execute(sql + " ORDER BY id")]

    def change_booking(self, booking_id, start=None, end=None):
        if start is None and end is None:
            raise ValidationError("Nothing to change: give --from and/or --to")
        with self._tx() as con:
            row = self._booking(con, booking_id)
            if row["status"] == "cancelled":
                raise ConflictError(f"Booking {booking_id} is cancelled and cannot be changed")
            new_start, new_end = _check_range(start or row["start_date"],
                                              end or row["end_date"])
            clash = self._overlaps(con, row["apartment_id"], new_start, new_end,
                                   ignore_booking_id=booking_id)
            if clash:
                raise self._conflict(clash)
            con.execute("UPDATE bookings SET start_date = ?, end_date = ? WHERE id = ?",
                        (new_start, new_end, booking_id))
            return dict(self._booking(con, booking_id))

    def cancel_booking(self, booking_id):
        """Marks the booking cancelled (kept for history); dates become free."""
        with self._tx() as con:
            row = self._booking(con, booking_id)
            if row["status"] == "cancelled":
                raise ConflictError(f"Booking {booking_id} is already cancelled")
            con.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?",
                        (booking_id,))
            return dict(self._booking(con, booking_id))
