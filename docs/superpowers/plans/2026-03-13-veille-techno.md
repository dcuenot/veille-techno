# Veille Techno Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily tech news briefing pipeline that collects news, generates an editorialized audio briefing via Claude + Amazon Polly, and deposits it on Home Assistant for playback on Amazon Echo.

**Architecture:** Sequential pipeline of 5 components (collector, weather, editor, audio, publisher) orchestrated by a main script. Each component is isolated behind an interface. Config-driven via YAML + .env.

**Tech Stack:** Python 3.11+, feedparser, anthropic, boto3, pydub, requests, rapidfuzz, python-dotenv, pyyaml. System dep: ffmpeg.

**Spec:** `docs/superpowers/specs/2026-03-12-veille-techno-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `config/settings.example.yaml` | Template config (sources, voice, weather, model) |
| `config/settings.yaml` | User's active config (gitignored) |
| `.env.example` | Template for secrets |
| `.env` | User's secrets (gitignored) |
| `.gitignore` | Ignore .env, settings.yaml, venv, __pycache__, output/ |
| `requirements.txt` | Python dependencies |
| `src/__init__.py` | Package root |
| `src/config.py` | Load and validate settings.yaml + .env |
| `src/collector/__init__.py` | Package init |
| `src/collector/base.py` | `Article` dataclass + `Source` ABC |
| `src/collector/rss.py` | Generic RSS collector |
| `src/collector/hackernews.py` | Hacker News via Algolia API |
| `src/collector/github_trending.py` | GitHub Trending scraper |
| `src/collector/dedup.py` | Deduplication by URL + fuzzy title match |
| `src/weather/__init__.py` | Package init |
| `src/weather/forecast.py` | OpenWeatherMap API client |
| `src/editor/__init__.py` | Package init |
| `src/editor/briefing.py` | Claude API: select + editorialize articles |
| `src/editor/ssml.py` | SSML template builder from structured segments |
| `src/audio/__init__.py` | Package init |
| `src/audio/base.py` | `TTSEngine` ABC |
| `src/audio/polly.py` | Amazon Polly implementation with SSML chunking |
| `src/publisher/__init__.py` | Package init |
| `src/publisher/homeassistant.py` | Copy MP3 + notify HA |
| `src/orchestrator.py` | Main pipeline: collect -> weather -> edit -> audio -> publish |
| `tests/conftest.py` | Shared fixtures |
| `tests/collector/test_base.py` | Test Article dataclass |
| `tests/collector/test_rss.py` | Test RSS collector |
| `tests/collector/test_hackernews.py` | Test HN collector |
| `tests/collector/test_github_trending.py` | Test GitHub Trending scraper |
| `tests/collector/test_dedup.py` | Test deduplication |
| `tests/weather/test_forecast.py` | Test weather client |
| `tests/editor/test_briefing.py` | Test briefing generation |
| `tests/editor/test_ssml.py` | Test SSML template |
| `tests/audio/test_polly.py` | Test Polly TTS + chunking |
| `tests/publisher/test_homeassistant.py` | Test HA publisher |
| `tests/test_orchestrator.py` | Test full pipeline |
| `tests/test_config.py` | Test config loading |

---

## Chunk 1: Project Scaffolding + Config

### Task 1: Project setup

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config/settings.example.yaml`
- Create: `src/__init__.py`

- [ ] **Step 1: Create .gitignore**

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# Secrets
.env
config/settings.yaml

# Output
output/

# IDE
.vscode/
.idea/

# OS
.DS_Store
```

- [ ] **Step 2: Create requirements.txt**

```
feedparser>=6.0,<7.0
anthropic>=0.40,<1.0
boto3>=1.35,<2.0
pydub>=0.25,<1.0
requests>=2.31,<3.0
rapidfuzz>=3.6,<4.0
python-dotenv>=1.0,<2.0
pyyaml>=6.0,<7.0
pytest>=8.0,<9.0
pytest-cov>=5.0,<6.0
```

- [ ] **Step 3: Create .env.example**

```
ANTHROPIC_API_KEY=sk-ant-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=eu-west-3
OWM_API_KEY=...
HA_URL=http://homeassistant.local:8123
HA_TOKEN=...
```

- [ ] **Step 4: Create config/settings.example.yaml**

```yaml
# Veille Techno - Configuration
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
  media_player_entity: media_player.echo_salon

logging:
  level: INFO
  log_dir: /config/logs/

sources:
  - name: Le Monde
    type: rss
    url: https://www.lemonde.fr/rss/une.xml
    category: general
  - name: France Info
    type: rss
    url: https://www.francetvinfo.fr/titres.rss
    category: general
  - name: Les Echos
    type: rss
    url: https://syndication.lesechos.fr/rss/rss_france.xml
    category: general
  - name: Reuters
    type: rss
    url: https://www.reutersagency.com/feed/?best-topics=tech
    category: general
  - name: BBC News
    type: rss
    url: https://feeds.bbci.co.uk/news/technology/rss.xml
    category: general
  - name: Hacker News
    type: hackernews
    category: tech
  - name: TechCrunch
    type: rss
    url: https://techcrunch.com/feed/
    category: tech
  - name: GitHub Trending
    type: github_trending
    category: tech
  - name: dev.to
    type: rss
    url: https://dev.to/feed
    category: tech
  - name: Papers with Code
    type: rss
    url: https://paperswithcode.com/latest
    category: tech
  - name: Anthropic Blog
    type: rss
    url: https://www.anthropic.com/rss.xml
    category: tech
  - name: OpenAI Blog
    type: rss
    url: https://openai.com/blog/rss.xml
    category: tech
  - name: Google AI Blog
    type: rss
    url: https://blog.google/technology/ai/rss/
    category: tech
  - name: AWS What's New
    type: rss
    url: https://aws.amazon.com/about-aws/whats-new/recent/feed/
    category: tech
  - name: Google Cloud Blog
    type: rss
    url: https://cloud.google.com/blog/feed
    category: tech
  - name: The Hacker News Security
    type: rss
    url: https://feeds.feedburner.com/TheHackersNews
    category: tech
```

- [ ] **Step 5: Create src/__init__.py**

```python
```

(Empty file — package marker only)

- [ ] **Step 6: Init venv and install deps**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Expected: All packages install successfully.

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt .env.example config/settings.example.yaml src/__init__.py
git commit -m "chore: scaffold project with deps, config templates, and gitignore"
```

---

### Task 2: Configuration loader

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test for config loader**

Create `tests/__init__.py` (empty) and `tests/test_config.py`:

```python
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
  media_player_entity: media_player.echo_salon
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
  media_player_entity: media_player.test
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Implement config loader**

Create `src/config.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: add config loader with YAML + env support"
```

---

## Chunk 2: Collector — Base + RSS + Dedup

### Task 3: Article dataclass and Source interface

**Files:**
- Create: `src/collector/__init__.py`
- Create: `src/collector/base.py`
- Create: `tests/collector/__init__.py`
- Create: `tests/collector/test_base.py`

- [ ] **Step 1: Write failing test for Article dataclass**

Create `tests/collector/__init__.py` (empty) and `tests/collector/test_base.py`:

```python
from datetime import datetime, timezone

from src.collector.base import Article


