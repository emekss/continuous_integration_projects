import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from bookingapp import (BookingService, ConflictError, NotFoundError,
                        ValidationError)
from bookingapp.cli import main


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "test.db")
        self.svc = BookingService(self.db)

    def tearDown(self):
        self.tmp.cleanup()


class ApartmentTests(Base):
    def test_add_and_list(self):
        a = self.svc.add_apartment("Sunny", "1 Main St")
        self.assertEqual(a["id"], 1)
        self.assertEqual(self.svc.list_apartments(), [a])

    def test_add_rejects_empty(self):
        with self.assertRaises(ValidationError):
            self.svc.add_apartment("  ", "x")
        with self.assertRaises(ValidationError):
            self.svc.add_apartment("x", "")

    def test_update_partial(self):
        a = self.svc.add_apartment("Old", "Addr")
        u = self.svc.update_apartment(a["id"], name="New")
        self.assertEqual((u["name"], u["address"]), ("New", "Addr"))
        u = self.svc.update_apartment(a["id"], address="Other")
        self.assertEqual((u["name"], u["address"]), ("New", "Other"))

    def test_update_errors(self):
        a = self.svc.add_apartment("A", "B")
        with self.assertRaises(ValidationError):
            self.svc.update_apartment(a["id"])
        with self.assertRaises(NotFoundError):
            self.svc.update_apartment(99, name="x")

    def test_remove(self):
        a = self.svc.add_apartment("A", "B")
        self.svc.remove_apartment(a["id"])
        self.assertEqual(self.svc.list_apartments(), [])
        with self.assertRaises(NotFoundError):
            self.svc.remove_apartment(a["id"])

    def test_remove_blocked_by_active_booking(self):
        a = self.svc.add_apartment("A", "B")
        b = self.svc.create_booking(a["id"], "2026-11-01", "2026-11-05")
        with self.assertRaises(ConflictError):
            self.svc.remove_apartment(a["id"])
        self.svc.cancel_booking(b["id"])
        self.svc.remove_apartment(a["id"])  # now allowed
        self.assertEqual(self.svc.list_bookings(), [])


class BookingTests(Base):
    def setUp(self):
        super().setUp()
        self.apt = self.svc.add_apartment("A", "B")["id"]

    def test_create_and_list(self):
        b = self.svc.create_booking(self.apt, "2026-11-01", "2026-11-05")
        self.assertEqual(b["status"], "active")
        self.assertEqual(self.svc.list_bookings(), [b])

    def test_unknown_apartment(self):
        with self.assertRaises(NotFoundError):
            self.svc.create_booking(42, "2026-11-01", "2026-11-05")

    def test_invalid_dates(self):
        for s, e in [("2026-11-05", "2026-11-01"), ("2026-11-01", "2026-11-01"),
                     ("nope", "2026-11-01"), ("2026-02-30", "2026-03-05")]:
            with self.assertRaises(ValidationError, msg=(s, e)):
                self.svc.create_booking(self.apt, s, e)

    def test_overlap_variants_rejected(self):
        self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")
        for s, e in [("2026-11-10", "2026-11-20"),   # identical
                     ("2026-11-05", "2026-11-11"),   # overlaps start
                     ("2026-11-19", "2026-11-25"),   # overlaps end
                     ("2026-11-12", "2026-11-14"),   # inside
                     ("2026-11-01", "2026-11-30")]:  # contains
            with self.assertRaises(ConflictError, msg=(s, e)):
                self.svc.create_booking(self.apt, s, e)
        self.assertEqual(len(self.svc.list_bookings()), 1)

    def test_back_to_back_allowed(self):
        self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")
        self.svc.create_booking(self.apt, "2026-11-20", "2026-11-25")
        self.svc.create_booking(self.apt, "2026-11-05", "2026-11-10")
        self.assertEqual(len(self.svc.list_bookings()), 3)

    def test_other_apartment_unaffected(self):
        other = self.svc.add_apartment("C", "D")["id"]
        self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")
        self.svc.create_booking(other, "2026-11-10", "2026-11-20")

    def test_change_dates(self):
        b = self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")
        c = self.svc.change_booking(b["id"], end="2026-11-22")
        self.assertEqual((c["start_date"], c["end_date"]), ("2026-11-10", "2026-11-22"))
        c = self.svc.change_booking(b["id"], start="2026-11-11")
        self.assertEqual(c["start_date"], "2026-11-11")

    def test_change_can_overlap_itself_but_not_others(self):
        b1 = self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")
        self.svc.create_booking(self.apt, "2026-11-20", "2026-11-25")
        self.svc.change_booking(b1["id"], start="2026-11-12")  # shrinks, fine
        with self.assertRaises(ConflictError):
            self.svc.change_booking(b1["id"], end="2026-11-21")
        # failed change left data untouched
        self.assertEqual(self.svc.list_bookings()[0]["end_date"], "2026-11-20")

    def test_change_errors(self):
        b = self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")
        with self.assertRaises(ValidationError):
            self.svc.change_booking(b["id"])
        with self.assertRaises(ValidationError):
            self.svc.change_booking(b["id"], end="2026-11-01")
        with self.assertRaises(NotFoundError):
            self.svc.change_booking(99, end="2026-11-01")

    def test_cancel_frees_dates_and_blocks_further_changes(self):
        b = self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")
        self.svc.cancel_booking(b["id"])
        self.assertEqual(self.svc.list_bookings()[0]["status"], "cancelled")
        self.svc.create_booking(self.apt, "2026-11-10", "2026-11-20")  # free again
        with self.assertRaises(ConflictError):
            self.svc.cancel_booking(b["id"])
        with self.assertRaises(ConflictError):
            self.svc.change_booking(b["id"], end="2026-11-21")
        with self.assertRaises(NotFoundError):
            self.svc.cancel_booking(99)


