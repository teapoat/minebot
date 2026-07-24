"""Парсинг событий из строк лога Paper.

Ключевые слова смертей сверены с официальной minecraft.wiki/w/Death_messages — в т.ч. пробел
"left the confines of this world" (мировой барьер), который легко упустить, ориентируясь на
устаревшие списки. Грамматика смертей в Java стабильна с 1.9 ("X was <глагол> by Y" для деталей
от сущности) — широкий `was` ловит новых мобов (mace smash, warden) без перечисления каждого.
Ачивки — 3 ключа локализации, стабильны с 1.12.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto

LOG_LINE_RE = re.compile(r"^\[(?P<time>\d{2}:\d{2}:\d{2})\] \[[^/]+/(?P<level>[A-Z]+)\]: (?P<msg>.*)$")

JOIN_RE = re.compile(r"^(?P<player>\S+) joined the game$")
LEAVE_RE = re.compile(r"^(?P<player>\S+) left the game$")
ADVANCEMENT_RE = re.compile(
    r"^(?P<player>\S+) has (?P<kind>made the advancement|reached the goal|completed the challenge) "
    r"\[(?P<name>.+)\]$"
)
SERVER_DONE_RE = re.compile(r"^Done \([\d.]+s\)! For help, type \"help\"$")
SERVER_STOPPING_RE = re.compile(r"^Stopping the server$")

# Ключевые слова смертей — при совпадении строка считается смертью, ник = первое слово строки.
DEATH_KEYWORDS = (
    "died", "was", "walked into", "drowned", "experienced kinetic energy", "blew up",
    "hit the ground", "fell", "went", "burned to death", "was burnt", "tried to swim",
    "discovered the floor", "froze to death", "starved to", "suffocated in a wall",
    "t want to live", "withered away", "left the confines of this world",
)


class EventKind(Enum):
    DEATH = auto()
    ADVANCEMENT = auto()
    JOIN = auto()
    LEAVE = auto()
    SERVER_START = auto()
    SERVER_STOP = auto()


@dataclass(frozen=True)
class Event:
    kind: EventKind
    time_str: str  # "HH:MM:SS" из лога (UTC)
    player: str | None
    text: str  # готовый для показа текст (без эмодзи, эмодзи добавляет formatting.py)


def parse_line(raw_line: str) -> Event | None:
    m = LOG_LINE_RE.match(raw_line.rstrip("\n"))
    if not m or m.group("level") != "INFO":
        return None

    time_str = m.group("time")
    msg = m.group("msg")

    if msg.startswith("<"):
        return None  # чат игрока, не событие

    if m2 := JOIN_RE.match(msg):
        player = m2.group("player")
        return Event(EventKind.JOIN, time_str, player, f"{player} joined the game")

    if m2 := LEAVE_RE.match(msg):
        player = m2.group("player")
        return Event(EventKind.LEAVE, time_str, player, f"{player} left the game")

    if m2 := ADVANCEMENT_RE.match(msg):
        return Event(EventKind.ADVANCEMENT, time_str, m2.group("player"), msg)

    if SERVER_DONE_RE.match(msg):
        return Event(EventKind.SERVER_START, time_str, None, msg)

    if SERVER_STOPPING_RE.match(msg):
        return Event(EventKind.SERVER_STOP, time_str, None, msg)

    first_word = msg.split(" ", 1)[0]
    if first_word and any(kw in msg for kw in DEATH_KEYWORDS):
        return Event(EventKind.DEATH, time_str, first_word, msg)

    return None
