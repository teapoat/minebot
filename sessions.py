"""Кулдаун входов/выходов (анти-дребезг) + журнал sessions.csv.

Кулдаун — скользящее окно per-игрок: первый вход и следующий за ним выход в сессии
показываются в чат; если игрок переподключается быстрее cooldown_min после выхода — считаем
это дребезгом (плохая сеть) и глушим и повторный вход, и следующий за ним выход, пока не
пройдёт пауза длиннее cooldown_min. sessions.csv пишет ВСЕ входы/выходы без исключений (сырые
данные — задел под будущую статистику), глушение касается только сообщений в чат.
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
        if not self._csv_path.exists():
            self._csv_path.write_text("time,player,event\n", encoding="utf-8")

    def _log_csv(self, now: datetime, player: str, event: str) -> None:
        with self._csv_path.open("a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([now.strftime("%Y-%m-%d %H:%M:%S"), player, event])

    def on_join(self, player: str) -> bool:
        """Возвращает True, если вход нужно показать в чат."""
        now = datetime.now(GMT_PLUS_6)
        self._log_csv(now, player, "join")
        st = self._state.setdefault(player, _PlayerState())
        if st.last_leave is not None and (now - st.last_leave) < self._cooldown:
            st.suppressed = True
            return False
        st.suppressed = False
        return True

    def on_leave(self, player: str) -> bool:
        """Возвращает True, если выход нужно показать в чат."""
        now = datetime.now(GMT_PLUS_6)
        self._log_csv(now, player, "leave")
        st = self._state.setdefault(player, _PlayerState())
        st.last_leave = now
        return not st.suppressed
