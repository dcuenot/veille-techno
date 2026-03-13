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
