# Apartment Booking

A small CLI for managing apartment bookings, backed by SQLite. Built to
demonstrate a three-layer architecture and a CI pipeline with lint, tests,
and coverage.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.11+ required. No other runtime dependencies — only the standard
library (`argparse`, `sqlite3`).

## Usage

```sh
python booking.py apartment list
python booking.py apartment add --name "Sunny Studio" --address "1 Main St"
python booking.py apartment update 1 --name "New Name"
python booking.py apartment remove 1
python booking.py apartment search --from 2026-05-01 --to 2026-05-10

python booking.py booking list
python booking.py booking create 1 --from 2026-05-01 --to 2026-05-10
python booking.py booking change 1 --to 2026-05-12
python booking.py booking cancel 1
```

Dates are ISO `YYYY-MM-DD`. On success commands print to stdout and exit 0;
on errors a message goes to stderr and the exit code is 1.

The database is `booking.db` in the current directory. Set `BOOKING_DB` to
use a different file (or `:memory:`):

```sh
BOOKING_DB=/tmp/test.db python booking.py apartment list
```

## Docker

This is a CLI, not a web server: the image takes the same arguments as
`booking.py` and does not expose a port. It needs no runtime packages beyond
Python's standard library.

```sh
docker build -t apartment-booking .
docker run --rm -v booking-data:/data apartment-booking apartment add \
  --name "Sunny Studio" --address "1 Main St"
docker run --rm -v booking-data:/data apartment-booking apartment list
docker run --rm -v booking-data:/data apartment-booking booking create 1 \
  --from 2026-05-01 --to 2026-05-10
```

Use the same `booking-data` named volume for every invocation. The SQLite file
is stored at `/data/booking.db` in that volume, so records survive when a
container exits or the image is rebuilt. The image runs as UID 10001 and
does not include the repository's local `booking.db`.

To use an existing local database instead, bind-mount the file (it must
already exist and be writable by UID 10001):

```sh
docker run --rm --mount type=bind,src="$(pwd)/booking.db",dst=/data/booking.db \
  apartment-booking apartment list
```

## Architecture

Three layers, so business logic is testable without the CLI or a real
database file:

```
CLI (booking.py, app/cli.py)   args parsing, output, exit codes
      |
Service layer (app/services.py)  validation, overlap rules
      |
Repository layer (app/repository.py)  SQL only
      |
SQLite (app/db.py, booking.db)
```

## Design decisions

- **Dates stored as ISO text** — they sort and compare correctly as strings.
- **Half-open ranges `[from, to)`** — a guest can check in on the day
  another checks out. Two bookings overlap when
  `new_from < existing_to AND new_to > existing_from`.
- **Change excludes itself** — the overlap query takes
  `exclude_booking_id` so a booking can be "changed" onto its own dates.
- **Remove policy: reject** — an apartment with bookings cannot be removed;
  bookings must be cancelled first (chosen over cascade-delete as the
  safer, more explicit option).
- **Apartment IDs** — new apartments take the lowest available positive ID,
  filling gaps left by removals. Existing apartments are never renumbered,
  so bookings still refer to the same apartment. A removed apartment's ID
  may later refer to a different apartment; do not treat IDs as permanent
  historical references.
- **Validation** — `from < to`, strict ISO dates, referenced apartments
  must exist. Empty names/addresses are rejected.

## Development

```sh
pytest --cov=app --cov-fail-under=80
ruff check .
```

CI (`.github/workflows/ci.yml`) runs lint, tests, and coverage on every
push and pull request.
