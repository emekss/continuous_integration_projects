import argparse
import sys

from app import db
from app.errors import BookingError
from app.services import ApartmentService, BookingService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="booking.py")
    sub = parser.add_subparsers(dest="entity", required=True)

    apt = sub.add_parser("apartment").add_subparsers(
        dest="action", required=True
    )
    apt.add_parser("list")
    a = apt.add_parser("add")
    a.add_argument("--name", required=True)
    a.add_argument("--address", required=True)
    u = apt.add_parser("update")
    u.add_argument("id", type=int)
    u.add_argument("--name")
    u.add_argument("--address")
    r = apt.add_parser("remove")
    r.add_argument("id", type=int)
    s = apt.add_parser("search")
    s.add_argument("--from", dest="date_from", required=True)
    s.add_argument("--to", dest="date_to", required=True)

    bk = sub.add_parser("booking").add_subparsers(
        dest="action", required=True
    )
    bk.add_parser("list")
    c = bk.add_parser("create")
    c.add_argument("apartment_id", type=int)
    c.add_argument("--from", dest="date_from", required=True)
    c.add_argument("--to", dest="date_to", required=True)
    ch = bk.add_parser("change")
    ch.add_argument("id", type=int)
    ch.add_argument("--from", dest="date_from")
    ch.add_argument("--to", dest="date_to")
    ca = bk.add_parser("cancel")
    ca.add_argument("id", type=int)

    return parser


def _print_apartment(apt) -> None:
    print(f"{apt.id}\t{apt.name}\t{apt.address}")


def _print_booking(b) -> None:
    print(f"{b.id}\tapartment={b.apartment_id}\t{b.date_from}..{b.date_to}")


def run(args: argparse.Namespace, conn) -> int:
    apt_service = ApartmentService(conn)
    bk_service = BookingService(conn)

    if args.entity == "apartment":
        if args.action == "list":
            for apt in apt_service.list():
                _print_apartment(apt)
        elif args.action == "add":
            _print_apartment(apt_service.add(args.name, args.address))
        elif args.action == "update":
            _print_apartment(
                apt_service.update(args.id, args.name, args.address)
            )
        elif args.action == "remove":
            apt_service.remove(args.id)
            print(f"Apartment {args.id} removed.")
        elif args.action == "search":
            for apt in apt_service.search(args.date_from, args.date_to):
                _print_apartment(apt)
    else:  # booking
        if args.action == "list":
            for b in bk_service.list():
                _print_booking(b)
        elif args.action == "create":
            _print_booking(
                bk_service.create(
                    args.apartment_id, args.date_from, args.date_to
                )
            )
        elif args.action == "change":
            _print_booking(
                bk_service.change(args.id, args.date_from, args.date_to)
            )
        elif args.action == "cancel":
            bk_service.cancel(args.id)
            print(f"Booking {args.id} cancelled.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    conn = db.connect()
    try:
        return run(args, conn)
    except BookingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
