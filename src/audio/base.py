from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSEngine(ABC):
    """Base class for text-to-speech engines."""

    @abstractmethod
    def synthesize(self, ssml: str, filename: str) -> Path:
        """Convert SSML text to audio file. Returns path to output file."""
        ...
