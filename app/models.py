from dataclasses import dataclass


@dataclass
class Apartment:
    id: int
    name: str
    address: str


@dataclass
class Booking:
    id: int
    apartment_id: int
    date_from: str
    date_to: str