class SearchTests(Base):
    def test_search_excludes_booked(self):
        a1 = self.svc.add_apartment("A1", "x")["id"]
        a2 = self.svc.add_apartment("A2", "y")["id"]
        self.svc.create_booking(a1, "2026-11-10", "2026-11-20")
        ids = lambda s, e: [a["id"] for a in self.svc.search_apartments(s, e)]
        self.assertEqual(ids("2026-11-15", "2026-11-18"), [a2])
        self.assertEqual(ids("2026-11-20", "2026-11-22"), [a1, a2])  # checkout day free
        self.assertEqual(ids("2026-11-01", "2026-11-10"), [a1, a2])
        self.assertEqual(ids("2026-11-01", "2026-11-11"), [a2])

    def test_search_ignores_cancelled(self):
        a = self.svc.add_apartment("A", "x")["id"]
        b = self.svc.create_booking(a, "2026-11-10", "2026-11-20")
        self.svc.cancel_booking(b["id"])
        self.assertEqual(len(self.svc.search_apartments("2026-11-12", "2026-11-14")), 1)

    def test_search_bad_range(self):
        with self.assertRaises(ValidationError):
            self.svc.search_apartments("2026-11-20", "2026-11-10")


class PersistenceTests(Base):
    def test_data_survives_restart(self):
        a = self.svc.add_apartment("A", "x")
        self.svc.create_booking(a["id"], "2026-11-10", "2026-11-20")
        restarted = BookingService(self.db)  # new object == new process
        self.assertEqual(len(restarted.list_apartments()), 1)
        self.assertEqual(len(restarted.list_bookings()), 1)
        with self.assertRaises(ConflictError):  # rule still enforced
            restarted.create_booking(a["id"], "2026-11-15", "2026-11-16")

    def test_env_var_configures_db(self):
        os.environ["BOOKING_DB"] = os.path.join(self.tmp.name, "env.db")
        try:
            BookingService().add_apartment("E", "e")
            self.assertTrue(os.path.exists(os.environ["BOOKING_DB"]))
        finally:
            del os.environ["BOOKING_DB"]


class CliTests(Base):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--db", self.db, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_full_flow(self):
        code, out, _ = self.run_cli("apartment", "add", "--name", "Loft", "--address", "5 Elm")
        self.assertEqual(code, 0)
        self.assertIn("Added apartment 1", out)
        code, out, _ = self.run_cli("booking", "create", "--apartment", "1",
                                    "--from", "2026-11-01", "--to", "2026-11-05")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("apartment", "search", "--from", "2026-11-02", "--to", "2026-11-03")
        self.assertIn("(none)", out)
        code, out, _ = self.run_cli("booking", "change", "1", "--to", "2026-11-03")
        self.assertIn("2026-11-03", out)
        code, out, _ = self.run_cli("booking", "cancel", "1")
        self.assertIn("cancelled", out)
        code, out, _ = self.run_cli("apartment", "search", "--from", "2026-11-02", "--to", "2026-11-03")
        self.assertIn("Loft", out)

    def test_overlap_error_exit_code(self):
        self.run_cli("apartment", "add", "--name", "L", "--address", "A")
        self.run_cli("booking", "create", "--apartment", "1", "--from", "2026-11-01", "--to", "2026-11-05")
        code, out, err = self.run_cli("booking", "create", "--apartment", "1",
                                      "--from", "2026-11-04", "--to", "2026-11-06")
        self.assertEqual(code, 1)
        self.assertIn("already booked", err)

    def test_json_output(self):
        self.run_cli("apartment", "add", "--name", "L", "--address", "A")
        out_io = io.StringIO()
        with redirect_stdout(out_io):
            main(["--db", self.db, "--json", "apartment", "list"])
        self.assertEqual(json.loads(out_io.getvalue())[0]["name"], "L")

    def test_missing_args_exit_2(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            main(["--db", self.db, "booking", "create"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
