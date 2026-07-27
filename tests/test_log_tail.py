import asyncio
import os

import pytest

from log_tail import tail_lines

pytestmark = pytest.mark.asyncio


async def _collect(gen, n, timeout=3.0):
    results = []

    async def _run():
        async for line in gen:
            results.append(line)
            if len(results) >= n:
                return

    await asyncio.wait_for(_run(), timeout)
    return results


async def test_preexisting_content_is_not_backfilled(tmp_path):
    path = tmp_path / "latest.log"
    path.write_text("old line before bot started\n")
    gen = tail_lines(path, poll_interval=0.01)

    async def writer():
        await asyncio.sleep(0.05)
        with path.open("a", encoding="utf-8") as f:
            f.write("new line\n")

    asyncio.create_task(writer())
    lines = await _collect(gen, 1)
    assert lines == ["new line\n"]


async def test_multiple_new_lines_are_yielded_in_order(tmp_path):
    path = tmp_path / "latest.log"
    path.write_text("")
    gen = tail_lines(path, poll_interval=0.01)

    async def writer():
        await asyncio.sleep(0.02)
        with path.open("a", encoding="utf-8") as f:
            f.write("first\nsecond\n")

    asyncio.create_task(writer())
    lines = await _collect(gen, 2)
    assert lines == ["first\n", "second\n"]


async def test_partial_line_waits_for_completion(tmp_path):
    path = tmp_path / "latest.log"
    path.write_text("")
    gen = tail_lines(path, poll_interval=0.01)

    async def writer():
        await asyncio.sleep(0.02)
        with path.open("a", encoding="utf-8") as f:
            f.write("partial")
        await asyncio.sleep(0.05)
        with path.open("a", encoding="utf-8") as f:
            f.write(" line\n")

    asyncio.create_task(writer())
    lines = await _collect(gen, 1)
    assert lines == ["partial line\n"]


async def test_rotation_reopens_from_start_of_new_file(tmp_path):
    # Paper rotates by atomically replacing the path with a new inode (os.replace),
    # never leaving the path missing from stat's perspective — unlike a plain
    # unlink()+recreate, which the tailer would instead treat as "file disappeared".
    path = tmp_path / "latest.log"
    path.write_text("old session\n")
    gen = tail_lines(path, poll_interval=0.01)

    async def rotate():
        await asyncio.sleep(0.05)
        new_file = tmp_path / "latest.log.new"
        new_file.write_text("fresh session start\n")
        os.replace(new_file, path)

    asyncio.create_task(rotate())
    lines = await _collect(gen, 1)
    assert lines == ["fresh session start\n"]


async def test_waits_for_file_to_be_created(tmp_path):
    # Opening a brand-new file always seeks to its current end (same as any other
    # first-open), so content written in the same instant as file creation would still
    # be skipped — only content appended *after* the tailer has opened the file is seen.
    path = tmp_path / "latest.log"
    gen = tail_lines(path, poll_interval=0.01)

    async def create_then_append():
        await asyncio.sleep(0.05)
        path.write_text("")
        await asyncio.sleep(0.05)
        with path.open("a", encoding="utf-8") as f:
            f.write("server started\n")

    asyncio.create_task(create_then_append())
    lines = await _collect(gen, 1)
    assert lines == ["server started\n"]
