"""Loads config.toml — feature toggles and paths, no code edits needed."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Features:
    deaths: bool
    advancements: bool
    joins: bool
    server_events: bool
    online_command: bool


@dataclass(frozen=True)
class Config:
    log_path: Path
    mc_host: str
    mc_port: int
    features: Features
    join_cooldown_min: int
    sessions_csv: Path


def load_config(path: Path) -> Config:
    with path.open("rb") as f:
        raw = tomllib.load(f)

    server = raw.get("server", {})
    features_raw = raw.get("features", {})
    joins = raw.get("joins", {})
    paths = raw.get("paths", {})

    return Config(
        log_path=Path(server["log_path"]),
        mc_host=server.get("mc_host", "127.0.0.1"),
        mc_port=int(server["mc_port"]),
        features=Features(
            deaths=features_raw.get("deaths", True),
            advancements=features_raw.get("advancements", True),
            joins=features_raw.get("joins", True),
            server_events=features_raw.get("server_events", False),
            online_command=features_raw.get("online_command", True),
        ),
        join_cooldown_min=int(joins.get("cooldown_min", 10)),
        sessions_csv=Path(paths.get("sessions_csv", "sessions.csv")),
    )
