from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.orchestrator import run_pipeline, run_dry_run, play_briefing, collect_all, _build_sources


@patch("src.orchestrator.HomeAssistantPublisher")
@patch("src.orchestrator.generate_briefing")
@patch("src.orchestrator.fetch_weather")
@patch("src.orchestrator.collect_all")
@patch("src.orchestrator.load_config")
def test_pipeline_runs_end_to_end(
    mock_load_config, mock_collect, mock_weather,
    mock_briefing, mock_publisher_cls, tmp_path,
):
    from src.collector.base import Article
    from src.editor.briefing import BriefingSegment
    from src.weather.forecast import WeatherData
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )

    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.echo"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(anthropic_api_key="test", owm_api_key="test", ha_url="http://localhost:8123", ha_token="test"),
    )
    mock_collect.return_value = [
        Article(title=f"Article {i}", source="Test", url=f"https://example.com/{i}",
                published_at=datetime(2026, 3, 12, tzinfo=timezone.utc), summary="Summary")
        for i in range(10)
    ]
    mock_weather.return_value = WeatherData(city="Test", description="clair", temp_current=12.0, temp_min=8.0, temp_max=16.0)
    mock_briefing.return_value = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="outro", text="A demain."),
    ]
    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    run_pipeline(config_path=tmp_path / "settings.yaml")

    mock_collect.assert_called_once()
    mock_weather.assert_called_once()
    mock_briefing.assert_called_once()
    # Verify briefing text saved to file
    saved_file = tmp_path / "ha" / "latest_briefing.txt"
    assert saved_file.exists()
    text = saved_file.read_text(encoding="utf-8")
    assert "Bonjour." in text
    assert "A demain." in text


@patch("src.orchestrator.HomeAssistantPublisher")
@patch("src.orchestrator.collect_all")
@patch("src.orchestrator.load_config")
def test_pipeline_aborts_when_not_enough_articles(
    mock_load_config, mock_collect, mock_publisher_cls, tmp_path,
):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )
    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.echo"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(anthropic_api_key="test", owm_api_key="test", ha_url="http://localhost:8123", ha_token="test"),
    )
    mock_collect.return_value = [MagicMock() for _ in range(3)]
    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    run_pipeline(config_path=tmp_path / "settings.yaml")

    mock_publisher.notify_failure.assert_called_once()


@patch("src.orchestrator.HomeAssistantPublisher")
@patch("src.orchestrator.generate_briefing")
@patch("src.orchestrator.fetch_weather")
@patch("src.orchestrator.collect_all")
@patch("src.orchestrator.load_config")
def test_pipeline_handles_exception_and_notifies(
    mock_load_config, mock_collect, mock_weather, mock_generate,
    mock_publisher_cls, tmp_path,
):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )
    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.echo"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(anthropic_api_key="test", owm_api_key="test", ha_url="http://localhost:8123", ha_token="test"),
    )
    mock_collect.return_value = [MagicMock() for _ in range(10)]
    mock_weather.return_value = None  # weather unavailable
    mock_generate.side_effect = RuntimeError("API error")
    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    run_pipeline(config_path=tmp_path / "settings.yaml")

    mock_publisher.notify_failure.assert_called_once()
    call_args = mock_publisher.notify_failure.call_args[0][0]
    assert "API error" in call_args


@patch("src.orchestrator.fetch_weather")
@patch("src.orchestrator.load_config")
def test_dry_run_reports_missing_keys(mock_load_config, mock_weather, tmp_path):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )
    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.echo"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(),  # all keys empty
    )
    mock_weather.return_value = None  # weather fails

    run_dry_run(config_path=tmp_path / "settings.yaml")
    # should log errors but not raise


@patch("src.orchestrator.fetch_weather")
@patch("src.orchestrator.load_config")
def test_dry_run_all_ok(mock_load_config, mock_weather, tmp_path):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )
    from src.weather.forecast import WeatherData
    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.echo"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(anthropic_api_key="key", owm_api_key="key", ha_token="key"),
    )
    mock_weather.return_value = WeatherData(city="Test", description="clair", temp_current=12.0, temp_min=8.0, temp_max=16.0)

    run_dry_run(config_path=tmp_path / "settings.yaml")
    # should complete without errors


@patch("src.orchestrator.HomeAssistantPublisher")
@patch("src.orchestrator.load_config")
def test_play_briefing_sends_tts(mock_load_config, mock_publisher_cls, tmp_path):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )
    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.chambre"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(anthropic_api_key="test", owm_api_key="test", ha_url="http://localhost:8123", ha_token="test"),
    )
    # Create the briefing file
    ha_dir = tmp_path / "ha"
    ha_dir.mkdir(parents=True)
    (ha_dir / "latest_briefing.txt").write_text("Bonjour, voici le briefing.", encoding="utf-8")

    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    play_briefing(config_path=tmp_path / "settings.yaml")

    mock_publisher.play_tts.assert_called_once_with("Bonjour, voici le briefing.")


@patch("src.orchestrator.HomeAssistantPublisher")
@patch("src.orchestrator.load_config")
def test_play_briefing_no_file(mock_load_config, mock_publisher_cls, tmp_path):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )
    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.chambre"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(anthropic_api_key="test", owm_api_key="test", ha_url="http://localhost:8123", ha_token="test"),
    )
    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    play_briefing(config_path=tmp_path / "settings.yaml")

    mock_publisher.play_tts.assert_not_called()


def test_collect_all_handles_source_failure():
    from unittest.mock import MagicMock
    bad_source = MagicMock()
    bad_source.name = "bad"
    bad_source.fetch.side_effect = RuntimeError("network error")
    good_source = MagicMock()
    good_source.name = "good"
    from src.collector.base import Article
    from datetime import datetime, timezone
    good_source.fetch.return_value = [
        Article(title="Art", source="good", url="https://example.com/1",
                published_at=datetime(2026, 3, 12, tzinfo=timezone.utc), summary="s"),
    ]
    result = collect_all([bad_source, good_source])
    assert len(result) == 1


def test_build_sources_all_types(tmp_path):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets, SourceConfig,
    )
    settings = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(model="claude-haiku-4-5-20251001", max_general_news=5, max_tech_news=10),
        audio=AudioConfig(engine="polly", voice="Lea", output_dir=str(tmp_path), retention_days=7),
        publisher=PublisherConfig(ha_media_dir=str(tmp_path / "ha"), media_player_entity="media_player.echo"),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(
            SourceConfig(name="RSS Feed", type="rss", category="general", url="https://example.com/feed"),
            SourceConfig(name="HN", type="hackernews", category="tech", url=""),
            SourceConfig(name="GH", type="github_trending", category="tech", url=""),
            SourceConfig(name="Unknown", type="unknown", category="general", url=""),
        ),
        secrets=Secrets(),
    )
    sources = _build_sources(settings)
    # unknown type is skipped, 3 valid sources built
    assert len(sources) == 3
