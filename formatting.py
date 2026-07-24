"""Текст ТГ-сообщения из события — эмодзи + время в фиксированном поясе.

Единый пояс для входов/выходов — GMT+6, фиксированное смещение без перехода на летнее время
(сервер сам пишет лог в UTC).
"""

from datetime import datetime, timedelta, timezone

from events import Event, EventKind

GMT_PLUS_6 = timezone(timedelta(hours=6))

_ADVANCEMENT_EMOJI = {
    "made the advancement": "🏆",
    "reached the goal": "🎯",
    "completed the challenge": "🏅",
}


def _now_local_hm() -> str:
    return datetime.now(GMT_PLUS_6).strftime("%H:%M")


def format_event(ev: Event) -> str:
    if ev.kind == EventKind.ADVANCEMENT:
        emoji = next((e for key, e in _ADVANCEMENT_EMOJI.items() if key in ev.text), "🏆")
        return f"{emoji} {ev.text}"

    if ev.kind == EventKind.JOIN:
        return f"🟢 {ev.player} зашёл ({_now_local_hm()})"

    if ev.kind == EventKind.LEAVE:
        return f"🔴 {ev.player} вышел ({_now_local_hm()})"

    if ev.kind == EventKind.SERVER_START:
        return "⚙️ Сервер запущен"

    if ev.kind == EventKind.SERVER_STOP:
        return "⚙️ Сервер остановлен"

    return f"💀 {ev.text}"
