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


def get(url: str) -> str:
    return urllib.request.urlopen(url).read().decode()


def test_index_shows_added_apartment(base_url):
    urllib.request.urlopen(f"{base_url}/apartments", data=b"name=Loft&address=1+St")
    assert "Loft" in get(base_url)


def test_booking_flow(base_url):
    urllib.request.urlopen(f"{base_url}/apartments", data=b"name=A&address=B")
    urllib.request.urlopen(
        f"{base_url}/bookings",
        data=b"apartment_id=1&date_from=2026-06-01&date_to=2026-06-05",
    )
    assert "2026-06-01" in get(base_url)


def test_invalid_booking_returns_400(base_url):
    urllib.request.urlopen(f"{base_url}/apartments", data=b"name=A&address=B")
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(
            f"{base_url}/bookings",
            data=b"apartment_id=1&date_from=2026-06-10&date_to=2026-06-01",
        )
    assert excinfo.value.code == 400


def test_search_lists_available_apartments(base_url):
    urllib.request.urlopen(f"{base_url}/apartments", data=b"name=A&address=B")
    page = get(f"{base_url}/search?date_from=2026-06-01&date_to=2026-06-05")
    assert "<td>A</td>" in page
