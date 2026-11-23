from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import db
from app.errors import BookingError
from app.services import ApartmentService, BookingService

DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _apartment_json(a) -> dict:
    return {"id": a.id, "name": a.name, "address": a.address}


def _booking_json(b) -> dict:
    return {
        "id": b.id,
        "apartment_id": b.apartment_id,
        "date_from": b.date_from,
        "date_to": b.date_to,
    }


class BookingHandler(BaseHTTPRequestHandler):
    def _json(self, data, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message, status: int = 400) -> None:
        self._json({"error": str(message)}, status)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode()
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return data if isinstance(data, dict) else {}

    def _serve_static(self, path: str) -> None:
        target = (DIST_DIR / path.lstrip("/")).resolve()
        if not target.is_relative_to(DIST_DIR):
            self.send_error(404)
            return
        if not target.is_file():
            target = DIST_DIR / "index.html"
        if not target.is_file():
            self._error("Frontend not built", 404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", guess_type(str(target))[0] or "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._serve_static(parsed.path)
            return
        conn = db.connect()
        try:
            apartments = ApartmentService(conn)
            if parsed.path == "/api/health":
                self._json({"status": "ok"})
            elif parsed.path == "/api/apartments":
                self._json([_apartment_json(a) for a in apartments.list()])
            elif parsed.path == "/api/bookings":
                self._json([_booking_json(b) for b in BookingService(conn).list()])
            elif parsed.path == "/api/search":
                query = parse_qs(parsed.query)
                results = apartments.search(
                    query.get("date_from", [""])[0],
                    query.get("date_to", [""])[0],
                )
                self._json([_apartment_json(a) for a in results])
            else:
                self._error("Not found", 404)
        except BookingError as e:
            self._error(e)
        finally:
            conn.close()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        data = self._body()
        conn = db.connect()
        try:
            if path == "/api/apartments":
                apt = ApartmentService(conn).add(
                    data.get("name", ""), data.get("address", "")
                )
                self._json(_apartment_json(apt), 201)
            elif path == "/api/bookings":
                booking = BookingService(conn).create(
                    int(data.get("apartment_id", 0)),
                    data.get("date_from", ""),
                    data.get("date_to", ""),
                )
                self._json(_booking_json(booking), 201)
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
            if len(parts) != 3 or parts[0] != "api":
                self._error("Not found", 404)
                return
            if parts[1] == "apartments":
                ApartmentService(conn).remove(int(parts[2]))
            elif parts[1] == "bookings":
                BookingService(conn).cancel(int(parts[2]))
            else:
                self._error("Not found", 404)
                return
            self._json({"deleted": int(parts[2])})
        except (BookingError, ValueError) as e:
            self._error(e)
        finally:
            conn.close()


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), BookingHandler)


def main() -> None:  # pragma: no cover
    port = int(os.environ.get("PORT", "8000"))
    server = make_server("0.0.0.0", port)
    print(f"Apartment Booking listening on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
