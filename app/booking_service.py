from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app import db
from app.api import ApiHandler, run
from app.errors import BookingError


class BookingApiHandler(ApiHandler):
    """Booking microservice: apartments, bookings and availability.

    Validates sessions by reading the shared SQLite `session` table, so
    cookies issued by the auth service work here without a service call.
    """

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        conn = db.connect()
        try:
            if parsed.path == "/api/health":
                self.ep_health()
                return
            if self._require_user(conn) is None:
                return
            if parsed.path == "/api/apartments":
                self.ep_apartments(conn)
            elif parsed.path == "/api/bookings":
                self.ep_bookings(conn)
            elif parsed.path == "/api/search":
                self.ep_search(conn, parse_qs(parsed.query))
            else:
                self._error("Not found", 404)
        except BookingError as e:
            self._error(e)
        finally:
            conn.close()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        data = self._body()
        conn = db.connect()
        try:
            user = self._require_user(conn)
            if user is None:
                return
            if parsed.path == "/api/apartments":
                self.ep_add_apartment(conn, data, user)
            elif parsed.path == "/api/bookings":
                self.ep_create_booking(conn, data)
            else:
                self._error("Not found", 404)
        except (BookingError, ValueError) as e:
            self._error(e)
        finally:
            conn.close()

    def do_DELETE(self) -> None:
        parts = urlparse(self.path).path.strip("/").split("/")
        conn = db.connect()
        try:
            user = self._require_user(conn)
            if user is None:
                return
            if len(parts) != 3 or parts[0] != "api":
                self._error("Not found", 404)
                return
            if parts[1] == "apartments":
                self.ep_remove_apartment(conn, int(parts[2]), user)
            elif parts[1] == "bookings":
                self.ep_cancel_booking(conn, int(parts[2]))
            else:
                self._error("Not found", 404)
        except (BookingError, ValueError) as e:
            self._error(e)
        finally:
            conn.close()


def main() -> None:  # pragma: no cover
    run(BookingApiHandler)


if __name__ == "__main__":
    main()
