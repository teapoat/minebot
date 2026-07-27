import datetime as datetime_module

import formatting
from events import Event, EventKind
from formatting import GMT_PLUS_6, format_event


class _FixedDateTime(datetime_module.datetime):
    """Stand-in for datetime.datetime whose now() always lands at a fixed instant."""

    fixed = datetime_module.datetime(2026, 1, 1, 10, 30, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.fixed.replace(tzinfo=tz) if tz else cls.fixed


def test_now_local_hm_uses_gmt_plus_6(monkeypatch):
    monkeypatch.setattr(formatting, "datetime", _FixedDateTime)
    assert formatting._now_local_hm() == "10:30"


def test_format_join(monkeypatch):
    monkeypatch.setattr(formatting, "datetime", _FixedDateTime)
    ev = Event(EventKind.JOIN, "04:30:00", "Steve", "Steve joined the game")
    assert format_event(ev) == "🟢 Steve зашёл (10:30)"


def test_format_leave(monkeypatch):
    monkeypatch.setattr(formatting, "datetime", _FixedDateTime)
    ev = Event(EventKind.LEAVE, "04:30:00", "Steve", "Steve left the game")
    assert format_event(ev) == "🔴 Steve вышел (10:30)"


def test_format_death():
    ev = Event(EventKind.DEATH, "14:23:05", "Player1", "Player1 was slain by Piglin")
    assert format_event(ev) == "💀 Player1 was slain by Piglin"


def test_format_advancement_made():
    ev = Event(EventKind.ADVANCEMENT, "14:23:05", "Steve", "Steve has made the advancement [Stone Age]")
    assert format_event(ev) == "🏆 Steve has made the advancement [Stone Age]"


def test_format_advancement_goal():
    ev = Event(EventKind.ADVANCEMENT, "14:23:05", "Steve", "Steve has reached the goal [Bee Our Guest]")
    assert format_event(ev) == "🎯 Steve has reached the goal [Bee Our Guest]"


def test_format_advancement_challenge():
    ev = Event(
        EventKind.ADVANCEMENT, "14:23:05", "Steve", "Steve has completed the challenge [Uneasy Alliance]"
    )
    assert format_event(ev) == "🏅 Steve has completed the challenge [Uneasy Alliance]"


def test_format_server_start():
    ev = Event(EventKind.SERVER_START, "14:23:05", None, 'Done (34.567s)! For help, type "help"')
    assert format_event(ev) == "⚙️ Сервер запущен"


def test_format_server_stop():
    ev = Event(EventKind.SERVER_STOP, "14:23:05", None, "Stopping the server")
    assert format_event(ev) == "⚙️ Сервер остановлен"


def test_gmt_plus_6_has_no_dst_offset():
    assert GMT_PLUS_6.utcoffset(None) == datetime_module.timedelta(hours=6)
