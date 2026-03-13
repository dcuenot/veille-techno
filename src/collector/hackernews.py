from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from src.collector.base import Article, Source

logger = logging.getLogger(__name__)

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://news.ycombinator.com/item?id="


class HackerNewsSource(Source):
    def __init__(self, name: str = "Hacker News", category: str = "tech", min_points: int = 50, timeout: int = 15) -> None:
        super().__init__(name=name, category=category, timeout=timeout)
        self.min_points = min_points

    def fetch(self) -> list[Article]:
        try:
            response = requests.get(
                ALGOLIA_URL,
                params={"tags": "story", "numericFilters": f"points>{self.min_points}", "hitsPerPage": 30},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch Hacker News: %s", e)
            return []

        articles: list[Article] = []
        for hit in data.get("hits", []):
            try:
                url = hit.get("url") or f"{HN_ITEM_URL}{hit['objectID']}"
                published = datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc)
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
            except KeyError as e:
                logger.warning("Skipping malformed HN hit (missing key %s)", e)
                continue

        logger.info("Fetched %d articles from Hacker News", len(articles))
        return articles
