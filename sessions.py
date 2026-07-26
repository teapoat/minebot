"""Join/leave cooldown (anti-flapping) + the sessions.csv log.

Cooldown is a per-player sliding window: the first join and the leave that follows it in a
session are shown in the chat; if a player reconnects faster than cooldown_min after leaving,
we treat it as flapping (bad network) and suppress both the repeat join and the leave that
follows it, until a gap longer than cooldown_min passes. sessions.csv logs ALL joins/leaves
without exception (raw data kept for future stats) — suppression only affects chat messages.

Also tracks the set of CURRENTLY connected players (`is_online`) — used to filter out
"deaths" whose subject isn't a real online player: the server (Paper) occasionally logs a
diagnostic line like "Named entity X[...] died: ..." for named mobs/pets, and the console
can respond with "No entity was found" to a failed command — both contain the word "was" and
without this check would be sent to the chat as a real player death. Nicknames on unlicensed
(offline-mode) servers aren't restricted to the Mojang format — validating against a nickname
alphabet isn't acceptable, only checking whether the player is currently in the game is.
"""

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

GMT_PLUS_6 = timezone(timedelta(hours=6))


@dataclass
class _PlayerState:
    last_leave: datetime | None = None
    suppressed: bool = False


class SessionTracker:
    def __init__(self, cooldown_min: int, csv_path: Path):
        self._cooldown = timedelta(minutes=cooldown_min)
        self._csv_path = csv_path
        self._state: dict[str, _PlayerState] = {}
        self._online: set[str] = set()
        if not self._csv_path.exists():
            self._csv_path.write_text("time,player,event\n", encoding="utf-8")

    def seed_online(self, players: list[str]) -> None:
        """Seeds the connected-player set at bot startup (the server may have been running before it)."""
        self._online.update(players)

    def is_online(self, player: str) -> bool:
        return player in self._online

    def _log_csv(self, now: datetime, player: str, event: str) -> None:
        with self._csv_path.open("a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([now.strftime("%Y-%m-%d %H:%M:%S"), player, event])

    def on_join(self, player: str) -> bool:
        """Returns True if the join should be shown in the chat."""
        now = datetime.now(GMT_PLUS_6)
        self._log_csv(now, player, "join")
        self._online.add(player)
        st = self._state.setdefault(player, _PlayerState())
        if st.last_leave is not None and (now - st.last_leave) < self._cooldown:
            st.suppressed = True
            return False
        st.suppressed = False
        return True

    def on_leave(self, player: str) -> bool:
        """Returns True if the leave should be shown in the chat."""
        now = datetime.now(GMT_PLUS_6)
        self._log_csv(now, player, "leave")
        self._online.discard(player)
        st = self._state.setdefault(player, _PlayerState())
        st.last_leave = now
        return not st.suppressed
