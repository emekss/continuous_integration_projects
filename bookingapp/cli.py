"""Command-line interface: thin wrapper over BookingService."""
import argparse
import json
import sys

from .service import BookingService, BookingError, DEFAULT_DB


def build_parser():
    p = argparse.ArgumentParser(
        prog="booking.py",
        description="Apartment booking backend. Dates use YYYY-MM-DD; "
                    "'--to' is the check-out day (exclusive).")
    p.add_argument("--db", help=f"SQLite file (default: $BOOKING_DB or ./{DEFAULT_DB})")
    p.add_argument("--json", action="store_true", help="print results as JSON")
    groups = p.add_subparsers(dest="group", metavar="COMMAND", required=True)

    # apartment ...
    apt = groups.add_parser("apartment", help="manage apartments") \
                .add_subparsers(dest="action", metavar="ACTION", required=True)
    apt.add_parser("list", help="list all apartments")
    a = apt.add_parser("add", help="add an apartment")
    a.add_argument("--name", required=True)
    a.add_argument("--address", required=True)
    a = apt.add_parser("update", help="update an apartment")
    a.add_argument("id", type=int)
    a.add_argument("--name")
    a.add_argument("--address")
    a = apt.add_parser("remove", help="remove an apartment")
    a.add_argument("id", type=int)
    a = apt.add_parser("search", help="apartments free during a date range")
    a.add_argument("--from", dest="start", required=True, metavar="DATE")
    a.add_argument("--to", dest="end", required=True, metavar="DATE")

    # booking ...
    bk = groups.add_parser("booking", help="manage bookings") \
               .add_subparsers(dest="action", metavar="ACTION", required=True)
    bk.add_parser("list", help="list all bookings")
    b = bk.add_parser("create", help="create a booking")
    b.add_argument("--apartment", type=int, required=True, metavar="ID")
    b.add_argument("--from", dest="start", required=True, metavar="DATE")
    b.add_argument("--to", dest="end", required=True, metavar="DATE")
    b = bk.add_parser("change", help="change booking dates")
    b.add_argument("id", type=int)
    b.add_argument("--from", dest="start", metavar="DATE")
    b.add_argument("--to", dest="end", metavar="DATE")
    b = bk.add_parser("cancel", help="cancel a booking")
    b.add_argument("id", type=int)
    return p


def _table(rows, columns):
    if not rows:
        return "(none)"
    widths = [max(len(h), *(len(str(r[k])) for r in rows)) for h, k in columns]
    line = lambda vals: "  ".join(str(v).ljust(w) for v, w in zip(vals, widths)).rstrip()
    out = [line([h for h, _ in columns]), line(["-" * w for w in widths])]
    out += [line([r[k] for _, k in columns]) for r in rows]
    return "\n".join(out)


APT_COLS = [("ID", "id"), ("NAME", "name"), ("ADDRESS", "address")]
BK_COLS = [("ID", "id"), ("APARTMENT", "apartment_id"), ("FROM", "start_date"),
           ("TO", "end_date"), ("STATUS", "status")]


def run(args, svc):
    """Dispatch a parsed command. Returns (data, columns, message)."""
    g, act = args.group, args.action
    if g == "apartment":
        if act == "list":
            return svc.list_apartments(), APT_COLS, None
        if act == "add":
            r = svc.add_apartment(args.name, args.address)
            return r, APT_COLS, f"Added apartment {r['id']}"
        if act == "update":
            r = svc.update_apartment(args.id, args.name, args.address)
            return r, APT_COLS, f"Updated apartment {r['id']}"
        if act == "remove":
            r = svc.remove_apartment(args.id)
            return r, APT_COLS, f"Removed apartment {r['id']}"
        if act == "search":
            return svc.search_apartments(args.start, args.end), APT_COLS, None
    else:
        if act == "list":
            return svc.list_bookings(), BK_COLS, None
        if act == "create":
            r = svc.create_booking(args.apartment, args.start, args.end)
            return r, BK_COLS, f"Created booking {r['id']}"
        if act == "change":
            r = svc.change_booking(args.id, args.start, args.end)
            return r, BK_COLS, f"Changed booking {r['id']}"
        if act == "cancel":
            r = svc.cancel_booking(args.id)
            return r, BK_COLS, f"Cancelled booking {r['id']}"


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        svc = BookingService(args.db)
        data, cols, msg = run(args, svc)
    except BookingError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        if msg:
            print(msg)
        print(_table(data if isinstance(data, list) else [data], cols))
    return 0
