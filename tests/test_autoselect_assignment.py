"""Selection uses live node population but remains stable during a session."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from database.db_autoselect import choose_autoselect_country


@contextmanager
def _db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def test_new_arrivals_split_even_when_panel_counts_have_not_refreshed():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "assignments.db"
        now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
        with patch("database.db_autoselect.get_db", side_effect=lambda: _db(path)):
            chosen = [
                choose_autoselect_country(key_id, {"de", "ee"}, {"de": 3, "ee": 3}, None, now=now)
                for key_id in range(1, 5)
            ]
        assert chosen.count("de") == 2
        assert chosen.count("ee") == 2


def test_active_viewer_stays_put_then_can_be_rebalanced_after_offline_gap():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "assignments.db"
        now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
        with patch("database.db_autoselect.get_db", side_effect=lambda: _db(path)):
            first = choose_autoselect_country(9, {"de", "ee"}, {"de": 2, "ee": 8}, None, now=now)
            active = choose_autoselect_country(
                9, {"de", "ee"}, {"de": 12, "ee": 1},
                (now + timedelta(hours=2)).isoformat(), now=now + timedelta(hours=2),
            )
            panel_down = choose_autoselect_country(
                9, {"de", "ee"}, None, None, now=now + timedelta(hours=3),
            )
            after_break = choose_autoselect_country(
                9, {"de", "ee"}, {"de": 12, "ee": 1},
                (now + timedelta(hours=2)).isoformat(), now=now + timedelta(hours=3),
            )
        assert (first, active, panel_down, after_break) == ("de", "de", "de", "ee")


def test_disconnected_main_moves_only_on_a_later_refresh():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "assignments.db"
        now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
        with patch("database.db_autoselect.get_db", side_effect=lambda: _db(path)):
            assert choose_autoselect_country(3, {"de", "ee"}, {"de": 1, "ee": 5}, None, now=now) == "de"
            assert choose_autoselect_country(
                3, {"de", "ee"}, {"ee": 5}, now.isoformat(), now=now + timedelta(minutes=1)
            ) == "ee"


def test_first_refresh_preserves_an_existing_online_connection():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "assignments.db"
        now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
        with patch("database.db_autoselect.get_db", side_effect=lambda: _db(path)):
            selected = choose_autoselect_country(
                11, {"de", "ee"}, {"de": 2, "ee": 8}, now.isoformat(),
                current_country="ee", now=now,
            )
        assert selected == "ee"
