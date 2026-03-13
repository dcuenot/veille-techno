from __future__ import annotations

import html
import logging
import re

from src.editor.briefing import BriefingSegment

logger = logging.getLogger(__name__)

BREAK_SHORT = '<break time="800ms"/>'
BREAK_LONG = '<break time="1200ms"/>'


def build_ssml(segments: list[BriefingSegment]) -> str:
    """Build SSML from briefing segments with pauses and prosody."""
    parts: list[str] = ['<speak><prosody rate="95%">']

    news_count = 0
    for i, segment in enumerate(segments):
        if i > 0:
            if segment.type == "news" and news_count == 1:
                parts.append(BREAK_LONG)
            else:
                parts.append(BREAK_SHORT)

        escaped_text = _sanitize_for_ssml(segment.text)
        parts.append(escaped_text)

        if segment.type == "news":
            news_count += 1

    parts.append("</prosody></speak>")
    result = "".join(parts)
    logger.debug("Generated SSML (%d chars): %.500s...", len(result), result)
    return result


def _sanitize_for_ssml(text: str) -> str:
    """Escape and clean text for valid SSML."""
    # Remove control characters (except newline/tab)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # Replace smart quotes and special punctuation
    cleaned = cleaned.replace("\u2019", "'")  # right single quote
    cleaned = cleaned.replace("\u2018", "'")  # left single quote
    cleaned = cleaned.replace("\u201c", '"')  # left double quote
    cleaned = cleaned.replace("\u201d", '"')  # right double quote
    cleaned = cleaned.replace("\u2026", "...")  # ellipsis
    cleaned = cleaned.replace("\u2013", "-")  # en dash
    cleaned = cleaned.replace("\u2014", "-")  # em dash
    # HTML escape for XML safety
    cleaned = html.escape(cleaned, quote=False)
    return cleaned
