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
