from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from time import mktime

import feedparser
import requests

from src.collector.base import Article, Source

logger = logging.getLogger(__name__)

LOOKBACK_WINDOW = timedelta(hours=48)


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
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch RSS feed %s: %s", self.name, e)
            return []

        feed = feedparser.parse(response.content)
        now = datetime.now(timezone.utc)
        cutoff = now - LOOKBACK_WINDOW
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
                    return datetime.fromtimestamp(
                        mktime(parsed_field), tz=timezone.utc
                    )
                except (ValueError, TypeError, OverflowError):
                    pass
        return None
