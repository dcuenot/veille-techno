"""Veille Techno — Main pipeline orchestrator.

Usage: python -m src.orchestrator [--config path/to/settings.yaml]
"""
from __future__ import annotations

import argparse
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config import Settings, load_config
from src.collector.base import Article, Source
from src.collector.rss import RSSSource
from src.collector.hackernews import HackerNewsSource
from src.collector.github_trending import GitHubTrendingSource
from src.collector.dedup import deduplicate
from src.weather.forecast import fetch_weather
from src.editor.briefing import generate_briefing
from src.publisher.homeassistant import HomeAssistantPublisher

logger = logging.getLogger("veille_techno")

MIN_ARTICLES = 5


def _setup_logging(settings: Settings) -> None:
    """Configure rotating file + console logging."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    log_dir = Path(settings.logging.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "veille-techno.log", maxBytes=5_000_000, backupCount=7,
    )
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    level_str = settings.logging.level.upper()
    level = logging.getLevelName(level_str)
    if not isinstance(level, int):
        raise ValueError(f"Invalid log level in config: {settings.logging.level!r}")
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def _build_sources(settings: Settings) -> list[Source]:
    """Build source instances from config."""
    sources: list[Source] = []
    for src_cfg in settings.sources:
        if src_cfg.type == "rss":
            sources.append(RSSSource(name=src_cfg.name, category=src_cfg.category, url=src_cfg.url))
        elif src_cfg.type == "hackernews":
            sources.append(HackerNewsSource(name=src_cfg.name, category=src_cfg.category))
        elif src_cfg.type == "github_trending":
            sources.append(GitHubTrendingSource(name=src_cfg.name, category=src_cfg.category))
    return sources


def collect_all(sources: list[Source]) -> list[Article]:
    """Fetch from all sources and deduplicate."""
    start = time.monotonic()
    all_articles: list[Article] = []
    for source in sources:
        try:
            articles = source.fetch()
            all_articles.extend(articles)
            logger.info("  %s: %d articles", source.name, len(articles))
        except Exception:
            logger.warning("  %s: FAILED", source.name, exc_info=True)
    deduped = deduplicate(all_articles)
    elapsed = time.monotonic() - start
    logger.info(
        "Collection complete: %d raw -> %d deduped in %.1fs",
        len(all_articles), len(deduped), elapsed,
    )
    return deduped


def run_pipeline(config_path: Path) -> None:
    """Execute the full briefing pipeline."""
    settings = load_config(config_path)
    _setup_logging(settings)
    logger.info("=== Veille Techno pipeline started ===")

    publisher = HomeAssistantPublisher(
        ha_media_dir=settings.publisher.ha_media_dir,
        ha_url=settings.secrets.ha_url,
        ha_token=settings.secrets.ha_token,
        media_player_entity=settings.publisher.media_player_entity,
        s3_bucket=settings.publisher.s3_bucket,
    )

    try:
        logger.info("Step 1: Collecting articles...")
        sources = _build_sources(settings)
        articles = collect_all(sources)

        if len(articles) < MIN_ARTICLES:
            msg = f"Not enough articles ({len(articles)}/{MIN_ARTICLES})"
            logger.warning(msg)
            publisher.notify_failure(msg)
            return

        logger.info("Step 2: Fetching weather...")
        start = time.monotonic()
        weather = fetch_weather(
            lat=settings.weather.lat,
            lon=settings.weather.lon,
            api_key=settings.secrets.owm_api_key,
        )
        if weather:
            logger.info("Weather: %s, %.0f°C in %.1fs", weather.description, weather.temp_current, time.monotonic() - start)
        else:
            logger.warning("Weather unavailable in %.1fs — will be omitted", time.monotonic() - start)

        logger.info("Step 3: Generating briefing...")
        start = time.monotonic()
        segments = generate_briefing(
            articles=articles,
            weather=weather,
            api_key=settings.secrets.anthropic_api_key,
            model=settings.editor.model,
            max_general_news=settings.editor.max_general_news,
            max_tech_news=settings.editor.max_tech_news,
        )
        logger.info("Briefing: %d segments in %.1fs", len(segments), time.monotonic() - start)

        logger.info("Step 4: Saving briefing text...")
        briefing_text = " ".join(seg.text for seg in segments)
        output_path = Path(settings.publisher.ha_media_dir) / "latest_briefing.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(briefing_text, encoding="utf-8")
        logger.info("Briefing saved to %s (%d chars)", output_path, len(briefing_text))

        logger.info("=== Prepare complete ===")

    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        publisher.notify_failure(f"Pipeline failed: {e}")


def play_briefing(config_path: Path) -> None:
    """Read saved briefing text and send via TTS."""
    settings = load_config(config_path)
    _setup_logging(settings)

    text_path = Path(settings.publisher.ha_media_dir) / "latest_briefing.txt"
    if not text_path.exists():
        logger.error("No briefing found at %s — run --prepare first", text_path)
        return

    text = text_path.read_text(encoding="utf-8")
    if not text.strip():
        logger.error("Briefing file is empty at %s", text_path)
        return

    publisher = HomeAssistantPublisher(
        ha_media_dir=settings.publisher.ha_media_dir,
        ha_url=settings.secrets.ha_url,
        ha_token=settings.secrets.ha_token,
        media_player_entity=settings.publisher.media_player_entity,
        s3_bucket=settings.publisher.s3_bucket,
    )
    publisher.play_tts(text)
    logger.info("Briefing played (%d chars)", len(text))


def run_dry_run(config_path: Path) -> None:
    """Validate config, test API keys, and source connectivity."""
    settings = load_config(config_path)
    _setup_logging(settings)
    logger.info("=== Dry run ===")
    errors: list[str] = []
    if not settings.secrets.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY not set")
    if not settings.secrets.owm_api_key:
        errors.append("OWM_API_KEY not set")
    if not settings.secrets.ha_token:
        errors.append("HA_TOKEN not set")
    sources = _build_sources(settings)
    logger.info("Configured %d sources", len(sources))
    weather = fetch_weather(
        lat=settings.weather.lat,
        lon=settings.weather.lon,
        api_key=settings.secrets.owm_api_key,
    )
    if weather:
        logger.info("Weather OK: %s", weather.description)
    else:
        errors.append("Weather API failed")
    if errors:
        for e in errors:
            logger.error("  %s", e)
        logger.error("Dry run FAILED")
    else:
        logger.info("Dry run OK — all checks passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Veille Techno Briefing")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/settings.yaml"),
        help="Path to settings.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and test API connectivity",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Collect news, generate briefing, save text (no TTS)",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play the latest saved briefing via TTS",
    )
    args = parser.parse_args()
    if args.dry_run:
        run_dry_run(args.config)
    elif args.play:
        play_briefing(args.config)
    elif args.prepare:
        run_pipeline(args.config)
    else:
        run_pipeline(args.config)


if __name__ == "__main__":
    main()
