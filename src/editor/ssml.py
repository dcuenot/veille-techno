from __future__ import annotations

import html

from src.editor.briefing import BriefingSegment

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

        escaped_text = html.escape(segment.text, quote=False)
        parts.append(escaped_text)

        if segment.type == "news":
            news_count += 1

    parts.append("</prosody></speak>")
    return "".join(parts)
