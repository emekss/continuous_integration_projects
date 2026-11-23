from __future__ import annotations

from urllib.parse import urlparse

from app import db
from app.api import ApiHandler, run
from app.errors import BookingError


class AuthHandler(ApiHandler):
    """Auth microservice: registration, login, logout and /api/me."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        conn = db.connect()
        try:
            if parsed.path == "/api/health":
                self.ep_health()
            elif parsed.path == "/api/me":
                self.ep_me(conn)
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
            else:
                self._error("Not found", 404)
        except (BookingError, ValueError) as e:
            self._error(e)
        finally:
            conn.close()


def main() -> None:  # pragma: no cover
    run(AuthHandler)


if __name__ == "__main__":
    main()
