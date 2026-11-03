import asyncio
import signal

import pytest

from lifecycle import run_until_stopped


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True], ids=["returned", "failed"])
async def test_worker_exit_cleans_up_other_workers_and_restores_handlers(failed):
    ready = asyncio.Event()
    cleaned = asyncio.Event()
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}

    async def follower():
        ready.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    async def finished():
        await ready.wait()
        if failed:
            raise RuntimeError("worker failed")

    if failed:
        with pytest.raises(RuntimeError, match="worker failed"):
            await run_until_stopped(follower(), finished())
    else:
        await run_until_stopped(follower(), finished())
    assert cleaned.is_set()
    assert {sig: signal.getsignal(sig) for sig in previous} == previous


@pytest.mark.asyncio
async def test_caller_cancellation_waits_for_worker_cleanup():
    ready = asyncio.Event()
    cleaned = asyncio.Event()

    async def follower():
        ready.set()
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            cleaned.set()

    task = asyncio.create_task(run_until_stopped(follower()))
    await ready.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cleaned.is_set()
