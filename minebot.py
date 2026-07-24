"""minebot — трансляция событий Minecraft (смерти/ачивки/входы) в Telegram."""

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
    if message.chat.id != CHAT_ID or not config.features.online_command:
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
            if not sessions.is_online(ev.player):
                # не реальный игрок: диагностический дамп / ответ консольной команды и т.п.
                log.info("DEATH-строка отклонена (не онлайн-игрок): %s", ev.text)
                continue
        if ev.kind == EventKind.ADVANCEMENT and not config.features.advancements:
            continue
        if ev.kind in (EventKind.SERVER_START, EventKind.SERVER_STOP) and not config.features.server_events:
            continue

        if ev.kind == EventKind.JOIN:
            shown = sessions.on_join(ev.player)  # sessions.csv пишет всегда, вне зависимости от фичи
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


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    try:
        _, _, names = await get_online(config.mc_host, config.mc_port)
        sessions.seed_online(names)
        log.info("Онлайн при старте: %s", names or "—")
    except Exception as e:
        log.warning("Не удалось получить список онлайн при старте: %s", e)
    log.info("minebot запущен; лог: %s; чат: %s", config.log_path, CHAT_ID)
    await asyncio.gather(watch_log(), dp.start_polling(bot))


if __name__ == "__main__":
    asyncio.run(main())
