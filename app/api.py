from __future__ import annotations

import json
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import auth, db, notify
from app.errors import BookingError
from app.services import ApartmentService, BookingService

DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
SESSION_COOKIE = "booking_session"


def apartment_json(a) -> dict:
    return {"id": a.id, "name": a.name, "address": a.address}


def booking_json(b) -> dict:
    return {
        "id": b.id,
        "apartment_id": b.apartment_id,
        "date_from": b.date_from,
        "date_to": b.date_to,
    }


def make_server(host: str, port: int, handler) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), handler)


def run(handler, default_port: int = 8000) -> None:  # pragma: no cover
    port = int(os.environ.get("PORT", str(default_port)))
    server = make_server("0.0.0.0", port, handler)
    print(f"Listening on http://0.0.0.0:{port}")
    server.serve_forever()


class ApiHandler(BaseHTTPRequestHandler):
    # ---- request/response helpers ----

    def _json(self, data, status: int = 200, headers=None) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
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
        self.send_header(
            "Content-Type", guess_type(str(target))[0] or "text/html"
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- auth helpers ----

    def _token(self) -> str:
        cookie = SimpleCookie(self.headers.get("Cookie"))
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else ""

    def _user(self, conn) -> dict | None:
        token = self._token()
        return auth.user_for_token(conn, token) if token else None

    def _session_headers(self, token: str) -> dict:
        return {
            "Set-Cookie": (
                f"{SESSION_COOKIE}={token}; HttpOnly; Path=/; SameSite=Lax"
            )
        }

    def _require_user(self, conn) -> dict | None:
        user = self._user(conn)
        if user is None:
            self._error("Authentication required", 401)
        return user

    # ---- endpoints (shared by the monolith and the split services) ----

    def ep_health(self) -> None:
        self._json({"status": "ok"})

    def ep_me(self, conn) -> None:
        user = self._user(conn)
        if user is None:
            self._error("Not authenticated", 401)
        else:
            self._json(user)

    def ep_auth(self, conn, path: str, data: dict) -> None:
        if path == "/api/auth/register":
            user_id = auth.create_user(
                conn, data.get("email", ""), data.get("password", "")
            )
            token = auth.create_session(conn, user_id)
            self._json(
                {
                    "id": user_id,
                    "email": data.get("email", "").strip().lower(),
                },
                201,
                self._session_headers(token),
            )
        elif path == "/api/auth/login":
            user_id = auth.authenticate(
                conn, data.get("email", ""), data.get("password", "")
            )
            if user_id is None:
                self._error("Invalid email or password", 401)
                return
            token = auth.create_session(conn, user_id)
            self._json(
                auth.user_for_token(conn, token),
                200,
                self._session_headers(token),
            )
        elif path == "/api/auth/logout":
            token = self._token()
            if token:
                auth.delete_session(conn, token)
            self._json(
                {"logged_out": True},
                headers={
                    "Set-Cookie": (
                        f"{SESSION_COOKIE}=; HttpOnly; Path=/; Max-Age=0"
                    )
                },
            )
        else:
            self._error("Not found", 404)

    def ep_apartments(self, conn) -> None:
        apartments = ApartmentService(conn).list()
        self._json([apartment_json(a) for a in apartments])

    def ep_bookings(self, conn) -> None:
        bookings = BookingService(conn).list()
        self._json([booking_json(b) for b in bookings])

    def ep_search(self, conn, query) -> None:
        results = ApartmentService(conn).search(
            query.get("date_from", [""])[0],
            query.get("date_to", [""])[0],
        )
        self._json([apartment_json(a) for a in results])

    def ep_add_apartment(self, conn, data: dict, user: dict) -> None:
        apt = ApartmentService(conn).add(
            data.get("name", ""), data.get("address", "")
        )
        notify.publish(
            {
                "event": "apartment_added",
                "user": user.get("email"),
                "apartment": apartment_json(apt),
            }
        )
        self._json(apartment_json(apt), 201)

    def ep_create_booking(self, conn, data: dict) -> None:
        booking = BookingService(conn).create(
            int(data.get("apartment_id", 0)),
            data.get("date_from", ""),
            data.get("date_to", ""),
        )
        self._json(booking_json(booking), 201)

    def ep_remove_apartment(self, conn, apartment_id: int, user: dict) -> None:
        apartments = ApartmentService(conn)
        apt = apartments.get(apartment_id)
        apartments.remove(apartment_id)
        notify.publish(
            {
                "event": "apartment_deleted",
                "user": user.get("email"),
                "apartment": apartment_json(apt),
            }
        )
        self._json({"deleted": apartment_id})

    def ep_cancel_booking(self, conn, booking_id: int) -> None:
        BookingService(conn).cancel(booking_id)
        self._json({"deleted": booking_id})
