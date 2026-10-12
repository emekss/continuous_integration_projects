# Apartment Booking (command-line backend)

A backend with no GUI. Everything runs from the terminal. Data is stored in a
SQLite file, so it is still there after you restart.

- Python 3.9+ (tested on 3.12). **No packages to install** (standard library only).

## Project layout

    booking.py              entry point:  python booking.py COMMAND [OPTIONS]
    bookingapp/service.py   the API (class BookingService) + SQLite storage
    bookingapp/cli.py       command-line parsing / printing
    tests/test_booking.py   25 automated tests
    requirements.txt        (no third-party dependencies)

## 1. Start the application

    cd apartment-booking
    python booking.py --help

There is no server to start; each command runs, saves, and exits.
The database file `booking.db` is created automatically in the current folder.

### Configuration

| Setting | How | Default |
|---|---|---|
| Database file | `--db PATH` option, or `BOOKING_DB` environment variable | `./booking.db` |
| Output as JSON | `--json` option (put it before the command) | text table |

    export BOOKING_DB=/path/to/my.db        # Windows: set BOOKING_DB=C:\path\my.db
    python booking.py --db other.db apartment list

## 2. Try the commands (a full walkthrough)

Dates are `YYYY-MM-DD`. `--from` is check-in, `--to` is check-out (the
check-out day is free for the next guest).

    # Apartments: add, view, update, remove
    python booking.py apartment add --name "Sunny Loft" --address "1 Main St"
    python booking.py apartment add --name "Garden Flat" --address "9 Oak Ave"
    python booking.py apartment list
    python booking.py apartment update 2 --address "11 Oak Ave"
    python booking.py apartment remove 2

    # Bookings: create, view, change, cancel
    python booking.py booking create --apartment 1 --from 2026-11-01 --to 2026-11-05
    python booking.py booking list
    python booking.py booking change 1 --to 2026-11-07
    python booking.py booking cancel 1

    # Search apartments free during a date range
    python booking.py apartment search --from 2026-11-02 --to 2026-11-04

    # Overlap prevention (this one fails with exit code 1)
    python booking.py booking create --apartment 1 --from 2026-11-01 --to 2026-11-05
    python booking.py booking create --apartment 1 --from 2026-11-04 --to 2026-11-08
    # Error: Apartment is already booked from 2026-11-01 to 2026-11-05 (booking 1)

    # Persistence: run `apartment list` again in a new terminal - data is still there.

## Command reference

    apartment list
    apartment add --name NAME --address ADDRESS
    apartment update ID [--name NAME] [--address ADDRESS]
    apartment remove ID
    apartment search --from DATE --to DATE
    booking list
    booking create --apartment ID --from DATE --to DATE
    booking change ID [--from DATE] [--to DATE]
    booking cancel ID

Exit codes: `0` success, `1` business error (message on stderr), `2` bad usage.

## Business rules

- Bookings of the same apartment may not overlap (`a.from < b.to and b.from < a.to`).
  Back-to-back stays (check-out day = next check-in day) are allowed.
- Changing a booking is checked against *other* bookings only, and is all-or-nothing.
- Cancelling keeps the record (status `cancelled`) but frees the dates; cancelled
  bookings can't be changed or re-cancelled.
- An apartment with active bookings can't be removed (cancel them first).
- The overlap check and insert happen in one SQLite write transaction
  (`BEGIN IMMEDIATE`), so two terminals can't double-book at once.

## 3. Using it as a Python API (no CLI)

    from bookingapp import BookingService, ConflictError

    svc = BookingService("booking.db")
    apt = svc.add_apartment("Sunny Loft", "1 Main St")      # -> dict
    svc.create_booking(apt["id"], "2026-11-01", "2026-11-05")
    svc.search_apartments("2026-11-02", "2026-11-04")        # -> []

| Method | Purpose |
|---|---|
| `add_apartment(name, address)` | create |
| `list_apartments()` | view all |
| `update_apartment(id, name=None, address=None)` | update |
| `remove_apartment(id)` | delete |
| `search_apartments(start, end)` | free apartments in range |
| `create_booking(apartment_id, start, end)` | create |
| `list_bookings(include_cancelled=True)` | view |
| `change_booking(id, start=None, end=None)` | change dates |
| `cancel_booking(id)` | cancel |

Errors (all subclass `BookingError`): `ValidationError` (bad input),
`NotFoundError` (unknown id), `ConflictError` (overlap / rule violation).

## 4. Run the tests

    python -m unittest discover -v        # or: pytest

They use a temporary database, so your real `booking.db` is never touched.
Covered: add/update/remove, create/change/cancel, every overlap shape
(identical, partial, contained, containing), back-to-back stays, search,
persistence across restarts, the CLI flow, exit codes, and JSON output.
