"""Parses events out of Paper server log lines.

Death keywords are cross-checked against the official minecraft.wiki/w/Death_messages,
including "left the confines of this world" (world border), which is easy to miss when
relying on outdated lists. Java death message grammar has been stable since 1.9 ("X was
<verb> by Y" for entity-caused deaths) — matching the broad `was` catches new mobs (mace
smash, warden) without enumerating each one. Advancements use 3 localization keys, stable
since 1.12.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto

LOG_LINE_RE = re.compile(r"^\[(?P<time>\d{2}:\d{2}:\d{2})\] \[[^/]+/(?P<level>[A-Z]+)\]: (?P<msg>.*)$")

# WARNING: on offline-mode servers, nicknames are NOT restricted to the Mojang format (2-char
# names, special characters like § ° ´, etc.) — validating against a nickname alphabet here is
# NOT acceptable. Filtering out "non-gameplay" lines such as a named entity's diagnostic death
# dump or a console command response ("No entity was found", which also contains "was") happens
# in bot.py instead: a DEATH is only considered real if ev.player is currently in the set of
# known connected players (SessionTracker.is_online).

JOIN_RE = re.compile(r"^(?P<player>\S+) joined the game$")
LEAVE_RE = re.compile(r"^(?P<player>\S+) left the game$")
ADVANCEMENT_RE = re.compile(
    r"^(?P<player>\S+) has (?P<kind>made the advancement|reached the goal|completed the challenge) "
    r"\[(?P<name>.+)\]$"
)
SERVER_DONE_RE = re.compile(r"^Done \([\d.]+s\)! For help, type \"help\"$")
SERVER_STOPPING_RE = re.compile(r"^Stopping the server$")

# Death keywords — a matching line is treated as a death, the nickname is the line's first word.
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
    time_str: str  # "HH:MM:SS" from the log (UTC)
    player: str | None
    text: str  # display-ready text (no emoji — formatting.py adds those)


def parse_line(raw_line: str) -> Event | None:
    m = LOG_LINE_RE.match(raw_line.rstrip("\n"))
    if not m or m.group("level") != "INFO":
        return None

    time_str = m.group("time")
    msg = m.group("msg")

    if msg.startswith("<"):
        return None  # player chat, not an event

    if msg.startswith("Named entity "):
        return None  # named entity's diagnostic death dump — contains uuid/coordinates/died/was
        # and is easily mistaken for a "player death" by naive matching if not filtered explicitly

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
