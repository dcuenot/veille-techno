from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import load_config, Settings


def test_load_config_returns_settings(tmp_path: Path):
    yaml_content = """
timezone: Europe/Paris
weather:
  city: Fontenay-sous-Bois
  lat: 48.8566
  lon: 2.4739
editor:
  model: claude-haiku-4-5-20251001
  max_general_news: 5
  max_tech_news: 10
audio:
  engine: polly
  voice: Lea
  output_dir: output/
  retention_days: 7
publisher:
  ha_media_dir: /config/www/briefings/
logging:
  level: INFO
  log_dir: /tmp/logs/
sources:
  - name: Le Monde
    type: rss
    url: https://www.lemonde.fr/rss/une.xml
    category: general
"""
    config_file = tmp_path / "settings.yaml"
    config_file.write_text(yaml_content)

    settings = load_config(config_file)

    assert isinstance(settings, Settings)
    assert settings.timezone == "Europe/Paris"
    assert settings.weather.city == "Fontenay-sous-Bois"
    assert settings.editor.model == "claude-haiku-4-5-20251001"
    assert settings.audio.voice == "Lea"
    assert len(settings.sources) == 1
    assert settings.sources[0].name == "Le Monde"


def test_load_config_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/settings.yaml"))


def test_load_config_loads_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    yaml_content = """
timezone: Europe/Paris
weather:
  city: Test
  lat: 0.0
  lon: 0.0
editor:
  model: claude-haiku-4-5-20251001
  max_general_news: 5
  max_tech_news: 10
audio:
  engine: polly
  voice: Lea
  output_dir: output/
  retention_days: 7
publisher:
  ha_media_dir: /tmp/
logging:
  level: INFO
  log_dir: /tmp/logs/
sources: []
"""
    config_file = tmp_path / "settings.yaml"
    config_file.write_text(yaml_content)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-aws")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("OWM_API_KEY", "test-owm")
    monkeypatch.setenv("HA_URL", "http://localhost:8123")
    monkeypatch.setenv("HA_TOKEN", "test-token")

    settings = load_config(config_file)

    assert settings.secrets.anthropic_api_key == "test-key"
    assert settings.secrets.owm_api_key == "test-owm"
