import pytest

from app.cli import main


@pytest.fixture
def cli(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("BOOKING_DB", str(db_file))

    def run(*argv):
        return main(list(argv))

    return run


def test_apartment_add_and_list(cli, capsys):
    assert (
        cli("apartment", "add", "--name", "Loft", "--address", "1 St")
        == 0
    )
    capsys.readouterr()
    assert cli("apartment", "list") == 0
    out = capsys.readouterr().out
    assert "Loft" in out and "1 St" in out


def test_apartment_add_reuses_available_id(cli, capsys):
    for name in ("First", "Second", "Third"):
        assert cli("apartment", "add", "--name", name, "--address", "x") == 0
    assert cli("apartment", "remove", "2") == 0
    capsys.readouterr()

    assert cli("apartment", "add", "--name", "New", "--address", "x") == 0
    assert capsys.readouterr().out.startswith("2\tNew\t")
    assert cli("apartment", "list") == 0
    assert [line.split("\t")[0] for line in capsys.readouterr().out.splitlines()] == [
        "1", "2", "3"
    ]


def test_booking_flow(cli, capsys):
    cli("apartment", "add", "--name", "A", "--address", "x")
    assert (
        cli(
            "booking", "create", "1",
            "--from", "2026-01-01", "--to", "2026-01-05",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "2026-01-01..2026-01-05" in out

    assert (
        cli(
            "booking", "create", "1",
            "--from", "2026-01-03", "--to", "2026-01-06",
        )
        == 1
    )
    err = capsys.readouterr().err
    assert "already booked" in err

    assert (
        cli("booking", "change", "1", "--to", "2026-01-07") == 0
    )
    assert cli("booking", "cancel", "1") == 0


def test_search_command(cli, capsys):
    cli("apartment", "add", "--name", "Free", "--address", "x")
    cli("apartment", "add", "--name", "Busy", "--address", "y")
    cli(
        "booking", "create", "2",
        "--from", "2026-01-01", "--to", "2026-01-10",
    )
    capsys.readouterr()
    assert (
        cli(
            "apartment", "search",
            "--from", "2026-01-05", "--to", "2026-01-08",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Free" in out
    assert "Busy" not in out


def test_errors_exit_nonzero(cli, capsys):
    assert cli("apartment", "remove", "42") == 1
    assert "not found" in capsys.readouterr().err.lower()

    cli("apartment", "add", "--name", "A", "--address", "x")
    assert (
        cli(
            "booking", "create", "1",
            "--from", "2026-01-10", "--to", "2026-01-01",
        )
        == 1
    )
    assert "error:" in capsys.readouterr().err


def test_update_and_remove(cli, capsys):
    cli("apartment", "add", "--name", "Old", "--address", "x")
    assert cli("apartment", "update", "1", "--name", "New") == 0
    assert "New" in capsys.readouterr().out
    assert cli("apartment", "remove", "1") == 0
    assert "removed" in capsys.readouterr().out
