from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app import db
from app.api import ApiHandler, make_server, run
from app.errors import BookingError

PUBLIC_PATHS = {"/api/health", "/api/auth/register", "/api/auth/login"}


class WebHandler(ApiHandler):
    """Monolith handler: serves the API and the built frontend."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._serve_static(parsed.path)
            return
        conn = db.connect()
        try:
            if parsed.path == "/api/health":
                self.ep_health()
            elif parsed.path == "/api/me":
                self.ep_me(conn)
            elif parsed.path in ("/api/auth/register", "/api/auth/login"):
                self._error("Not found", 404)
            elif self._require_user(conn) is None:
                return
            elif parsed.path == "/api/apartments":
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
            if parsed.path.startswith("/api/auth/"):
                self.ep_auth(conn, parsed.path, data)
                return
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
    run(WebHandler)


if __name__ == "__main__":
    main()
