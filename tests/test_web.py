import json
import threading
import urllib.error
import urllib.request

import pytest

from app.web import make_server


@pytest.fixture
def base_url(tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKING_DB", str(tmp_path / "booking.db"))
    server = make_server("127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def get_json(url):
    return json.loads(urllib.request.urlopen(url).read())


def post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


def delete(url):
    req = urllib.request.Request(url, method="DELETE")
    return json.loads(urllib.request.urlopen(req).read())


def test_apartment_add_and_list(base_url):
    created = post_json(
        f"{base_url}/api/apartments", {"name": "Loft", "address": "1 St"}
    )
    assert created["id"] == 1
    apartments = get_json(f"{base_url}/api/apartments")
    assert apartments == [{"id": 1, "name": "Loft", "address": "1 St"}]


def test_booking_flow(base_url):
    post_json(f"{base_url}/api/apartments", {"name": "A", "address": "B"})
    booking = post_json(
        f"{base_url}/api/bookings",
        {"apartment_id": 1, "date_from": "2026-06-01", "date_to": "2026-06-05"},
    )
    assert booking["id"] == 1
    assert get_json(f"{base_url}/api/bookings")[0]["date_from"] == "2026-06-01"
    assert delete(f"{base_url}/api/bookings/1") == {"deleted": 1}
    assert get_json(f"{base_url}/api/bookings") == []


def test_invalid_booking_returns_400(base_url):
    post_json(f"{base_url}/api/apartments", {"name": "A", "address": "B"})
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        post_json(
            f"{base_url}/api/bookings",
            {
                "apartment_id": 1,
                "date_from": "2026-06-10",
                "date_to": "2026-06-01",
            },
        )
    assert excinfo.value.code == 400


def test_search_lists_available_apartments(base_url):
    post_json(f"{base_url}/api/apartments", {"name": "A", "address": "B"})
    results = get_json(
        f"{base_url}/api/search?date_from=2026-06-01&date_to=2026-06-05"
    )
    assert results == [{"id": 1, "name": "A", "address": "B"}]


def test_health(base_url):
    assert get_json(f"{base_url}/api/health") == {"status": "ok"}
