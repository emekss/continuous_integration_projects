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

## Web app

The backend is a small stdlib `http.server` JSON API (`python -m app.web`,
port 8000 by default, override with `PORT`). The frontend is a React app in
`frontend/` built with Vite.

API endpoints: `GET/POST /api/apartments`, `DELETE /api/apartments/{id}`,
`GET/POST /api/bookings`, `DELETE /api/bookings/{id}`,
`GET /api/search?date_from&date_to`, `GET /api/health`.

### Frontend development

```sh
cd frontend
npm install
npm run dev
```

Vite serves the UI on http://localhost:5173 and proxies `/api` to the backend
on port 8080 — start both for development (e.g.
`PORT=8080 python -m app.web`, or the Docker container mapped with
`-p 8080:8000`). Override the proxy target with `BOOKING_API_URL`:

```sh
BOOKING_API_URL=http://localhost:8000 npm run dev
```

For a production-style local run, build the frontend and let the Python
server serve it on port 8000:

```sh
cd frontend && npm run build && cd ..
python -m app.web
```

## Docker

```sh
docker build -t apartment-booking .
docker run --rm -p 8000:8000 -v booking-data:/data apartment-booking
```

Then open http://localhost:8000. The image is multi-stage: Node builds the
React frontend, and the Python server serves the built UI plus the API on
`PORT` (default 8000). The SQLite file lives at `/data/booking.db` in the
`booking-data` volume, so records survive when the container exits or the
image is rebuilt. The image runs as UID 10001 and does not include the
repository's local `booking.db`.

The CLI still works inside the image by overriding the default command:

```sh
docker run --rm -v booking-data:/data apartment-booking \
  python booking.py apartment list
```

To use an existing local database instead, bind-mount the file (it must
already exist and be writable by UID 10001):

```sh
docker run --rm -p 8000:8000 \
  --mount type=bind,src="$(pwd)/booking.db",dst=/data/booking.db \
  apartment-booking
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

## GitHub Actions

The workflow in `.github/workflows/ci.yml` runs Ruff, tests, and an 80%
coverage gate on Python 3.11-3.14. It also builds the Docker image and
checks that SQLite data survives between container invocations. Checks run
on pull requests and pushes to `main` (or manually via Actions).

To publish a release, push a version tag after the changes are on `main`:

```sh
git tag v1.0.0
git push origin v1.0.0
```

The tag runs all checks before publishing
`ghcr.io/emekss/continuous_integration_projects:v1.0.0` to GitHub Container
Registry. Publication uses the built-in `GITHUB_TOKEN` with `packages: write`;
no personal access token is needed. GitHub Packages may make the image
private initially; change its visibility in the repository's Packages
settings if you want unauthenticated pulls. This CLI has no server deployment
step: run the published image wherever you want, attaching a persistent
volume at `/data`.
