import json
import threading
import urllib.error
import urllib.request

import pytest

from app import db, projection
from app.auth_service import AuthHandler
from app.booking_service import BookingApiHandler
from app.web import WebHandler, make_server


def start_server(handler, tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKING_DB", str(tmp_path / "booking.db"))
    server = make_server("127.0.0.1", 0, handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def base_url(tmp_path, monkeypatch):
    server = start_server(WebHandler, tmp_path, monkeypatch)
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture
def services(tmp_path, monkeypatch):
    db_file = tmp_path / "booking.db"
    monkeypatch.setenv("BOOKING_DB", str(db_file))
    auth = make_server("127.0.0.1", 0, AuthHandler)
    booking = make_server("127.0.0.1", 0, BookingApiHandler)
    threading.Thread(target=auth.serve_forever, daemon=True).start()
    threading.Thread(target=booking.serve_forever, daemon=True).start()
    yield (
        f"http://127.0.0.1:{auth.server_address[1]}",
        f"http://127.0.0.1:{booking.server_address[1]}",
    )
    auth.shutdown()
    booking.shutdown()


def test_session_works_across_split_services(services):
    auth_url, booking_url = services
    resp = request_json(
        f"{auth_url}/api/auth/register",
        {"email": "svc@example.com", "password": "password123"},
    )
    session = resp.headers["Set-Cookie"].split(";")[0]
    # without replication the booking service cannot resolve the session
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        get_json(f"{booking_url}/api/apartments", session)
    assert excinfo.value.code == 401
    # simulate the consumer applying the user_registered event
    user = json.loads(resp.read())
    conn = db.connect()
    projection.upsert_user(conn, user["id"], user["email"])
    conn.close()
    assert get_json(f"{booking_url}/api/apartments", session) == []


def request_json(url, payload=None, method=None, cookie=None):
    headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method or ("POST" if data is not None else "GET"),
    )
    return urllib.request.urlopen(req)


@pytest.fixture
def cookie(base_url):
    resp = request_json(
        f"{base_url}/api/auth/register",
        {"email": "owner@example.com", "password": "password123"},
    )
    return resp.headers["Set-Cookie"].split(";")[0]


def get_json(url, cookie=None):
    return json.loads(request_json(url, cookie=cookie).read())


def post_json(url, payload, cookie=None):
    return json.loads(request_json(url, payload, cookie=cookie).read())


def delete(url, cookie=None):
    return json.loads(
        request_json(url, method="DELETE", cookie=cookie).read()
    )


def test_unauthenticated_requests_are_rejected(base_url):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        request_json(f"{base_url}/api/apartments")
    assert excinfo.value.code == 401


def test_register_login_logout(base_url, cookie):
    assert get_json(f"{base_url}/api/me", cookie)["email"] == (
        "owner@example.com"
    )
    post_json(f"{base_url}/api/auth/logout", {}, cookie)
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        request_json(f"{base_url}/api/me", cookie=cookie)
    assert excinfo.value.code == 401
    user = post_json(
        f"{base_url}/api/auth/login",
        {"email": "owner@example.com", "password": "password123"},
    )
    assert user["email"] == "owner@example.com"


def test_login_with_wrong_password_returns_401(base_url, cookie):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        post_json(
            f"{base_url}/api/auth/login",
            {"email": "owner@example.com", "password": "wrong-password"},
        )
    assert excinfo.value.code == 401


def test_apartment_add_and_list(base_url, cookie):
    created = post_json(
        f"{base_url}/api/apartments",
        {"name": "Loft", "address": "1 St"},
        cookie,
    )
    assert created["id"] == 1
    apartments = get_json(f"{base_url}/api/apartments", cookie)
    assert apartments == [
        {"id": 1, "name": "Loft", "address": "1 St", "owner": None}
    ]


def test_booking_flow(base_url, cookie):
    post_json(f"{base_url}/api/apartments", {"name": "A", "address": "B"}, cookie)
    booking = post_json(
        f"{base_url}/api/bookings",
        {"apartment_id": 1, "date_from": "2026-06-01", "date_to": "2026-06-05"},
        cookie,
    )
    assert booking["id"] == 1
    bookings = get_json(f"{base_url}/api/bookings", cookie)
    assert bookings[0]["date_from"] == "2026-06-01"
    assert delete(f"{base_url}/api/bookings/1", cookie) == {"deleted": 1}
    assert get_json(f"{base_url}/api/bookings", cookie) == []


def test_invalid_booking_returns_400(base_url, cookie):
    post_json(f"{base_url}/api/apartments", {"name": "A", "address": "B"}, cookie)
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        post_json(
            f"{base_url}/api/bookings",
            {
                "apartment_id": 1,
                "date_from": "2026-06-10",
                "date_to": "2026-06-01",
            },
            cookie,
        )
    assert excinfo.value.code == 400


def test_search_lists_available_apartments(base_url, cookie):
    post_json(f"{base_url}/api/apartments", {"name": "A", "address": "B"}, cookie)
    results = get_json(
        f"{base_url}/api/search?date_from=2026-06-01&date_to=2026-06-05",
        cookie,
    )
    assert results == [
        {"id": 1, "name": "A", "address": "B", "owner": None}
    ]


def test_health(base_url):
    assert get_json(f"{base_url}/api/health") == {"status": "ok"}
