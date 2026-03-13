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
