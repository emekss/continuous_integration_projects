import pytest

from app.errors import NotFoundError, ValidationError


class TestBookingCrud:
    def test_create_booking(self, booking_service, apartment):
        b = booking_service.create(
            apartment.id, "2026-03-01", "2026-03-07"
        )
        assert b.id == 1
        assert b.apartment_id == apartment.id
        assert b.date_from == "2026-03-01"
        assert b.date_to == "2026-03-07"

    def test_list_bookings(self, booking_service, apartment):
        booking_service.create(apartment.id, "2026-03-01", "2026-03-02")
        booking_service.create(apartment.id, "2026-03-10", "2026-03-12")
        assert len(booking_service.list()) == 2

    def test_create_for_missing_apartment(self, booking_service):
        with pytest.raises(NotFoundError):
            booking_service.create(999, "2026-03-01", "2026-03-02")

    def test_change_dates(self, booking_service, apartment):
        b = booking_service.create(
            apartment.id, "2026-03-01", "2026-03-05"
        )
        changed = booking_service.change(
            b.id, date_to="2026-03-08"
        )
        assert changed.date_from == "2026-03-01"
        assert changed.date_to == "2026-03-08"

    def test_change_missing_booking(self, booking_service):
        with pytest.raises(NotFoundError):
            booking_service.change(999, date_to="2026-03-08")

    def test_change_nothing_raises(self, booking_service, apartment):
        b = booking_service.create(
            apartment.id, "2026-03-01", "2026-03-05"
        )
        with pytest.raises(ValidationError):
            booking_service.change(b.id)

    def test_cancel_booking(self, booking_service, apartment):
        b = booking_service.create(
            apartment.id, "2026-03-01", "2026-03-05"
        )
        booking_service.cancel(b.id)
        assert booking_service.list() == []

    def test_cancel_missing_booking(self, booking_service):
        with pytest.raises(NotFoundError):
            booking_service.cancel(999)


class TestDateValidation:
    @pytest.mark.parametrize(
        "date_from,date_to",
        [
            ("2026-03-05", "2026-03-01"),  # from after to
            ("2026-03-01", "2026-03-01"),  # same day = empty range
            ("not-a-date", "2026-03-01"),
            ("2026-03-01", "2026-13-01"),  # month 13
            ("03/01/2026", "2026-03-05"),  # wrong format
        ],
    )
    def test_invalid_ranges_rejected(
        self, booking_service, apartment, date_from, date_to
    ):
        with pytest.raises(ValidationError):
            booking_service.create(apartment.id, date_from, date_to)

    def test_change_to_invalid_range_rejected(
        self, booking_service, apartment
    ):
        b = booking_service.create(
            apartment.id, "2026-03-01", "2026-03-05"
        )
        with pytest.raises(ValidationError):
            booking_service.change(b.id, date_from="2026-03-10")
