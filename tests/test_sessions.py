import csv
import datetime as datetime_module

import pytest

import sessions as sessions_module
from sessions import GMT_PLUS_6, SessionTracker


class _Clock:
    def __init__(self, start: datetime_module.datetime):
        self.current = start

    def now(self, tz=None):
        return self.current

    def advance(self, **kwargs):
        self.current += datetime_module.timedelta(**kwargs)


@pytest.fixture
def clock(monkeypatch):
    c = _Clock(datetime_module.datetime(2026, 1, 1, 0, 0, 0, tzinfo=GMT_PLUS_6))

    class _FakeDateTime(datetime_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return c.now(tz)

    monkeypatch.setattr(sessions_module, "datetime", _FakeDateTime)
    return c


@pytest.fixture
def csv_path(tmp_path):
    return tmp_path / "sessions.csv"


def _read_rows(csv_path):
    with csv_path.open(encoding="utf-8") as f:
        return list(csv.reader(f))


def test_csv_is_created_with_header(csv_path, clock):
    SessionTracker(cooldown_min=10, csv_path=csv_path)
    rows = _read_rows(csv_path)
    assert rows == [["time", "player", "event"]]


def test_first_join_is_shown(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    assert tracker.on_join("Steve") is True


def test_join_marks_player_online(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    assert tracker.is_online("Steve") is False
    tracker.on_join("Steve")
    assert tracker.is_online("Steve") is True


def test_leave_marks_player_offline(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.on_join("Steve")
    tracker.on_leave("Steve")
    assert tracker.is_online("Steve") is False


def test_normal_leave_is_shown(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.on_join("Steve")
    assert tracker.on_leave("Steve") is True


def test_rejoin_within_cooldown_is_suppressed(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.on_join("Steve")
    tracker.on_leave("Steve")
    clock.advance(minutes=5)
    assert tracker.on_join("Steve") is False


def test_leave_after_suppressed_rejoin_is_also_suppressed(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.on_join("Steve")
    tracker.on_leave("Steve")
    clock.advance(minutes=5)
    tracker.on_join("Steve")
    clock.advance(minutes=1)
    assert tracker.on_leave("Steve") is False


def test_rejoin_after_cooldown_expires_is_shown(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.on_join("Steve")
    tracker.on_leave("Steve")
    clock.advance(minutes=11)
    assert tracker.on_join("Steve") is True


def test_csv_logs_every_join_and_leave_regardless_of_suppression(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.on_join("Steve")
    tracker.on_leave("Steve")
    clock.advance(minutes=5)
    tracker.on_join("Steve")  # suppressed in chat, still logged to csv
    rows = _read_rows(csv_path)
    events = [(row[1], row[2]) for row in rows[1:]]
    assert events == [("Steve", "join"), ("Steve", "leave"), ("Steve", "join")]


def test_cooldown_is_per_player(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.on_join("Steve")
    tracker.on_leave("Steve")
    clock.advance(minutes=1)
    assert tracker.on_join("Alex") is True


def test_seed_online(csv_path, clock):
    tracker = SessionTracker(cooldown_min=10, csv_path=csv_path)
    tracker.seed_online(["Steve", "Alex"])
    assert tracker.is_online("Steve") is True
    assert tracker.is_online("Alex") is True
    assert tracker.is_online("Herobrine") is False
