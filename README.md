# minebot

A Telegram bot that relays Minecraft server events (deaths, achievements, joins/leaves)
into a Telegram chat — reads the server log in real time and formats events nicely.

Built together with [Claude Code](https://claude.com/claude-code) — from reading the
legacy code and making architecture decisions to live debugging on a production server.

## What it does

- 💀 Player deaths, 🏆 achievements, 🟢🔴 joins/leaves (with anti-flap on flaky connections)
- `/online` — who is on the server right now (a direct server query, not log polling)
- Every feature can be turned on/off in `config.toml`, no code changes needed
- Survives log file rotation and server restarts

## Requirements

- **Python 3.12 or newer.**
- A Minecraft **Paper** (or compatible) server you can read `logs/latest.log` from —
  local access or a shared volume/mount. The bot does not connect to the server console,
  only tails the log file and queries the server status port.
- No GPU, no extra system packages beyond Python — all dependencies are pure-Python
  (see `requirements.txt`: aiogram, python-dotenv, mcstatus).

## Setup

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN and CHAT_ID
```

Edit `config.toml`: set `server.log_path` to your server's `logs/latest.log` and
`server.mc_host`/`server.mc_port` to where the server's status port is reachable.

## Run

```bash
venv/bin/python minebot.py
```

## Deploy

See `deploy/minebot.service` for a systemd unit template. Edit the paths
(`WorkingDirectory`, `ExecStart`, `User`/`Group`) to match where you installed it.

## Tests

```bash
venv/bin/pip install -r requirements-dev.txt
venv/bin/pytest
venv/bin/ruff check .
```

## How it's built

- `minebot.py` — entry point, aiogram router for commands
- `log_tail.py` — async log reading that survives file rotation
- `events.py` — parses log lines into events
- `sessions.py` — anti-flap for joins/leaves, plus tracking who is actually online
- `formatting.py` — message formatting
- `mc_query.py` — server status query for `/online`
