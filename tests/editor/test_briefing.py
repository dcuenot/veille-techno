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
    {"type": "weather", "text": "Cote meteo, ciel degage, 12 degres."},
    {"type": "news", "text": "Dans l'essentiel aujourd'hui..."},
    {"type": "news", "text": "Cote tech maintenant..."},
    {"type": "outro", "text": "Bonne journee et a demain."},
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
        description="ciel degage",
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
        {"type": "outro", "text": "A demain."},
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
