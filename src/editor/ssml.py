from __future__ import annotations

import html
import logging
import re

from src.editor.briefing import BriefingSegment

logger = logging.getLogger(__name__)

# Pauses between segments (sentence-level)
BREAK_BETWEEN = '<break strength="strong"/>'
# Pauses between sections (paragraph-level)
BREAK_SECTION = '<break strength="x-strong"/>'
# Pause after each sentence within a segment
BREAK_SENTENCE = '<break strength="strong"/>'


def _add_sentence_breaks(text: str) -> str:
    """Insert sentence-level pauses after sentence-ending punctuation."""
    # Add break after . ! ? followed by a space and uppercase letter
    result = re.sub(
        r'([.!?])\s+(?=[A-ZÀ-ÖÙ-Ü])',
        rf'\1{BREAK_SENTENCE} ',
        text,
    )
    return result


def build_ssml(segments: list[BriefingSegment]) -> str:
    """Build SSML from briefing segments with pauses and prosody."""
    parts: list[str] = ['<speak><amazon:domain name="news"><amazon:auto-breaths><prosody rate="95%" volume="x-loud">']

    news_count = 0
    for i, segment in enumerate(segments):
        if i > 0:
            if segment.type == "news" and news_count == 1:
                # Longer pause before tech section
                parts.append(BREAK_SECTION)
            elif segment.type == "outro":
                parts.append(BREAK_SECTION)
            else:
                parts.append(BREAK_BETWEEN)

        escaped_text = _sanitize_for_ssml(segment.text)
        text_with_breaks = _add_sentence_breaks(escaped_text)
        parts.append(text_with_breaks)

        if segment.type == "news":
            news_count += 1

    parts.append("</prosody></amazon:auto-breaths></amazon:domain></speak>")
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
