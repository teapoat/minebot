"""Статус сервера для /online — через Server List Ping (не требует настройки query-протокола).

Условие: на сервере enable-status=true и hide-online-players=false в server.properties —
иначе список игроков в ответе не приходит.
"""

from mcstatus import JavaServer


async def get_online(host: str, port: int) -> tuple[int, int, list[str]]:
    """Возвращает (онлайн, макс, ники). Кидает исключение, если сервер недоступен."""
    server = JavaServer(host, port)
    status = await server.async_status()
    names = [p.name for p in (status.players.sample or [])]
    return status.players.online, status.players.max, names
