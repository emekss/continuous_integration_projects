import pytest

from app.db import connect
from app.services import ApartmentService, BookingService


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


@pytest.fixture
def apartment_service(conn):
    return ApartmentService(conn)


@pytest.fixture
def booking_service(conn):
    return BookingService(conn)


@pytest.fixture
def apartment(apartment_service):
    return apartment_service.add("Sunny Studio", "1 Main St")
