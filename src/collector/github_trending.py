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
    def __init__(self, name: str = "GitHub Trending", category: str = "tech", timeout: int = 15) -> None:
        super().__init__(name=name, category=category, timeout=timeout)

    def fetch(self) -> list[Article]:
        try:
            response = requests.get(TRENDING_URL, timeout=self.timeout, headers={"Accept": "text/html"})
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch GitHub Trending: %s", e)
            return []
        return self._parse_html(response.text)

    def _parse_html(self, html: str) -> list[Article]:
        articles: list[Article] = []
        now = datetime.now(timezone.utc)

        article_pattern = re.compile(r'<article class="Box-row">(.*?)</article>', re.DOTALL)
        href_pattern = re.compile(r'<a href="(/[^"]+)"[^>]*>([^<]*)</a>')
        desc_pattern = re.compile(r'<p class="[^"]*color-fg-muted[^"]*"[^>]*>\s*([^<]*?)\s*</p>')

        for article_match in article_pattern.finditer(html):
            body = article_match.group(1)
            href_m = href_pattern.search(body)
            if not href_m:
                continue
            desc_m = desc_pattern.search(body)

            path = href_m.group(1).strip()
            name = re.sub(r"\s+", " ", href_m.group(2)).strip()
            description = desc_m.group(1).strip() if desc_m else ""

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

        logger.info("Fetched %d repos from GitHub Trending", len(articles))
        return articles
