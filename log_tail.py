"""Async tail-follow of logs/latest.log with rotation handling.

Paper renames/recreates latest.log on server restart (new inode on disk) — we track
(st_dev, st_ino) and reopen the file from the start when it changes. On startup we seek
to the END of the current file — events that happened while the bot wasn't running are
not backfilled.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path


async def tail_lines(path: Path, poll_interval: float = 0.5) -> AsyncIterator[str]:
    f = None
    inode: tuple[int, int] | None = None
    try:
        while True:
            if f is None:
                if not path.exists():
                    await asyncio.sleep(poll_interval)
                    continue
                f = path.open("r", encoding="utf-8", errors="replace")
                f.seek(0, 2)
                st = path.stat()
                inode = (st.st_dev, st.st_ino)

            line = f.readline()
            if line:
                if line.endswith("\n"):
                    yield line
                    continue
                # partial line (file still being written) — wait and re-read from the same position
                f.seek(f.tell() - len(line))
                await asyncio.sleep(poll_interval)
                continue

            try:
                st = path.stat()
            except FileNotFoundError:
                f.close()
                f = None
                await asyncio.sleep(poll_interval)
                continue

            if (st.st_dev, st.st_ino) != inode:
                f.close()
                f = path.open("r", encoding="utf-8", errors="replace")
                inode = (st.st_dev, st.st_ino)
                continue

            await asyncio.sleep(poll_interval)
    finally:
        if f is not None:
            f.close()
