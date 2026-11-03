"""minebot — relays Minecraft events (deaths/advancements/joins) to Telegram."""

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

from config import load_config
from events import EventKind, parse_line
from formatting import format_event
from lifecycle import run_until_stopped
from log_tail import tail_lines
from mc_query import get_online
from sessions import SessionTracker

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("minebot")

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])

config = load_config(BASE_DIR / "config.toml")
sessions = SessionTracker(config.join_cooldown_min, BASE_DIR / config.sessions_csv)

bot = Bot(token=BOT_TOKEN)
router = Router()


@router.message(Command("online"))
async def cmd_online(message: Message) -> None:
    if message.chat.id != CHAT_ID:
        # logged so a wrong CHAT_ID in .env is easy to spot (and the right one to copy)
        log.info("/online ignored: chat id %s is not CHAT_ID %s", message.chat.id, CHAT_ID)
        return
    if not config.features.online_command:
        return
    try:
        online, max_players, names = await get_online(config.mc_host, config.mc_port)
    except Exception as e:
        log.warning("mc_query failed: %s", e)
        await message.answer("⚠️ Сервер сейчас недоступен.")
        return
    who = ", ".join(names) if names else "—"
    await message.answer(f"👥 Онлайн {online}/{max_players}: {who}")


async def watch_log() -> None:
    async for raw_line in tail_lines(config.log_path):
        ev = parse_line(raw_line)
        if ev is None:
            continue

        if ev.kind == EventKind.DEATH:
            if not config.features.deaths:
                continue
            if not (sessions.is_online(ev.player) or sessions.left_recently(ev.player)):
                # not a real player: diagnostic dump / console command response / etc.
                log.info("DEATH line rejected (not an online player): %s", ev.text)
                continue
        if ev.kind == EventKind.ADVANCEMENT and not config.features.advancements:
            continue
        if ev.kind in (EventKind.SERVER_START, EventKind.SERVER_STOP) and not config.features.server_events:
            continue

        if ev.kind == EventKind.JOIN:
            shown = sessions.on_join(ev.player)  # sessions.csv is always written, regardless of the feature flag
            if not config.features.joins or not shown:
                continue
        elif ev.kind == EventKind.LEAVE:
            shown = sessions.on_leave(ev.player)
            if not config.features.joins or not shown:
                continue

        text = format_event(ev)
        try:
            await bot.send_message(chat_id=CHAT_ID, text=text)
        except Exception as e:
            log.warning("send_message failed: %s", e)


async def poll_updates(dp: Dispatcher) -> None:
    polling = asyncio.create_task(
        dp.start_polling(bot, handle_signals=False, close_bot_session=False)
    )
    try:
        # Cancelling start_polling directly can leave its internal request task alive.
        await asyncio.shield(polling)
    finally:
        if not polling.done():
            try:
                await dp.stop_polling()
            except RuntimeError:
                # The task may have been cancelled before polling acquired its lock.
                polling.cancel()
        await asyncio.gather(polling, return_exceptions=True)


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    try:
        try:
            _, _, names = await get_online(config.mc_host, config.mc_port)
            sessions.seed_online(names)
            log.info("Online at startup: %s", names or "—")
        except Exception as e:
            log.warning("Failed to fetch the online player list at startup: %s", e)
        log.info("minebot started; log: %s; chat: %s", config.log_path, CHAT_ID)

        if config.features.online_command:
            # One signal owner stops both polling and log following.
            await run_until_stopped(watch_log(), poll_updates(dp))
        else:
            # Telegram permits one getUpdates listener per token; sending log events
            # still works when polling is disabled.
            log.info("online_command is disabled — polling not started")
            await run_until_stopped(watch_log())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
