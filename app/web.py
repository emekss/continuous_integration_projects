from __future__ import annotations

import html
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from app import db
from app.errors import BookingError
from app.services import ApartmentService, BookingService

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Apartment Booking</title>
<style>
body {{ font-family: sans-serif; margin: 2rem auto; max-width: 48rem; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
th, td {{ border: 1px solid #ccc; padding: 0.3rem 0.6rem; text-align: left; }}
form {{ display: flex; gap: 0.4rem; margin-bottom: 1.5rem; }}
form.inline {{ display: inline; margin: 0; }}
.error {{ color: #b00; }}
</style>
</head>
<body>
<h1>Apartment Booking</h1>
{error}
<h2>Apartments</h2>
<table>
<tr><th>ID</th><th>Name</th><th>Address</th><th></th></tr>
{apartments}
</table>
<form method="post" action="/apartments">
<input name="name" placeholder="Name" required>
<input name="address" placeholder="Address" required>
<button type="submit">Add apartment</button>
</form>
<h2>Bookings</h2>
<table>
<tr><th>ID</th><th>Apartment</th><th>From</th><th>To</th><th></th></tr>
{bookings}
</table>
<form method="post" action="/bookings">
<input name="apartment_id" type="number" min="1" placeholder="Apartment ID" required>
<input name="date_from" type="date" required>
<input name="date_to" type="date" required>
<button type="submit">Create booking</button>
</form>
<h2>Search availability</h2>
<form method="get" action="/search">
<input name="date_from" type="date" required>
<input name="date_to" type="date" required>
<button type="submit">Search</button>
</form>
</body>
</html>
"""

ERROR_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Error</title></head>
<body><h1>Error</h1><p class="error">{message}</p>
<p><a href="/">Back</a></p></body></html>
"""

SEARCH_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Search</title></head>
<body>
<h1>Available apartments {date_from}&ndash;{date_to}</h1>
<table>
<tr><th>ID</th><th>Name</th><th>Address</th></tr>
{rows}
</table>
<p><a href="/">Back</a></p>
</body></html>
"""


def _esc(value: object) -> str:
    return html.escape(str(value))


def _apartment_rows(apartments, actions: bool = True) -> str:
    rows = "".join(
        f"<tr><td>{a.id}</td><td>{_esc(a.name)}</td><td>{_esc(a.address)}</td>"
        + (
            f'<td><form class="inline" method="post"'
            f' action="/apartments/{a.id}/delete">'
            f"<button>Remove</button></form></td>"
            if actions
            else ""
        )
        + "</tr>"
        for a in apartments
    )
    colspan = 4 if actions else 3
    return rows or f'<tr><td colspan="{colspan}">None.</td></tr>'


def _booking_rows(bookings) -> str:
    rows = "".join(
        f"<tr><td>{b.id}</td><td>{b.apartment_id}</td>"
        f"<td>{b.date_from}</td><td>{b.date_to}</td>"
        f'<td><form class="inline" method="post"'
        f' action="/bookings/{b.id}/delete">'
        f"<button>Cancel</button></form></td></tr>"
        for b in bookings
    )
    return rows or '<tr><td colspan="5">None.</td></tr>'


class BookingHandler(BaseHTTPRequestHandler):
    def _html(self, body: str, status: int = 200) -> None:
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect_home(self) -> None:
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def _form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode()
        return {key: vals[0] for key, vals in parse_qs(body).items()}

    def _index(self, conn, error: str = "") -> str:
        err = f'<p class="error">{_esc(error)}</p>' if error else ""
        return PAGE.format(
            error=err,
            apartments=_apartment_rows(ApartmentService(conn).list()),
            bookings=_booking_rows(BookingService(conn).list()),
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        conn = db.connect()
        try:
            if parsed.path == "/":
                self._html(self._index(conn))
            elif parsed.path == "/search":
                query = parse_qs(parsed.query)
                date_from = query.get("date_from", [""])[0]
                date_to = query.get("date_to", [""])[0]
                results = ApartmentService(conn).search(date_from, date_to)
                self._html(
                    SEARCH_PAGE.format(
                        date_from=_esc(date_from),
                        date_to=_esc(date_to),
                        rows=_apartment_rows(results, actions=False),
                    )
                )
            else:
                self.send_error(404)
        except BookingError as e:
            self._html(ERROR_PAGE.format(message=_esc(e)), status=400)
        finally:
            conn.close()

    def do_POST(self) -> None:
        parts = urlparse(self.path).path.strip("/").split("/")
        form = self._form()
        conn = db.connect()
        try:
            if parts == ["apartments"]:
                ApartmentService(conn).add(
                    form.get("name", ""), form.get("address", "")
                )
            elif parts == ["bookings"]:
                BookingService(conn).create(
                    int(form.get("apartment_id", "0")),
                    form.get("date_from", ""),
                    form.get("date_to", ""),
                )
            elif len(parts) == 3 and parts[2] == "delete":
                if parts[0] == "apartments":
                    ApartmentService(conn).remove(int(parts[1]))
                elif parts[0] == "bookings":
                    BookingService(conn).cancel(int(parts[1]))
                else:
                    self.send_error(404)
                    return
            else:
                self.send_error(404)
                return
            self._redirect_home()
        except (BookingError, ValueError) as e:
            self._html(ERROR_PAGE.format(message=_esc(e)), status=400)
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