def test_article_creation():
    article = Article(
        title="Test Article",
        source="Test Source",
        url="https://example.com/article",
        published_at=datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc),
        summary="This is a test summary.",
    )
    assert article.title == "Test Article"
    assert article.source == "Test Source"
    assert article.url == "https://example.com/article"


def test_article_summary_truncation():
    long_summary = "A" * 600
    article = Article(
        title="Test",
        source="Test",
        url="https://example.com",
        published_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
        summary=long_summary,
    )
    assert len(article.summary) <= 500


def test_article_is_immutable():
    article = Article(
        title="Test",
        source="Test",
        url="https://example.com",
        published_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
        summary="Summary",
    )
    try:
        article.title = "Changed"
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collector/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement Article and Source ABC**

Create `src/collector/__init__.py` (empty) and `src/collector/base.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

MAX_SUMMARY_LENGTH = 500


@dataclass(frozen=True)
class Article:
    title: str
    source: str
    url: str
    published_at: datetime
    summary: str
    category: str = ""

    def __post_init__(self) -> None:
        if len(self.summary) > MAX_SUMMARY_LENGTH:
            object.__setattr__(
                self, "summary", self.summary[:MAX_SUMMARY_LENGTH]
            )


class Source(ABC):
    """Base class for all news sources."""

    def __init__(self, name: str, category: str, timeout: int = 15) -> None:
        self.name = name
        self.category = category
        self.timeout = timeout

    @abstractmethod
    def fetch(self) -> list[Article]:
        """Fetch articles from this source. Returns empty list on failure."""
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/collector/test_base.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/collector/__init__.py src/collector/base.py tests/collector/__init__.py tests/collector/test_base.py
git commit -m "feat: add Article dataclass and Source ABC"
```

---

### Task 4: RSS Collector

**Files:**
- Create: `src/collector/rss.py`
- Create: `tests/collector/test_rss.py`

- [ ] **Step 1: Write failing test for RSS collector**

Create `tests/collector/test_rss.py`:

```python
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.collector.rss import RSSSource


SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article One</title>
      <link>https://example.com/1</link>
      <pubDate>Thu, 12 Mar 2026 10:00:00 GMT</pubDate>
      <description>First article summary.</description>
    </item>
    <item>
      <title>Article Two</title>
      <link>https://example.com/2</link>
      <pubDate>Thu, 12 Mar 2026 11:00:00 GMT</pubDate>
      <description>Second article summary.</description>
    </item>
  </channel>
</rss>"""


@patch("src.collector.rss.requests.get")
def test_rss_source_fetches_articles(mock_get: MagicMock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = SAMPLE_FEED.encode()
    mock_get.return_value = mock_response

    source = RSSSource(
        name="Test Feed",
        category="tech",
        url="https://example.com/feed",
    )
    articles = source.fetch()

    assert len(articles) == 2
    assert articles[0].title == "Article One"
    assert articles[0].source == "Test Feed"
    assert articles[0].url == "https://example.com/1"
    assert articles[0].summary == "First article summary."


@patch("src.collector.rss.requests.get")
def test_rss_source_returns_empty_on_error(mock_get: MagicMock):
    mock_get.side_effect = Exception("Network error")

    source = RSSSource(
        name="Test Feed",
        category="tech",
        url="https://example.com/feed",
    )
    articles = source.fetch()

    assert articles == []


@patch("src.collector.rss.requests.get")
def test_rss_source_filters_old_articles(mock_get: MagicMock):
    old_feed = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Old Article</title>
          <link>https://example.com/old</link>
          <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
          <description>Very old.</description>
        </item>
      </channel>
    </rss>"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = old_feed.encode()
    mock_get.return_value = mock_response

    source = RSSSource(
        name="Test Feed",
        category="tech",
        url="https://example.com/feed",
    )
    articles = source.fetch()

    assert articles == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collector/test_rss.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement RSS collector**

Create `src/collector/rss.py`:

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import requests

from src.collector.base import Article, Source

logger = logging.getLogger(__name__)

HOURS_24 = timedelta(hours=24)


class RSSSource(Source):
    """Generic RSS feed collector."""

    def __init__(
        self, name: str, category: str, url: str, timeout: int = 15
    ) -> None:
        super().__init__(name=name, category=category, timeout=timeout)
        self.url = url

    def fetch(self) -> list[Article]:
        try:
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
        except Exception:
            logger.warning("Failed to fetch RSS feed: %s", self.name)
            return []

        feed = feedparser.parse(response.content)
        now = datetime.now(timezone.utc)
        cutoff = now - HOURS_24
        articles: list[Article] = []

        for entry in feed.entries:
            published = self._parse_date(entry)
            if published is None or published < cutoff:
                continue

            summary = entry.get("summary", entry.get("description", ""))
            articles.append(
                Article(
                    title=entry.get("title", ""),
                    source=self.name,
                    url=entry.get("link", ""),
                    published_at=published,
                    summary=summary,
                    category=self.category,
                )
            )

        logger.info("Fetched %d articles from %s", len(articles), self.name)
        return articles

    @staticmethod
    def _parse_date(entry: dict) -> datetime | None:
        """Try to parse published date from feed entry."""
        for date_field in ("published", "updated", "created"):
            raw = entry.get(date_field)
            if raw:
                try:
                    return parsedate_to_datetime(raw)
                except (ValueError, TypeError):
                    pass
            parsed_field = entry.get(f"{date_field}_parsed")
            if parsed_field:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(
                        mktime(parsed_field), tz=timezone.utc
                    )
                except (ValueError, TypeError, OverflowError):
                    pass
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/collector/test_rss.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/collector/rss.py tests/collector/test_rss.py
git commit -m "feat: add RSS collector with date filtering"
```

---

### Task 5: Deduplication

**Files:**
- Create: `src/collector/dedup.py`
- Create: `tests/collector/test_dedup.py`

- [ ] **Step 1: Write failing test for deduplication**

Create `tests/collector/test_dedup.py`:

```python
from datetime import datetime, timezone

from src.collector.base import Article
from src.collector.dedup import deduplicate


def _make_article(title: str, url: str = "https://example.com") -> Article:
    return Article(
        title=title,
        source="Test",
        url=url,
        published_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
        summary="Summary",
    )


def test_dedup_removes_exact_url_duplicates():
    articles = [
        _make_article("Article A", "https://example.com/1"),
        _make_article("Article B", "https://example.com/1"),
    ]
    result = deduplicate(articles)
    assert len(result) == 1


def test_dedup_removes_similar_titles():
    articles = [
        _make_article("OpenAI announces GPT-5", "https://a.com/1"),
        _make_article("OpenAI announces GPT 5 model", "https://b.com/2"),
    ]
    result = deduplicate(articles)
    assert len(result) == 1


def test_dedup_keeps_distinct_articles():
    articles = [
        _make_article("Python 3.13 released", "https://a.com/1"),
        _make_article("Rust 2.0 announced", "https://b.com/2"),
    ]
    result = deduplicate(articles)
    assert len(result) == 2


def test_dedup_empty_list():
    assert deduplicate([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collector/test_dedup.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement deduplication**

Create `src/collector/dedup.py`:

```python
from __future__ import annotations

from rapidfuzz.fuzz import token_sort_ratio

from src.collector.base import Article

SIMILARITY_THRESHOLD = 80


