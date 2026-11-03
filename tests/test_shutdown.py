"""Exercise the real entry point without reading credentials or contacting services."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


DRIVER = '''
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

import config
import dotenv

# Never load a local .env or a deployed configuration in this process.
dotenv.load_dotenv = lambda *args, **kwargs: None
os.environ["BOT_TOKEN"] = "123456:TEST_ONLY_TOKEN_FOR_OFFLINE_CHECKS"
os.environ["CHAT_ID"] = "1"
polling = os.environ["TEST_POLLING"] == "1"
config.load_config = lambda path: SimpleNamespace(
    join_cooldown_min=10, sessions_csv=str(Path.cwd() / "sessions.csv"),
    log_path=Path.cwd() / "latest.log",
    features=SimpleNamespace(online_command=polling),
)

import minebot

async def get_online(*args):
    return 0, 0, []

async def watch_log():
    Path("watch-ready").touch()
    try:
        await asyncio.Event().wait()
    finally:
        Path("watch-stopped").touch()

async def poll(self, bot, **kwargs):
    Path("poll-ready").touch()
    try:
        await asyncio.Event().wait()
    finally:
        Path("poll-stopped").touch()

original_close = minebot.bot.session.close
async def close():
    if polling:
        assert Path("poll-stopped").exists(), "session closed before polling cleanup"
    await original_close()
    Path("session-closed").touch()

minebot.config.mc_host = "localhost"
minebot.config.mc_port = 25565
minebot.get_online = get_online
minebot.watch_log = watch_log
minebot.Dispatcher._polling = poll
minebot.bot.session.close = close
asyncio.run(minebot.main())
'''


@pytest.mark.skipif(os.name != "posix", reason="Unix service signals")
@pytest.mark.parametrize("polling", [True, False], ids=["polling", "no-polling"])
@pytest.mark.parametrize("stop_signal", [signal.SIGTERM, signal.SIGINT], ids=["term", "interrupt"])
def test_signal_stops_log_and_closes_session(tmp_path, polling, stop_signal):
    driver = tmp_path / "worker.py"
    driver.write_text(DRIVER, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env["TEST_POLLING"] = "1" if polling else "0"
    process = subprocess.Popen(
        [sys.executable, str(driver)], cwd=tmp_path, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        ready = tmp_path / ("poll-ready" if polling else "watch-ready")
        deadline = time.monotonic() + 10
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), process.communicate(timeout=1)
        process.send_signal(stop_signal)
        stdout, stderr = process.communicate(timeout=3)
        assert process.returncode == 0, stdout + stderr
        assert (tmp_path / "watch-stopped").exists()
        assert (tmp_path / "session-closed").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=3)
