class BookingError(Exception):
    """Base class for application errors."""


class NotFoundError(BookingError):
    """Requested entity does not exist."""


class OverlapError(BookingError):
    """Booking conflicts with an existing booking."""


class ValidationError(BookingError):
    """Input failed validation."""
