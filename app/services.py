import sqlite3
from datetime import date

from app.errors import NotFoundError, OverlapError, ValidationError
from app.models import Apartment, Booking
from app.repository import ApartmentRepository, BookingRepository


def _validate_date_range(date_from: str, date_to: str) -> None:
    try:
        d_from = date.fromisoformat(date_from)
        d_to = date.fromisoformat(date_to)
    except ValueError:
        raise ValidationError(
            f"Invalid date(s): {date_from!r}, {date_to!r}."
            " Expected ISO format YYYY-MM-DD."
        ) from None
    if date_from != d_from.isoformat() or date_to != d_to.isoformat():
        raise ValidationError(
            f"Invalid date(s): {date_from!r}, {date_to!r}."
            " Expected ISO format YYYY-MM-DD."
        )
    if date_from >= date_to:
        raise ValidationError("date_from must be before date_to.")


class ApartmentService:
    def __init__(self, conn: sqlite3.Connection):
        self.apartments = ApartmentRepository(conn)

    def add(self, name: str, address: str) -> Apartment:
        if not name.strip():
            raise ValidationError("name must not be empty.")
        if not address.strip():
            raise ValidationError("address must not be empty.")
        return self.apartments.create(name, address)

    def get(self, apartment_id: int) -> Apartment:
        apt = self.apartments.get(apartment_id)
        if apt is None:
            raise NotFoundError(f"Apartment {apartment_id} not found.")
        return apt

    def list(self) -> list[Apartment]:
        return self.apartments.list()

    def update(
        self,
        apartment_id: int,
        name: str | None = None,
        address: str | None = None,
    ) -> Apartment:
        self.get(apartment_id)
        if name is None and address is None:
            raise ValidationError(
                "Nothing to update: pass --name and/or --address."
            )
        return self.apartments.update(apartment_id, name, address)

    def remove(self, apartment_id: int) -> None:
        self.get(apartment_id)
        if self.apartments.has_bookings(apartment_id):
            raise ValidationError(
                f"Apartment {apartment_id} has bookings;"
                " cancel them before removing it."
            )
        self.apartments.delete(apartment_id)

    def search(self, date_from: str, date_to: str) -> list[Apartment]:
        _validate_date_range(date_from, date_to)
        return self.apartments.search_available(date_from, date_to)


class BookingService:
    def __init__(self, conn: sqlite3.Connection):
        self.bookings = BookingRepository(conn)
        self.apartments = ApartmentRepository(conn)

    def create(
        self, apartment_id: int, date_from: str, date_to: str
    ) -> Booking:
        _validate_date_range(date_from, date_to)
        if self.apartments.get(apartment_id) is None:
            raise NotFoundError(f"Apartment {apartment_id} not found.")
        if self.bookings.has_overlap(apartment_id, date_from, date_to):
            raise OverlapError(
                f"Apartment {apartment_id} is already booked"
                f" during {date_from}..{date_to}."
            )
        return self.bookings.create(apartment_id, date_from, date_to)

    def get(self, booking_id: int) -> Booking:
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise NotFoundError(f"Booking {booking_id} not found.")
        return booking

    def list(self) -> list[Booking]:
        return self.bookings.list()

    def change(
        self,
        booking_id: int,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> Booking:
        booking = self.get(booking_id)
        if date_from is None and date_to is None:
            raise ValidationError(
                "Nothing to change: pass --from and/or --to."
            )
        new_from = date_from if date_from is not None else booking.date_from
        new_to = date_to if date_to is not None else booking.date_to
        _validate_date_range(new_from, new_to)
        if self.bookings.has_overlap(
            booking.apartment_id,
            new_from,
            new_to,
            exclude_booking_id=booking_id,
        ):
            raise OverlapError(
                f"Apartment {booking.apartment_id} is already booked"
                f" during {new_from}..{new_to}."
            )
        return self.bookings.update(booking_id, date_from, date_to)

    def cancel(self, booking_id: int) -> None:
        if not self.bookings.delete(booking_id):
            raise NotFoundError(f"Booking {booking_id} not found.")
