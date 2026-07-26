"""Server status for /online — via Server List Ping (no query protocol setup required).

Requires enable-status=true and hide-online-players=false in server.properties —
otherwise the player list won't be included in the response.
"""

from mcstatus import JavaServer


async def get_online(host: str, port: int) -> tuple[int, int, list[str]]:
    """Returns (online, max, nicknames). Raises if the server is unreachable."""
    server = JavaServer(host, port)
    status = await server.async_status()
    names = [p.name for p in (status.players.sample or [])]
    return status.players.online, status.players.max, names
