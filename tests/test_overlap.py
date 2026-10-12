import pytest

from app.errors import OverlapError


class TestOverlap:
    """Existing booking: 2026-04-10 .. 2026-04-20 (half-open range)."""

    @pytest.fixture
    def existing(self, booking_service, apartment):
        return booking_service.create(
            apartment.id, "2026-04-10", "2026-04-20"
        )

    @pytest.mark.parametrize(
        "date_from,date_to",
        [
            ("2026-04-10", "2026-04-20"),  # exact same range
            ("2026-04-05", "2026-04-15"),  # overlaps the start
            ("2026-04-15", "2026-04-25"),  # overlaps the end
            ("2026-04-12", "2026-04-18"),  # fully inside
            ("2026-04-01", "2026-04-30"),  # fully covers
            ("2026-04-19", "2026-04-25"),  # touches last day
        ],
    )
    def test_overlapping_rejected(
        self, booking_service, apartment, existing, date_from, date_to
    ):
        with pytest.raises(OverlapError):
            booking_service.create(apartment.id, date_from, date_to)

    @pytest.mark.parametrize(
        "date_from,date_to",
        [
            ("2026-04-20", "2026-04-25"),  # check-in on checkout day
            ("2026-04-01", "2026-04-10"),  # checkout on check-in day
            ("2026-05-01", "2026-05-05"),  # completely after
            ("2026-03-01", "2026-03-05"),  # completely before
        ],
    )
    def test_non_overlapping_allowed(
        self, booking_service, apartment, existing, date_from, date_to
    ):
        b = booking_service.create(apartment.id, date_from, date_to)
        assert b.id is not None

    def test_other_apartment_unaffected(
        self,
        booking_service,
        apartment_service,
        apartment,
        existing,
    ):
        other = apartment_service.add("Other", "5 Elm St")
        b = booking_service.create(
            other.id, "2026-04-10", "2026-04-20"
        )
        assert b.apartment_id == other.id

    def test_change_onto_own_dates_allowed(
        self, booking_service, existing
    ):
        changed = booking_service.change(
            existing.id,
            date_from="2026-04-10",
            date_to="2026-04-20",
        )
        assert changed.date_from == "2026-04-10"

    def test_change_onto_other_booking_rejected(
        self, booking_service, apartment, existing
    ):
        other = booking_service.create(
            apartment.id, "2026-04-25", "2026-04-30"
        )
        with pytest.raises(OverlapError):
            booking_service.change(
                other.id, date_from="2026-04-18"
            )

    def test_change_can_move_into_gap(
        self, booking_service, apartment, existing
    ):
        other = booking_service.create(
            apartment.id, "2026-04-25", "2026-04-30"
        )
        changed = booking_service.change(
            other.id, date_from="2026-04-20"
        )
        assert changed.date_from == "2026-04-20"
        assert changed.date_to == "2026-04-30"

    def test_freed_dates_after_cancel(
        self, booking_service, apartment, existing
    ):
        booking_service.cancel(existing.id)
        b = booking_service.create(
            apartment.id, "2026-04-10", "2026-04-20"
        )
        assert b.id != existing.id
