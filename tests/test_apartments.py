import pytest

from app.errors import NotFoundError, ValidationError


class TestApartmentCrud:
    def test_add_returns_apartment_with_id(self, apartment_service):
        apt = apartment_service.add("Loft", "2 Oak Ave")
        assert apt.id == 1
        assert apt.name == "Loft"
        assert apt.address == "2 Oak Ave"

    def test_list_returns_all_in_order(self, apartment_service):
        apartment_service.add("A", "addr-a")
        apartment_service.add("B", "addr-b")
        apts = apartment_service.list()
        assert [a.name for a in apts] == ["A", "B"]

    def test_add_fills_lowest_gap_without_renumbering_booked_apartment(
        self, apartment_service, booking_service
    ):
        apartments = [
            apartment_service.add(str(i), "address") for i in range(1, 7)
        ]
        booking = booking_service.create(
            apartments[5].id, "2026-01-10", "2026-01-15"
        )
        apartment_service.remove(apartments[4].id)
        apartment_service.remove(apartments[2].id)

        assert apartment_service.add("Replacement", "address").id == 3
        assert apartment_service.add("Next", "address").id == 5
        assert apartment_service.add("Last", "address").id == 7
        assert booking_service.get(booking.id).apartment_id == 6
        assert [apt.id for apt in apartment_service.list()] == list(range(1, 8))

    def test_update_name_only(self, apartment_service, apartment):
        updated = apartment_service.update(apartment.id, name="New Name")
        assert updated.name == "New Name"
        assert updated.address == apartment.address

    def test_update_address_only(self, apartment_service, apartment):
        updated = apartment_service.update(
            apartment.id, address="9 New Rd"
        )
        assert updated.address == "9 New Rd"
        assert updated.name == apartment.name

    def test_update_nothing_raises(self, apartment_service, apartment):
        with pytest.raises(ValidationError):
            apartment_service.update(apartment.id)

    def test_update_missing_raises(self, apartment_service):
        with pytest.raises(NotFoundError):
            apartment_service.update(999, name="x")

    def test_remove_apartment(self, apartment_service, apartment):
        apartment_service.remove(apartment.id)
        assert apartment_service.list() == []

    def test_remove_missing_raises(self, apartment_service):
        with pytest.raises(NotFoundError):
            apartment_service.remove(999)

    def test_remove_with_bookings_rejected(
        self, apartment_service, booking_service, apartment
    ):
        booking_service.create(apartment.id, "2026-01-10", "2026-01-15")
        with pytest.raises(ValidationError):
            apartment_service.remove(apartment.id)

    def test_empty_name_rejected(self, apartment_service):
        with pytest.raises(ValidationError):
            apartment_service.add("  ", "addr")

    def test_empty_address_rejected(self, apartment_service):
        with pytest.raises(ValidationError):
            apartment_service.add("name", "")


class TestApartmentSearch:
    def test_search_returns_unbooked_apartments(
        self, apartment_service, booking_service, apartment
    ):
        other = apartment_service.add("Other", "3 Pine St")
        booking_service.create(apartment.id, "2026-02-01", "2026-02-05")
        results = apartment_service.search("2026-02-10", "2026-02-12")
        assert {a.id for a in results} == {apartment.id, other.id}

    def test_search_excludes_overlapping(
        self, apartment_service, booking_service, apartment
    ):
        other = apartment_service.add("Other", "3 Pine St")
        booking_service.create(apartment.id, "2026-02-01", "2026-02-05")
        results = apartment_service.search("2026-02-03", "2026-02-10")
        assert [a.id for a in results] == [other.id]

    def test_search_back_to_back_is_available(
        self, apartment_service, booking_service, apartment
    ):
        booking_service.create(apartment.id, "2026-02-01", "2026-02-05")
        results = apartment_service.search("2026-02-05", "2026-02-08")
        assert [a.id for a in results] == [apartment.id]

    def test_search_invalid_range_rejected(self, apartment_service):
        with pytest.raises(ValidationError):
            apartment_service.search("2026-02-05", "2026-02-01")