def deduplicate(articles: list[Article]) -> list[Article]:
    """Remove duplicate articles by URL and fuzzy title matching."""
    seen_urls: set[str] = set()
    unique_titles: list[str] = []
    result: list[Article] = []

    for article in articles:
        if article.url in seen_urls:
            continue

        is_similar = any(
            token_sort_ratio(article.title, existing) >= SIMILARITY_THRESHOLD
            for existing in unique_titles
        )
        if is_similar:
            continue

        seen_urls.add(article.url)
        unique_titles.append(article.title)
        result.append(article)

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/collector/test_dedup.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/collector/dedup.py tests/collector/test_dedup.py
git commit -m "feat: add article deduplication with URL + fuzzy title match"
```

---

## Chunk 3: Collector — HN + GitHub Trending

### Task 6: Hacker News collector (Algolia API)

**Files:**
- Create: `src/collector/hackernews.py`
- Create: `tests/collector/test_hackernews.py`

- [ ] **Step 1: Write failing test for HN collector**

Create `tests/collector/test_hackernews.py`:

```python
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.collector.hackernews import HackerNewsSource


SAMPLE_RESPONSE = {
    "hits": [
        {
            "title": "Show HN: My new project",
            "url": "https://example.com/project",
            "created_at_i": 1741770000,
            "points": 150,
            "objectID": "12345",
        },
        {
            "title": "Ask HN: Best practices",
            "url": "",
            "created_at_i": 1741770000,
            "points": 80,
            "objectID": "12346",
        },
    ]
}


