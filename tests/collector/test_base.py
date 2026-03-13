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
