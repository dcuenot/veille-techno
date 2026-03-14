from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class WeatherConfig:
    city: str
    lat: float
    lon: float


@dataclass(frozen=True)
class EditorConfig:
    model: str
    max_general_news: int
    max_tech_news: int


@dataclass(frozen=True)
class AudioConfig:
    engine: str
    voice: str
    output_dir: str
    retention_days: int


@dataclass(frozen=True)
class PublisherConfig:
    ha_media_dir: str
    media_player_entity: str
    s3_bucket: str = ""


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    log_dir: str


@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    category: str
    url: str = ""


@dataclass(frozen=True)
class Secrets:
    anthropic_api_key: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "eu-west-3"
    owm_api_key: str = ""
    ha_url: str = ""
    ha_token: str = ""


@dataclass(frozen=True)
class Settings:
    timezone: str
    weather: WeatherConfig
    editor: EditorConfig
    audio: AudioConfig
    publisher: PublisherConfig
    logging: LoggingConfig
    sources: tuple[SourceConfig, ...]
    secrets: Secrets = field(default_factory=Secrets)


def load_config(config_path: Path) -> Settings:
    """Load settings from YAML file and environment variables."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    load_dotenv()

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    sources = tuple(
        SourceConfig(
            name=s["name"],
            type=s["type"],
            category=s["category"],
            url=s.get("url", ""),
        )
        for s in raw.get("sources", [])
    )

    secrets = Secrets(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        aws_default_region=os.environ.get("AWS_DEFAULT_REGION", "eu-west-3"),
        owm_api_key=os.environ.get("OWM_API_KEY", ""),
        ha_url=os.environ.get("HA_URL", ""),
        ha_token=os.environ.get("HA_TOKEN", ""),
    )

    return Settings(
        timezone=raw["timezone"],
        weather=WeatherConfig(**raw["weather"]),
        editor=EditorConfig(**raw["editor"]),
        audio=AudioConfig(**raw["audio"]),
        publisher=PublisherConfig(**raw["publisher"]),
        logging=LoggingConfig(**raw["logging"]),
        sources=sources,
        secrets=secrets,
    )
