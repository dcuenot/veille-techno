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
    assert "news.ycombinator.com" in articles[1].url

@patch("src.collector.hackernews.requests.get")
def test_hn_returns_empty_on_error(mock_get: MagicMock):
    mock_get.side_effect = Exception("API error")
    source = HackerNewsSource(name="Hacker News", category="tech")
    articles = source.fetch()
    assert articles == []
