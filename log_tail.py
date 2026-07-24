"""Асинхронный tail-follow logs/latest.log с обработкой ротации.

Paper переименовывает/пересоздаёт latest.log при рестарте сервера (новый inode на диске) —
отслеживаем (st_dev, st_ino) и переоткрываем файл с начала при расхождении. При старте
встаём в КОНЕЦ текущего файла — события, случившиеся пока бот не работал, не досылаются.
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
                # неполная строка (файл дописывается) — подождать и перечитать с той же позиции
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
