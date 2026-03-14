from __future__ import annotations

import logging
import time
from io import BytesIO
from pathlib import Path

import boto3
from pydub import AudioSegment

from src.audio.base import TTSEngine

logger = logging.getLogger(__name__)

MAX_SSML_CHARS = 3000
MAX_RETRIES = 2


def chunk_ssml(ssml: str, max_chars: int = MAX_SSML_CHARS) -> list[str]:
    """Split SSML into chunks that fit within Polly's character limit.

    Strips <speak> and <prosody> wrappers, splits plain text on sentence
    boundaries, then re-wraps each chunk with both tags.
    """
    import re

    inner = ssml
    if inner.startswith("<speak>"):
        inner = inner[7:]
    if inner.endswith("</speak>"):
        inner = inner[:-8]

    # Extract and strip prosody wrapper if present
    prosody_open = ""
    prosody_close = ""
    prosody_match = re.match(r'(<prosody[^>]*>)(.*)(</prosody>)$', inner, re.DOTALL)
    if prosody_match:
        prosody_open = prosody_match.group(1)
        inner = prosody_match.group(2)
        prosody_close = prosody_match.group(3)

    wrapper_open = f"<speak>{prosody_open}"
    wrapper_close = f"{prosody_close}</speak>"
    overhead = len(wrapper_open) + len(wrapper_close)
    max_inner = max_chars - overhead

    if len(inner) <= max_inner:
        return [f"{wrapper_open}{inner}{wrapper_close}"]

    chunks: list[str] = []
    remaining = inner

    while remaining:
        if len(remaining) <= max_inner:
            chunks.append(f"{wrapper_open}{remaining}{wrapper_close}")
            break

        split_at = remaining[:max_inner].rfind(". ")
        if split_at != -1:
            split_at += 2
        else:
            split_at = remaining[:max_inner].rfind(" ")
            if split_at != -1:
                split_at += 1
            else:
                split_at = max_inner

        chunk_text = remaining[:split_at]
        remaining = remaining[split_at:]
        chunks.append(f"{wrapper_open}{chunk_text}{wrapper_close}")

    return chunks


ALEXA_MAX_DURATION_S = 230  # Alexa <audio> limit is 240s, keep margin


def convert_for_alexa(mp3_path: Path) -> list[Path]:
    """Convert MP3 to Alexa-compatible chunks (48kbps, 16kHz, stereo, <=230s each)."""
    import subprocess

    # First convert to Alexa format
    converted = mp3_path.with_suffix(".alexa.mp3")
    cmd = [
        "ffmpeg", "-y", "-i", str(mp3_path),
        "-ac", "2", "-codec:a", "libmp3lame",
        "-b:a", "48k", "-ar", "16000",
        str(converted),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    # Get duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(converted)],
        capture_output=True, text=True, timeout=30,
    )
    duration = float(probe.stdout.strip())

    if duration <= ALEXA_MAX_DURATION_S:
        logger.info("Converted %s for Alexa (%.0fs, 1 chunk)", mp3_path.name, duration)
        return [converted]

    # Split into chunks
    num_chunks = int(duration // ALEXA_MAX_DURATION_S) + 1
    chunks: list[Path] = []
    stem = mp3_path.stem

    for i in range(num_chunks):
        start = i * ALEXA_MAX_DURATION_S
        chunk_path = mp3_path.parent / f"{stem}.alexa-{i + 1}.mp3"
        split_cmd = [
            "ffmpeg", "-y", "-i", str(converted),
            "-ss", str(start), "-t", str(ALEXA_MAX_DURATION_S),
            "-c", "copy", str(chunk_path),
        ]
        res = subprocess.run(split_cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            raise RuntimeError(f"ffmpeg split failed for chunk {i + 1}: {res.stderr}")
        chunks.append(chunk_path)

    # Clean up single converted file
    converted.unlink(missing_ok=True)
    logger.info("Converted %s for Alexa (%.0fs, %d chunks)", mp3_path.name, duration, len(chunks))
    return chunks


class PollyTTS(TTSEngine):
    """Amazon Polly Neural TTS implementation."""

    def __init__(self, voice: str = "Lea", output_dir: str = "output/") -> None:
        self.voice = voice
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, ssml: str, filename: str) -> Path:
        """Convert SSML to MP3 via Amazon Polly. Handles chunking."""
        client = boto3.client("polly")
        chunks = chunk_ssml(ssml)

        logger.info("Synthesizing %d SSML chunk(s) with voice %s", len(chunks), self.voice)

        audio_segments: list[AudioSegment] = []

        for i, chunk in enumerate(chunks):
            audio_data = self._synthesize_chunk(client, chunk)
            segment = AudioSegment.from_mp3(BytesIO(audio_data))
            audio_segments.append(segment)
            logger.info("Chunk %d/%d synthesized", i + 1, len(chunks))

        if not audio_segments:
            raise RuntimeError("No audio segments were synthesized — SSML may be empty")
        combined = audio_segments[0]
        for segment in audio_segments[1:]:
            combined = combined + segment

        output_path = self.output_dir / f"{filename}.mp3"
        combined.export(str(output_path), format="mp3")
        logger.info("Audio saved to %s", output_path)
        return output_path

    def _synthesize_chunk(self, client: object, ssml: str) -> bytes:
        """Synthesize a single SSML chunk with retry + exponential backoff."""
        for i in range(MAX_RETRIES):
            try:
                response = client.synthesize_speech(
                    Text=ssml,
                    TextType="ssml",
                    OutputFormat="mp3",
                    VoiceId=self.voice,
                    Engine="neural",
                )
                return response["AudioStream"].read()
            except Exception as e:
                logger.warning("Polly synthesis error (attempt %d): %s", i + 1, e)
                if i < MAX_RETRIES - 1:
                    time.sleep(2 ** i)
                else:
                    raise
        raise RuntimeError("Polly synthesis failed")
