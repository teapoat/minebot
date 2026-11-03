"""Stop all service workers together and wait for their cleanup."""

import asyncio
from collections.abc import Coroutine
import signal
from typing import Any


async def run_until_stopped(*workers: Coroutine[Any, Any, None]) -> None:
    loop = asyncio.get_running_loop()
    stopped = asyncio.Event()
    previous_handlers = {}
    tasks = []
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous = signal.getsignal(sig)
            try:
                loop.add_signal_handler(sig, stopped.set)
            except NotImplementedError:
                # Windows does not support event-loop signal handlers.
                continue
            previous_handlers[sig] = previous
        tasks = [asyncio.create_task(worker) for worker in workers]
        stop_task = asyncio.create_task(stopped.wait())
        tasks.append(stop_task)
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # A failed worker must still fail the service after the others are stopped.
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for sig, previous in previous_handlers.items():
            loop.remove_signal_handler(sig)
            signal.signal(sig, previous)
