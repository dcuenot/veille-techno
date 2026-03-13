from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import requests

from src.collector.rss import RSSSource, LOOKBACK_WINDOW


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
    # Feed dates are 2026-03-12, so we freeze "now" to be within the lookback window
    frozen_now = datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = SAMPLE_FEED.encode()
    mock_get.return_value = mock_response

    source = RSSSource(
        name="Test Feed",
        category="tech",
        url="https://example.com/feed",
    )

    with patch("src.collector.rss.datetime", wraps=datetime) as mock_dt:
        mock_dt.now.return_value = frozen_now
        articles = source.fetch()

    assert len(articles) == 2
    assert articles[0].title == "Article One"
    assert articles[0].source == "Test Feed"
    assert articles[0].url == "https://example.com/1"
    assert articles[0].summary == "First article summary."


@patch("src.collector.rss.requests.get")
def test_rss_source_returns_empty_on_error(mock_get: MagicMock):
    mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

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