@patch("src.collector.hackernews.requests.get")
def test_hn_fetches_articles(mock_get: MagicMock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_get.return_value = mock_response

    source = HackerNewsSource(name="Hacker News", category="tech")
    articles = source.fetch()

    assert len(articles) == 2
    assert articles[0].title == "Show HN: My new project"
    assert articles[0].source == "Hacker News"
    # Article without URL should use HN discussion link
    assert "news.ycombinator.com" in articles[1].url


@patch("src.collector.hackernews.requests.get")
def test_hn_returns_empty_on_error(mock_get: MagicMock):
    mock_get.side_effect = Exception("API error")

    source = HackerNewsSource(name="Hacker News", category="tech")
    articles = source.fetch()

    assert articles == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collector/test_hackernews.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement HN collector**

Create `src/collector/hackernews.py`:

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from src.collector.base import Article, Source

logger = logging.getLogger(__name__)

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://news.ycombinator.com/item?id="


class HackerNewsSource(Source):
    """Hacker News collector via Algolia API."""

    def __init__(
        self,
        name: str = "Hacker News",
        category: str = "tech",
        min_points: int = 50,
        timeout: int = 15,
    ) -> None:
        super().__init__(name=name, category=category, timeout=timeout)
        self.min_points = min_points

    def fetch(self) -> list[Article]:
        try:
            response = requests.get(
                ALGOLIA_URL,
                params={
                    "tags": "story",
                    "numericFilters": f"points>{self.min_points}",
                    "hitsPerPage": 30,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            logger.warning("Failed to fetch Hacker News")
            return []

        articles: list[Article] = []
        for hit in data.get("hits", []):
            url = hit.get("url") or f"{HN_ITEM_URL}{hit['objectID']}"
            published = datetime.fromtimestamp(
                hit["created_at_i"], tz=timezone.utc
            )
            articles.append(
                Article(
                    title=hit.get("title", ""),
                    source=self.name,
                    url=url,
                    published_at=published,
                    summary=f"Points: {hit.get('points', 0)}",
                    category=self.category,
                )
            )

        logger.info("Fetched %d articles from Hacker News", len(articles))
        return articles
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/collector/test_hackernews.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/collector/hackernews.py tests/collector/test_hackernews.py
git commit -m "feat: add Hacker News collector via Algolia API"
```

---

### Task 7: GitHub Trending scraper

**Files:**
- Create: `src/collector/github_trending.py`
- Create: `tests/collector/test_github_trending.py`

- [ ] **Step 1: Write failing test for GitHub Trending**

Create `tests/collector/test_github_trending.py`:

```python
from unittest.mock import patch, MagicMock

from src.collector.github_trending import GitHubTrendingSource


SAMPLE_HTML = """
<html><body>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/user/repo-one">user / repo-one</a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">A cool project description</p>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/org/repo-two">org / repo-two</a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">Another project</p>
</article>
</body></html>
"""


@patch("src.collector.github_trending.requests.get")
def test_github_trending_fetches_repos(mock_get: MagicMock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_HTML
    mock_get.return_value = mock_response

    source = GitHubTrendingSource(name="GitHub Trending", category="tech")
    articles = source.fetch()

    assert len(articles) == 2
    assert "repo-one" in articles[0].title
    assert articles[0].url == "https://github.com/user/repo-one"
    assert articles[0].summary == "A cool project description"


@patch("src.collector.github_trending.requests.get")
def test_github_trending_returns_empty_on_error(mock_get: MagicMock):
    mock_get.side_effect = Exception("Scraping failed")

    source = GitHubTrendingSource(name="GitHub Trending", category="tech")
    articles = source.fetch()

    assert articles == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collector/test_github_trending.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement GitHub Trending scraper**

Create `src/collector/github_trending.py`:

```python
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import requests

from src.collector.base import Article, Source

logger = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending"
GITHUB_BASE = "https://github.com"


class GitHubTrendingSource(Source):
    """GitHub Trending page scraper. Fragile — fails gracefully."""

    def __init__(
        self,
        name: str = "GitHub Trending",
        category: str = "tech",
        timeout: int = 15,
    ) -> None:
        super().__init__(name=name, category=category, timeout=timeout)

    def fetch(self) -> list[Article]:
        try:
            response = requests.get(
                TRENDING_URL,
                timeout=self.timeout,
                headers={"Accept": "text/html"},
            )
            response.raise_for_status()
        except Exception:
            logger.warning("Failed to fetch GitHub Trending")
            return []

        return self._parse_html(response.text)

    def _parse_html(self, html: str) -> list[Article]:
        articles: list[Article] = []
        now = datetime.now(timezone.utc)

        repo_pattern = re.compile(
            r'<article class="Box-row">.*?'
            r'<a href="(/[^"]+)"[^>]*>([^<]*)</a>.*?'
            r'(?:<p class="[^"]*color-fg-muted[^"]*"[^>]*>([^<]*)</p>)?',
            re.DOTALL,
        )

        for match in repo_pattern.finditer(html):
            path = match.group(1).strip()
            name = match.group(2).strip()
            description = (match.group(3) or "").strip()

            # Clean up name (remove extra whitespace)
            name = re.sub(r"\s+", " ", name).strip()

            articles.append(
                Article(
                    title=f"Trending: {name}",
                    source=self.name,
                    url=f"{GITHUB_BASE}{path}",
                    published_at=now,
                    summary=description,
                    category=self.category,
                )
            )

        logger.info(
            "Fetched %d repos from GitHub Trending", len(articles)
        )
        return articles
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/collector/test_github_trending.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/collector/github_trending.py tests/collector/test_github_trending.py
git commit -m "feat: add GitHub Trending scraper"
```

---

## Chunk 4: Weather

### Task 8: OpenWeatherMap client

**Files:**
- Create: `src/weather/__init__.py`
- Create: `src/weather/forecast.py`
- Create: `tests/weather/__init__.py`
- Create: `tests/weather/test_forecast.py`

- [ ] **Step 1: Write failing test for weather client**

Create `tests/weather/__init__.py` (empty) and `tests/weather/test_forecast.py`:

```python
from unittest.mock import patch, MagicMock

from src.weather.forecast import fetch_weather, WeatherData


SAMPLE_RESPONSE = {
    "weather": [{"description": "ciel degagé", "id": 800}],
    "main": {"temp": 12.5, "temp_min": 8.0, "temp_max": 16.0},
    "name": "Fontenay-sous-Bois",
}


@patch("src.weather.forecast.requests.get")
def test_fetch_weather_returns_data(mock_get: MagicMock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_get.return_value = mock_response

    result = fetch_weather(
        lat=48.8566, lon=2.4739, api_key="test-key"
    )

    assert isinstance(result, WeatherData)
    assert result.city == "Fontenay-sous-Bois"
    assert result.temp_current == 12.5
    assert result.temp_min == 8.0
    assert result.temp_max == 16.0
    assert result.description == "ciel degagé"


@patch("src.weather.forecast.requests.get")
def test_fetch_weather_returns_none_on_error(mock_get: MagicMock):
    mock_get.side_effect = Exception("API down")

    result = fetch_weather(lat=0.0, lon=0.0, api_key="test")

    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/weather/test_forecast.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement weather client**

Create `src/weather/__init__.py` (empty) and `src/weather/forecast.py`:

```python
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


@dataclass(frozen=True)
class WeatherData:
    city: str
    description: str
    temp_current: float
    temp_min: float
    temp_max: float


def fetch_weather(
    lat: float, lon: float, api_key: str, timeout: int = 15
) -> WeatherData | None:
    """Fetch current weather from OpenWeatherMap. Returns None on failure."""
    try:
        response = requests.get(
            OWM_URL,
            params={
                "lat": lat,
                "lon": lon,
                "appid": api_key,
                "units": "metric",
                "lang": "fr",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        logger.warning("Failed to fetch weather data")
        return None

    return WeatherData(
        city=data.get("name", ""),
        description=data["weather"][0]["description"],
        temp_current=data["main"]["temp"],
        temp_min=data["main"]["temp_min"],
        temp_max=data["main"]["temp_max"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/weather/test_forecast.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/weather/__init__.py src/weather/forecast.py tests/weather/__init__.py tests/weather/test_forecast.py
git commit -m "feat: add OpenWeatherMap client"
```

---

## Chunk 5: Editor — Briefing + SSML

### Task 9: Briefing generator (Claude API)

**Files:**
- Create: `src/editor/__init__.py`
- Create: `src/editor/briefing.py`
- Create: `tests/editor/__init__.py`
- Create: `tests/editor/test_briefing.py`

- [ ] **Step 1: Write failing test for briefing generator**

Create `tests/editor/__init__.py` (empty) and `tests/editor/test_briefing.py`:

```python
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.collector.base import Article
from src.weather.forecast import WeatherData
from src.editor.briefing import generate_briefing, BriefingSegment


def _make_articles(count: int, category: str = "tech") -> list[Article]:
    return [
        Article(
            title=f"Article {i}",
            source=f"Source {i}",
            url=f"https://example.com/{i}",
            published_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
            summary=f"Summary of article {i}.",
        )
        for i in range(count)
    ]


MOCK_RESPONSE_SEGMENTS = [
    {"type": "intro", "text": "Bonjour, c'est mercredi 12 mars 2026."},
    {"type": "weather", "text": "Côté météo, ciel dégagé, 12 degrés."},
    {"type": "news", "text": "Dans l'essentiel aujourd'hui..."},
    {"type": "news", "text": "Côté tech maintenant..."},
    {"type": "outro", "text": "Bonne journée et à demain."},
]


@patch("src.editor.briefing.anthropic.Anthropic")
def test_generate_briefing_returns_segments(mock_anthropic_cls: MagicMock):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text=json.dumps({"segments": MOCK_RESPONSE_SEGMENTS}))
    ]
    mock_client.messages.create.return_value = mock_message

    weather = WeatherData(
        city="Fontenay-sous-Bois",
        description="ciel dégagé",
        temp_current=12.0,
        temp_min=8.0,
        temp_max=16.0,
    )

    articles = _make_articles(15)
    segments = generate_briefing(
        articles=articles,
        weather=weather,
        api_key="test-key",
        model="claude-haiku-4-5-20251001",
        max_general_news=5,
        max_tech_news=10,
    )

    assert len(segments) == 5
    assert segments[0].type == "intro"
    assert segments[-1].type == "outro"
    mock_client.messages.create.assert_called_once()


@patch("src.editor.briefing.anthropic.Anthropic")
def test_generate_briefing_without_weather(mock_anthropic_cls: MagicMock):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    segments_no_weather = [
        {"type": "intro", "text": "Bonjour."},
        {"type": "news", "text": "Les news..."},
        {"type": "outro", "text": "À demain."},
    ]
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text=json.dumps({"segments": segments_no_weather}))
    ]
    mock_client.messages.create.return_value = mock_message

    articles = _make_articles(10)
    segments = generate_briefing(
        articles=articles,
        weather=None,
        api_key="test-key",
        model="claude-haiku-4-5-20251001",
        max_general_news=5,
        max_tech_news=10,
    )

    assert len(segments) == 3
    assert all(s.type != "weather" for s in segments)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/editor/test_briefing.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement briefing generator**

Create `src/editor/__init__.py` (empty) and `src/editor/briefing.py`:

```python
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from src.collector.base import Article
from src.weather.forecast import WeatherData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un présentateur de briefing matinal francophone. Ton ton est informé, accessible et naturel.

Tu reçois une liste d'articles et des données météo. Tu dois produire un briefing audio structuré en segments JSON.

RÈGLES :
- Phrases courtes, adaptées à l'oral (pas de lecture)
- Pas de jargon non expliqué
- Pas d'URLs
- Transitions naturelles entre les sujets
- Le briefing doit durer environ 7-8 minutes à la lecture

FORMAT DE SORTIE (JSON strict) :
{
  "segments": [
    {"type": "intro", "text": "Bonjour, c'est [jour] [date], voici votre briefing du matin."},
    {"type": "weather", "text": "Côté météo à [ville], [conditions]."},
    {"type": "news", "text": "Dans l'essentiel aujourd'hui... [3-5 news actu générale avec transitions]"},
    {"type": "news", "text": "Côté tech maintenant... [10 news tech avec contexte et analyse]"},
    {"type": "outro", "text": "Bonne journée, et à demain."}
  ]
}

IMPORTANT : Retourne UNIQUEMENT du JSON valide, sans commentaire ni markdown."""

MAX_RETRIES = 2


@dataclass(frozen=True)
class BriefingSegment:
    type: str  # "intro", "weather", "news", "outro"
    text: str


def generate_briefing(
    articles: list[Article],
    weather: WeatherData | None,
    api_key: str,
    model: str,
    max_general_news: int,
    max_tech_news: int,
) -> list[BriefingSegment]:
    """Generate editorialized briefing segments via Claude API."""
    client = anthropic.Anthropic(api_key=api_key)

    user_content = _build_user_prompt(
        articles, weather, max_general_news, max_tech_news
    )

    for attempt in range(MAX_RETRIES):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = message.content[0].text
            data = json.loads(raw)
            return [
                BriefingSegment(type=s["type"], text=s["text"])
                for s in data["segments"]
            ]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(
                "Briefing parse error (attempt %d): %s", attempt + 1, e
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
        except anthropic.APIError as e:
            logger.warning(
                "Claude API error (attempt %d): %s", attempt + 1, e
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    raise RuntimeError("Failed to generate briefing after retries")


def _build_user_prompt(
    articles: list[Article],
    weather: WeatherData | None,
    max_general_news: int,
    max_tech_news: int,
) -> str:
    now = datetime.now(ZoneInfo("Europe/Paris"))
    parts = [
        f"Date : {now.strftime('%A %d %B %Y')}",
        "",
    ]

    if weather:
        parts.append("MÉTÉO :")
        parts.append(
            f"  Ville : {weather.city}"
        )
        parts.append(
            f"  Conditions : {weather.description}"
        )
        parts.append(
            f"  Température : {weather.temp_current:.0f}°C "
            f"(min {weather.temp_min:.0f}°C, max {weather.temp_max:.0f}°C)"
        )
        parts.append("")
    else:
        parts.append("MÉTÉO : non disponible (omets le segment météo)")
        parts.append("")

    parts.append(
        f"ARTICLES (sélectionne {max_general_news} actu générale "
        f"+ {max_tech_news} tech) :"
    )
    parts.append("")

    for i, article in enumerate(articles, 1):
        parts.append(
            f"{i}. [{article.category}] [{article.source}] {article.title}"
        )
        parts.append(f"   Date : {article.published_at.isoformat()}")
        parts.append(f"   Résumé : {article.summary}")
        parts.append("")

    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/editor/test_briefing.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/editor/__init__.py src/editor/briefing.py tests/editor/__init__.py tests/editor/test_briefing.py
git commit -m "feat: add Claude-powered briefing generator"
```

---

### Task 10: SSML template builder

**Files:**
- Create: `src/editor/ssml.py`
- Create: `tests/editor/test_ssml.py`

- [ ] **Step 1: Write failing test for SSML builder**

Create `tests/editor/test_ssml.py`:

```python
from src.editor.briefing import BriefingSegment
from src.editor.ssml import build_ssml


def test_build_ssml_wraps_in_speak_tag():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="outro", text="À demain."),
    ]
    ssml = build_ssml(segments)
    assert ssml.startswith("<speak>")
    assert ssml.endswith("</speak>")


def test_build_ssml_adds_breaks_between_segments():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="weather", text="Il fait beau."),
        BriefingSegment(type="outro", text="À demain."),
    ]
    ssml = build_ssml(segments)
    assert '<break time="800ms"/>' in ssml


def test_build_ssml_adds_long_break_before_tech():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="news", text="L'essentiel."),
        BriefingSegment(type="news", text="Côté tech."),
        BriefingSegment(type="outro", text="À demain."),
    ]
    ssml = build_ssml(segments)
    assert '<break time="1200ms"/>' in ssml


def test_build_ssml_applies_prosody():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
    ]
    ssml = build_ssml(segments)
    assert '<prosody rate="95%">' in ssml


def test_build_ssml_escapes_special_chars():
    segments = [
        BriefingSegment(type="news", text='L\'IA & le "cloud" <3'),
    ]
    ssml = build_ssml(segments)
    # Ampersand should be escaped
    assert "&amp;" in ssml
    assert "<3" not in ssml  # < should be escaped
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/editor/test_ssml.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement SSML builder**

Create `src/editor/ssml.py`:

```python
from __future__ import annotations

import html

from src.editor.briefing import BriefingSegment

BREAK_SHORT = '<break time="800ms"/>'
BREAK_LONG = '<break time="1200ms"/>'


def build_ssml(segments: list[BriefingSegment]) -> str:
    """Build SSML from briefing segments with pauses and prosody."""
    parts: list[str] = ['<speak><prosody rate="95%">']

    news_count = 0
    for i, segment in enumerate(segments):
        if i > 0:
            # Long break between the two news blocks (general -> tech)
            if segment.type == "news" and news_count == 1:
                parts.append(BREAK_LONG)
            else:
                parts.append(BREAK_SHORT)

        escaped_text = html.escape(segment.text, quote=False)
        parts.append(escaped_text)

        if segment.type == "news":
            news_count += 1

    parts.append("</prosody></speak>")
    return "".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/editor/test_ssml.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/editor/ssml.py tests/editor/test_ssml.py
git commit -m "feat: add SSML template builder with breaks and prosody"
```

---

## Chunk 6: Audio — Polly TTS

### Task 11: TTS interface and Polly implementation

**Files:**
- Create: `src/audio/__init__.py`
- Create: `src/audio/base.py`
- Create: `src/audio/polly.py`
- Create: `tests/audio/__init__.py`
- Create: `tests/audio/test_polly.py`

- [ ] **Step 1: Write failing test for SSML chunking + Polly**

Create `tests/audio/__init__.py` (empty) and `tests/audio/test_polly.py`:

```python
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from src.audio.polly import PollyTTS, chunk_ssml


def test_chunk_ssml_short_text():
    ssml = "<speak>Short text.</speak>"
    chunks = chunk_ssml(ssml, max_chars=3000)
    assert len(chunks) == 1
    assert chunks[0] == "<speak>Short text.</speak>"


def test_chunk_ssml_long_text():
    # Build SSML longer than 3000 chars
    sentence = "Ceci est une phrase de test. "
    body = sentence * 150  # ~4200 chars
    ssml = f"<speak>{body}</speak>"
    chunks = chunk_ssml(ssml, max_chars=3000)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.startswith("<speak>")
        assert chunk.endswith("</speak>")
        assert len(chunk) <= 3000


def test_chunk_ssml_preserves_all_text():
    sentence = "Phrase numero {}. "
    body = "".join(sentence.format(i) for i in range(100))
    ssml = f"<speak>{body}</speak>"
    chunks = chunk_ssml(ssml, max_chars=3000)
    recombined = "".join(
        c.replace("<speak>", "").replace("</speak>", "")
        for c in chunks
    )
    assert recombined == body


@patch("src.audio.polly.AudioSegment")
@patch("src.audio.polly.boto3.client")
def test_polly_synthesize_creates_mp3(
    mock_boto_client: MagicMock, mock_audio_segment: MagicMock, tmp_path: Path
):
    mock_polly = MagicMock()
    mock_boto_client.return_value = mock_polly
    mock_polly.synthesize_speech.return_value = {
        "AudioStream": MagicMock(read=MagicMock(return_value=b"fake-audio"))
    }

    mock_segment = MagicMock()
    mock_audio_segment.from_mp3.return_value = mock_segment
    # __add__ returns self for concatenation
    mock_segment.__add__ = MagicMock(return_value=mock_segment)

    tts = PollyTTS(voice="Lea", output_dir=str(tmp_path))
    ssml = "<speak>Bonjour.</speak>"
    result = tts.synthesize(ssml, "test-briefing")

    assert result.suffix == ".mp3"
    mock_polly.synthesize_speech.assert_called_once()
    mock_segment.export.assert_called_once()


@patch("src.audio.polly.AudioSegment")
@patch("src.audio.polly.boto3.client")
def test_polly_retries_on_failure(
    mock_boto_client: MagicMock, mock_audio_segment: MagicMock, tmp_path: Path
):
    mock_polly = MagicMock()
    mock_boto_client.return_value = mock_polly
    # First call fails, second succeeds
    mock_polly.synthesize_speech.side_effect = [
        Exception("Transient error"),
        {"AudioStream": MagicMock(read=MagicMock(return_value=b"audio"))},
    ]

    mock_segment = MagicMock()
    mock_audio_segment.from_mp3.return_value = mock_segment

    tts = PollyTTS(voice="Lea", output_dir=str(tmp_path))
    result = tts.synthesize("<speak>Test.</speak>", "retry-test")

    assert mock_polly.synthesize_speech.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/audio/test_polly.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement TTS base and Polly**

Create `src/audio/__init__.py` (empty), `src/audio/base.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSEngine(ABC):
    """Base class for text-to-speech engines."""

    @abstractmethod
    def synthesize(self, ssml: str, filename: str) -> Path:
        """Convert SSML text to audio file. Returns path to output file."""
        ...
```

Create `src/audio/polly.py`:

```python
from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

import boto3
from pydub import AudioSegment

from src.audio.base import TTSEngine

logger = logging.getLogger(__name__)

MAX_SSML_CHARS = 3000
MAX_RETRIES = 2


def chunk_ssml(ssml: str, max_chars: int = MAX_SSML_CHARS) -> list[str]:
    """Split SSML into chunks that fit within Polly's character limit.

    Strips outer <speak> tags, splits the inner plain text on sentence
    boundaries, and re-wraps each chunk in <speak></speak>.

    Note: The SSML template builder (ssml.py) produces segments with
    inline tags (<break/>, <prosody>). This function splits on text
    boundaries only, never inside an XML tag, because it operates on
    the flattened text between <speak> tags.
    """
    # Remove outer <speak> and optional <prosody> wrapper
    inner = ssml
    if inner.startswith("<speak>"):
        inner = inner[7:]
    if inner.endswith("</speak>"):
        inner = inner[:-8]

    overhead = len("<speak></speak>")
    max_inner = max_chars - overhead

    if len(inner) <= max_inner:
        return [f"<speak>{inner}</speak>"]

    chunks: list[str] = []
    remaining = inner

    while remaining:
        if len(remaining) <= max_inner:
            chunks.append(f"<speak>{remaining}</speak>")
            break

        # Find last sentence boundary within limit
        split_at = remaining[:max_inner].rfind(". ")
        if split_at != -1:
            # Include the period and space in this chunk
            split_at += 2
        else:
            # No sentence boundary — split at last space
            split_at = remaining[:max_inner].rfind(" ")
            if split_at != -1:
                split_at += 1  # Include the space
            else:
                # No space — hard split
                split_at = max_inner

        chunk_text = remaining[:split_at]
        remaining = remaining[split_at:]
        chunks.append(f"<speak>{chunk_text}</speak>")

    return chunks


class PollyTTS(TTSEngine):
    """Amazon Polly Neural TTS implementation."""

    def __init__(self, voice: str = "Lea", output_dir: str = "output/") -> None:
        self.voice = voice
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, ssml: str, filename: str) -> Path:
        """Convert SSML to MP3 via Amazon Polly. Handles chunking."""
        client = boto3.client("polly")
        chunks = chunk_ssml(ssml)

        logger.info(
            "Synthesizing %d SSML chunk(s) with voice %s",
            len(chunks),
            self.voice,
        )

        audio_segments: list[AudioSegment] = []

        for i, chunk in enumerate(chunks):
            audio_data = self._synthesize_chunk(client, chunk)
            segment = AudioSegment.from_mp3(BytesIO(audio_data))
            audio_segments.append(segment)
            logger.info("Chunk %d/%d synthesized", i + 1, len(chunks))

        # Concatenate all chunks
        combined = audio_segments[0]
        for segment in audio_segments[1:]:
            combined = combined + segment

        output_path = self.output_dir / f"{filename}.mp3"
        combined.export(str(output_path), format="mp3")
        logger.info("Audio saved to %s", output_path)
        return output_path

    def _synthesize_chunk(self, client: object, ssml: str) -> bytes:
        """Synthesize a single SSML chunk with retry + exponential backoff."""
        import time

        for i in range(MAX_RETRIES):
            try:
                response = client.synthesize_speech(
                    Text=ssml,
                    TextType="ssml",
                    OutputFormat="mp3",
                    VoiceId=self.voice,
                    Engine="neural",
                )
                return response["AudioStream"].read()
            except Exception as e:
                logger.warning(
                    "Polly synthesis error (attempt %d): %s", i + 1, e
                )
                if i < MAX_RETRIES - 1:
                    time.sleep(2 ** i)
                else:
                    raise
        raise RuntimeError("Polly synthesis failed")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/audio/test_polly.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/audio/__init__.py src/audio/base.py src/audio/polly.py tests/audio/__init__.py tests/audio/test_polly.py
git commit -m "feat: add Polly TTS with SSML chunking and concatenation"
```

---

## Chunk 7: Publisher + Orchestrator

### Task 12: Home Assistant publisher

**Files:**
- Create: `src/publisher/__init__.py`
- Create: `src/publisher/homeassistant.py`
- Create: `tests/publisher/__init__.py`
- Create: `tests/publisher/test_homeassistant.py`

- [ ] **Step 1: Write failing test for HA publisher**

Create `tests/publisher/__init__.py` (empty) and `tests/publisher/test_homeassistant.py`:

```python
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.publisher.homeassistant import HomeAssistantPublisher


def test_publish_copies_file(tmp_path: Path):
    # Create source MP3
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_mp3 = source_dir / "briefing-2026-03-12.mp3"
    source_mp3.write_bytes(b"fake mp3 data")

    # Target dir
    target_dir = tmp_path / "ha_media"
    target_dir.mkdir()

    publisher = HomeAssistantPublisher(
        ha_media_dir=str(target_dir),
        ha_url="http://localhost:8123",
        ha_token="test-token",
        media_player_entity="media_player.echo",
    )

    publisher.publish(source_mp3)

    target_file = target_dir / "briefing-2026-03-12.mp3"
    assert target_file.exists()
    assert target_file.read_bytes() == b"fake mp3 data"


@patch("src.publisher.homeassistant.requests.post")
def test_notify_failure_calls_ha_api(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=200)

    publisher = HomeAssistantPublisher(
        ha_media_dir="/tmp",
        ha_url="http://localhost:8123",
        ha_token="test-token",
        media_player_entity="media_player.echo",
    )

    publisher.notify_failure("Pipeline failed: API error")

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "notify" in call_kwargs[0][0]


def test_cleanup_old_files(tmp_path: Path):
    import time

    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create old file (fake old mtime)
    old_file = media_dir / "briefing-2026-03-01.mp3"
    old_file.write_bytes(b"old")

    # Create recent file
    new_file = media_dir / "briefing-2026-03-12.mp3"
    new_file.write_bytes(b"new")

    publisher = HomeAssistantPublisher(
        ha_media_dir=str(media_dir),
        ha_url="http://localhost:8123",
        ha_token="test-token",
        media_player_entity="media_player.echo",
    )

    # Set old file mtime to 10 days ago
    import os
    old_time = time.time() - (10 * 86400)
    os.utime(old_file, (old_time, old_time))

    publisher.cleanup(retention_days=7)

    assert not old_file.exists()
    assert new_file.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/publisher/test_homeassistant.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement HA publisher**

Create `src/publisher/__init__.py` (empty) and `src/publisher/homeassistant.py`:

```python
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class HomeAssistantPublisher:
    """Publishes MP3 to Home Assistant and manages cleanup."""

    def __init__(
        self,
        ha_media_dir: str,
        ha_url: str,
        ha_token: str,
        media_player_entity: str,
    ) -> None:
        self.ha_media_dir = Path(ha_media_dir)
        self.ha_url = ha_url.rstrip("/")
        self.ha_token = ha_token
        self.media_player_entity = media_player_entity

    def publish(self, mp3_path: Path) -> Path:
        """Copy MP3 to HA media directory."""
        self.ha_media_dir.mkdir(parents=True, exist_ok=True)
        target = self.ha_media_dir / mp3_path.name
        shutil.copy2(mp3_path, target)
        logger.info("Published %s to %s", mp3_path.name, target)
        return target

    def notify_failure(self, message: str) -> None:
        """Send a persistent notification via HA API."""
        url = f"{self.ha_url}/api/services/notify/persistent_notification"
        try:
            requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "title": "Veille Techno - Erreur",
                    "message": message,
                },
                timeout=10,
            )
            logger.info("Failure notification sent to HA")
        except Exception:
            logger.error("Failed to send notification to HA")

    def cleanup(self, retention_days: int = 7) -> None:
        """Remove MP3 files older than retention_days."""
        if not self.ha_media_dir.exists():
            return

        cutoff = time.time() - (retention_days * 86400)

        for mp3_file in self.ha_media_dir.glob("briefing-*.mp3"):
            if mp3_file.stat().st_mtime < cutoff:
                mp3_file.unlink()
                logger.info("Cleaned up old file: %s", mp3_file.name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/publisher/test_homeassistant.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/publisher/__init__.py src/publisher/homeassistant.py tests/publisher/__init__.py tests/publisher/test_homeassistant.py
git commit -m "feat: add Home Assistant publisher with cleanup"
```

---

### Task 13: Orchestrator (main pipeline)

**Files:**
- Create: `src/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test for orchestrator**

Create `tests/test_orchestrator.py`:

```python
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.orchestrator import run_pipeline


@patch("src.orchestrator.HomeAssistantPublisher")
@patch("src.orchestrator.PollyTTS")
@patch("src.orchestrator.generate_briefing")
@patch("src.orchestrator.build_ssml")
@patch("src.orchestrator.fetch_weather")
@patch("src.orchestrator.collect_all")
@patch("src.orchestrator.load_config")
def test_pipeline_runs_end_to_end(
    mock_load_config: MagicMock,
    mock_collect: MagicMock,
    mock_weather: MagicMock,
    mock_ssml: MagicMock,
    mock_briefing: MagicMock,
    mock_polly_cls: MagicMock,
    mock_publisher_cls: MagicMock,
    tmp_path: Path,
):
    # Setup mocks
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
        editor=EditorConfig(
            model="claude-haiku-4-5-20251001",
            max_general_news=5,
            max_tech_news=10,
        ),
        audio=AudioConfig(
            engine="polly", voice="Lea",
            output_dir=str(tmp_path), retention_days=7,
        ),
        publisher=PublisherConfig(
            ha_media_dir=str(tmp_path / "ha"),
            media_player_entity="media_player.echo",
        ),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(
            anthropic_api_key="test",
            owm_api_key="test",
            ha_url="http://localhost:8123",
            ha_token="test",
        ),
    )

    mock_collect.return_value = [
        Article(
            title=f"Article {i}",
            source="Test",
            url=f"https://example.com/{i}",
            published_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
            summary="Summary",
        )
        for i in range(10)
    ]

    mock_weather.return_value = WeatherData(
        city="Test", description="clair", temp_current=12.0,
        temp_min=8.0, temp_max=16.0,
    )

    mock_briefing.return_value = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="outro", text="À demain."),
    ]

    mock_ssml.return_value = "<speak>Bonjour. À demain.</speak>"

    mock_polly = MagicMock()
    mock_polly_cls.return_value = mock_polly
    mock_polly.synthesize.return_value = tmp_path / "test.mp3"

    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    run_pipeline(config_path=tmp_path / "settings.yaml")

    mock_collect.assert_called_once()
    mock_weather.assert_called_once()
    mock_briefing.assert_called_once()
    mock_ssml.assert_called_once()
    mock_polly.synthesize.assert_called_once()
    mock_publisher.publish.assert_called_once()
    mock_publisher.cleanup.assert_called_once()


@patch("src.orchestrator.HomeAssistantPublisher")
@patch("src.orchestrator.collect_all")
@patch("src.orchestrator.load_config")
def test_pipeline_aborts_when_not_enough_articles(
    mock_load_config: MagicMock,
    mock_collect: MagicMock,
    mock_publisher_cls: MagicMock,
    tmp_path: Path,
):
    from src.config import (
        Settings, WeatherConfig, EditorConfig, AudioConfig,
        PublisherConfig, LoggingConfig, Secrets,
    )

    mock_load_config.return_value = Settings(
        timezone="Europe/Paris",
        weather=WeatherConfig(city="Test", lat=0.0, lon=0.0),
        editor=EditorConfig(
            model="claude-haiku-4-5-20251001",
            max_general_news=5,
            max_tech_news=10,
        ),
        audio=AudioConfig(
            engine="polly", voice="Lea",
            output_dir=str(tmp_path), retention_days=7,
        ),
        publisher=PublisherConfig(
            ha_media_dir=str(tmp_path / "ha"),
            media_player_entity="media_player.echo",
        ),
        logging=LoggingConfig(level="INFO", log_dir=str(tmp_path / "logs")),
        sources=(),
        secrets=Secrets(
            anthropic_api_key="test",
            owm_api_key="test",
            ha_url="http://localhost:8123",
            ha_token="test",
        ),
    )

    # Only 3 articles — below minimum of 5
    mock_collect.return_value = [MagicMock() for _ in range(3)]

    mock_publisher = MagicMock()
    mock_publisher_cls.return_value = mock_publisher

    run_pipeline(config_path=tmp_path / "settings.yaml")

    mock_publisher.notify_failure.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement orchestrator**

Create `src/orchestrator.py`:

```python
"""Veille Techno — Main pipeline orchestrator.

Usage: python -m src.orchestrator [--config path/to/settings.yaml]
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date
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
from src.editor.ssml import build_ssml
from src.audio.polly import PollyTTS
from src.publisher.homeassistant import HomeAssistantPublisher

logger = logging.getLogger("veille_techno")

MIN_ARTICLES = 5


def _setup_logging(settings: Settings) -> None:
    """Configure rotating file + console logging."""
    log_dir = Path(settings.logging.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / "veille-techno.log",
        maxBytes=5_000_000,
        backupCount=7,
    )
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.logging.level, logging.INFO))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def _build_sources(settings: Settings) -> list[Source]:
    """Build source instances from config."""
    sources: list[Source] = []
    for src_cfg in settings.sources:
        if src_cfg.type == "rss":
            sources.append(
                RSSSource(
                    name=src_cfg.name,
                    category=src_cfg.category,
                    url=src_cfg.url,
                )
            )
        elif src_cfg.type == "hackernews":
            sources.append(
                HackerNewsSource(
                    name=src_cfg.name, category=src_cfg.category
                )
            )
        elif src_cfg.type == "github_trending":
            sources.append(
                GitHubTrendingSource(
                    name=src_cfg.name, category=src_cfg.category
                )
            )
    return sources


def collect_all(sources: list[Source]) -> list[Article]:
    """Fetch from all sources and deduplicate."""
    start = time.monotonic()
    all_articles: list[Article] = []

    for source in sources:
        try:
            articles = source.fetch()
            all_articles.extend(articles)
            logger.info(
                "  %s: %d articles", source.name, len(articles)
            )
        except Exception:
            logger.warning("  %s: FAILED", source.name, exc_info=True)

    deduped = deduplicate(all_articles)
    elapsed = time.monotonic() - start
    logger.info(
        "Collection complete: %d raw -> %d deduped in %.1fs",
        len(all_articles),
        len(deduped),
        elapsed,
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
    )

    try:
        # Step 1: Collect
        logger.info("Step 1: Collecting articles...")
        sources = _build_sources(settings)
        articles = collect_all(sources)

        if len(articles) < MIN_ARTICLES:
            msg = f"Not enough articles ({len(articles)}/{MIN_ARTICLES})"
            logger.warning(msg)
            publisher.notify_failure(msg)
            return

        # Step 2: Weather
        logger.info("Step 2: Fetching weather...")
        weather = fetch_weather(
            lat=settings.weather.lat,
            lon=settings.weather.lon,
            api_key=settings.secrets.owm_api_key,
        )
        if weather:
            logger.info("Weather: %s, %.0f°C", weather.description, weather.temp_current)
        else:
            logger.warning("Weather unavailable — will be omitted")

        # Step 3: Generate briefing
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
        logger.info(
            "Briefing: %d segments in %.1fs",
            len(segments),
            time.monotonic() - start,
        )

        # Step 4: Build SSML and synthesize audio
        logger.info("Step 4: Synthesizing audio...")
        ssml = build_ssml(segments)
        tts = PollyTTS(
            voice=settings.audio.voice,
            output_dir=settings.audio.output_dir,
        )
        today = date.today().isoformat()
        mp3_path = tts.synthesize(ssml, f"briefing-{today}")

        # Step 5: Publish
        logger.info("Step 5: Publishing to Home Assistant...")
        publisher.publish(mp3_path)
        publisher.cleanup(retention_days=settings.audio.retention_days)

        logger.info("=== Pipeline complete ===")

    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        publisher.notify_failure(f"Pipeline failed: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Veille Techno Briefing")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/settings.yaml"),
        help="Path to settings.yaml",
    )
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest --cov=src --cov-report=term-missing -v`
Expected: All tests PASS, coverage > 80%.

- [ ] **Step 6: Commit**

```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator pipeline — end-to-end flow"
```

---

## Chunk 8: Integration Test + Final Polish

### Task 14: Integration test (dry-run mode)

**Files:**
- Modify: `src/orchestrator.py` — add `--dry-run` flag
- Create: `tests/test_integration.py`

- [ ] **Step 1: Add --dry-run support to orchestrator**

In `src/orchestrator.py`, add to `main()`:

```python
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Validate config and test API connectivity without generating briefing",
)
```

Add a `dry_run` function in `src/orchestrator.py`:

```python
def run_dry_run(config_path: Path) -> None:
    """Validate config, test API keys, and source connectivity."""
    settings = load_config(config_path)
    _setup_logging(settings)
    logger.info("=== Dry run ===")

    errors: list[str] = []

    # Check secrets
    if not settings.secrets.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY not set")
    if not settings.secrets.owm_api_key:
        errors.append("OWM_API_KEY not set")
    if not settings.secrets.ha_token:
        errors.append("HA_TOKEN not set")

    # Check sources
    sources = _build_sources(settings)
    logger.info("Configured %d sources", len(sources))

    # Test weather
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
```

Update `main()`:

```python
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
    args = parser.parse_args()

    if args.dry_run:
        run_dry_run(args.config)
    else:
        run_pipeline(args.config)
```

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest --cov=src --cov-report=term-missing -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/orchestrator.py
git commit -m "feat: add --dry-run flag for config and connectivity validation"
```

---

### Task 15: Cron setup documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

```markdown
# Veille Techno

Briefing matinal audio automatisé — collecte de news, éditorialisation par IA, synthèse vocale, diffusion sur Amazon Echo via Home Assistant.

## Installation (Raspberry Pi)

### Prérequis

- Python >= 3.11
- ffmpeg: `sudo apt install ffmpeg`
- Home Assistant avec Alexa Media Player (HACS)

### Setup

```bash
git clone <repo-url> ~/veille-techno
cd ~/veille-techno

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
cp config/settings.example.yaml config/settings.yaml
```

Editer `.env` avec vos clés API et `config/settings.yaml` avec votre configuration.

### Validation

```bash
source .venv/bin/activate
python -m src.orchestrator --dry-run --config config/settings.yaml
```

### Cron (génération quotidienne à 7h30)

```bash
crontab -e
```

Ajouter :

```
30 7 * * * cd /home/<user>/veille-techno && /home/<user>/veille-techno/.venv/bin/python -m src.orchestrator --config config/settings.yaml >> /tmp/veille-techno-cron.log 2>&1
```

### Home Assistant

Configurer une automatisation HA qui lit le MP3 sur vos Echo quand le capteur de présence/réveil se déclenche :

```yaml
automation:
  - alias: "Briefing matinal"
    trigger:
      - platform: state
        entity_id: binary_sensor.alarm_clock
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ is_state('media_player.echo_salon', 'idle') }}
    action:
      - service: media_player.volume_set
        target:
          entity_id: media_player.echo_salon
        data:
          volume_level: 0.5
      - service: media_player.play_media
        target:
          entity_id: media_player.echo_salon
        data:
          media_content_id: >
            http://<HA_IP>:8123/local/briefings/briefing-{{ now().strftime('%Y-%m-%d') }}.mp3
          media_content_type: music
```

## Tests

```bash
source .venv/bin/activate
python -m pytest --cov=src --cov-report=term-missing -v
```

## Coût estimé

~6 EUR/mois (Claude Haiku + Amazon Polly). Polly gratuit la première année (Free Tier).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install, cron, and HA automation guide"
```

---

### Task 16: Final test run + coverage check

- [ ] **Step 1: Run full test suite with coverage**

Run: `python -m pytest --cov=src --cov-report=term-missing -v`
Expected: All tests PASS, coverage >= 80%.

- [ ] **Step 2: Fix any coverage gaps if below 80%**

Add missing tests as needed for uncovered branches.

- [ ] **Step 3: Final commit if any fixes**

```bash
git add -A
git commit -m "test: improve coverage to 80%+"
```
