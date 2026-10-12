import sqlite3

from app.models import Apartment, Booking


class ApartmentRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, name: str, address: str) -> Apartment:
        cur = self.conn.execute(
            """
            INSERT INTO apartment (id, name, address)
            VALUES (
                (SELECT MIN(candidate) FROM (
                    SELECT 1 AS candidate
                    UNION ALL SELECT id + 1 FROM apartment
                ) WHERE candidate NOT IN (SELECT id FROM apartment)),
                ?, ?
            )
            """,
            (name, address),
        )
        self.conn.commit()
        return Apartment(id=cur.lastrowid, name=name, address=address)

    def get(self, apartment_id: int) -> Apartment | None:
        row = self.conn.execute(
            "SELECT id, name, address FROM apartment WHERE id = ?",
            (apartment_id,),
        ).fetchone()
        return Apartment(*row) if row else None

    def list(self) -> list[Apartment]:
        rows = self.conn.execute(
            "SELECT id, name, address FROM apartment ORDER BY id"
        ).fetchall()
        return [Apartment(*r) for r in rows]

    def update(
        self,
        apartment_id: int,
        name: str | None = None,
        address: str | None = None,
    ) -> Apartment | None:
        apt = self.get(apartment_id)
        if apt is None:
            return None
        new_name = name if name is not None else apt.name
        new_address = address if address is not None else apt.address
        self.conn.execute(
            "UPDATE apartment SET name = ?, address = ? WHERE id = ?",
            (new_name, new_address, apartment_id),
        )
        self.conn.commit()
        return Apartment(id=apartment_id, name=new_name, address=new_address)

    def delete(self, apartment_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM apartment WHERE id = ?", (apartment_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def has_bookings(self, apartment_id: int) -> bool:
        return (
            self.conn.execute(
                "SELECT 1 FROM booking WHERE apartment_id = ? LIMIT 1",
                (apartment_id,),
            ).fetchone()
            is not None
        )

    def search_available(self, date_from: str, date_to: str) -> list[Apartment]:
        rows = self.conn.execute(
            """
            SELECT a.id, a.name, a.address FROM apartment a
            WHERE NOT EXISTS (
                SELECT 1 FROM booking b
                WHERE b.apartment_id = a.id
                  AND ? < b.date_to AND ? > b.date_from
            )
            ORDER BY a.id
            """,
            (date_from, date_to),
        ).fetchall()
        return [Apartment(*r) for r in rows]


class BookingRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self, apartment_id: int, date_from: str, date_to: str
    ) -> Booking:
        cur = self.conn.execute(
            "INSERT INTO booking (apartment_id, date_from, date_to)"
            " VALUES (?, ?, ?)",
            (apartment_id, date_from, date_to),
        )
        self.conn.commit()
        return Booking(
            id=cur.lastrowid,
            apartment_id=apartment_id,
            date_from=date_from,
            date_to=date_to,
        )

    def get(self, booking_id: int) -> Booking | None:
        row = self.conn.execute(
            "SELECT id, apartment_id, date_from, date_to"
            " FROM booking WHERE id = ?",
            (booking_id,),
        ).fetchone()
        return Booking(*row) if row else None

    def list(self) -> list[Booking]:
        rows = self.conn.execute(
            "SELECT id, apartment_id, date_from, date_to"
            " FROM booking ORDER BY id"
        ).fetchall()
        return [Booking(*r) for r in rows]

    def update(
        self,
        booking_id: int,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> Booking | None:
        booking = self.get(booking_id)
        if booking is None:
            return None
        new_from = date_from if date_from is not None else booking.date_from
        new_to = date_to if date_to is not None else booking.date_to
        self.conn.execute(
            "UPDATE booking SET date_from = ?, date_to = ? WHERE id = ?",
            (new_from, new_to, booking_id),
        )
        self.conn.commit()
        return Booking(
            id=booking_id,
            apartment_id=booking.apartment_id,
            date_from=new_from,
            date_to=new_to,
        )

    def delete(self, booking_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM booking WHERE id = ?", (booking_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def has_overlap(
        self,
        apartment_id: int,
        date_from: str,
        date_to: str,
        exclude_booking_id: int | None = None,
    ) -> bool:
        sql = (
            "SELECT 1 FROM booking"
            " WHERE apartment_id = ? AND ? < date_to AND ? > date_from"
        )
        params: list = [apartment_id, date_from, date_to]
        if exclude_booking_id is not None:
            sql += " AND id != ?"
            params.append(exclude_booking_id)
        return (
            self.conn.execute(sql + " LIMIT 1", params).fetchone()
            is not None
        )
