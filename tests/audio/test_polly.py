from pathlib import Path
from unittest.mock import patch, MagicMock, call

from src.audio.polly import PollyTTS, chunk_ssml


def test_chunk_ssml_short_text():
    ssml = "<speak>Short text.</speak>"
    chunks = chunk_ssml(ssml, max_chars=3000)
    assert len(chunks) == 1
    assert chunks[0] == "<speak>Short text.</speak>"


def test_chunk_ssml_long_text():
    sentence = "Ceci est une phrase de test. "
    body = sentence * 150  # ~4200 chars
    ssml = f"<speak>{body}</speak>"
    chunks = chunk_ssml(ssml, max_chars=3000)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.startswith("<speak>")
        assert chunk.endswith("</speak>")
        assert len(chunk) <= 3000


def test_chunk_ssml_preserves_all_text():
    sentence = "Phrase numero {}. "
    body = "".join(sentence.format(i) for i in range(100))
    ssml = f"<speak>{body}</speak>"
    chunks = chunk_ssml(ssml, max_chars=3000)
    recombined = "".join(
        c.replace("<speak>", "").replace("</speak>", "")
        for c in chunks
    )
    assert recombined == body


def test_chunk_ssml_splits_on_break_tags():
    """Prefer splitting at <break/> boundaries, never inside a tag."""
    inner = (
        'Phrase un.<break strength="strong"/> '
        'Phrase deux.<break strength="strong"/> '
        'Phrase trois.<break strength="x-strong"/> '
        'Phrase quatre.'
    )
    ssml = f"<speak>{inner}</speak>"
    # Force a small limit so it must split
    chunks = chunk_ssml(ssml, max_chars=80)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.startswith("<speak>")
        assert chunk.endswith("</speak>")
        # No chunk should contain a broken/truncated XML tag
        import re
        # Every < should have a matching >
        tags = re.findall(r'<[^>]*$', chunk.replace("<speak>", "").replace("</speak>", ""))
        assert tags == [], f"Broken tag found in chunk: {chunk}"


def test_chunk_ssml_preserves_prosody_with_breaks():
    """Chunking with prosody wrapper and break tags should produce valid SSML."""
    inner = (
        'Bonjour.<break strength="strong"/> '
        'Les nouvelles du jour.<break strength="x-strong"/> '
        'A demain.'
    )
    ssml = f'<speak><prosody rate="95%" volume="x-loud">{inner}</prosody></speak>'
    chunks = chunk_ssml(ssml, max_chars=120)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert '<prosody rate="95%" volume="x-loud">' in chunk
        assert "</prosody></speak>" in chunk


@patch("src.audio.polly.AudioSegment")
@patch("src.audio.polly.boto3.client")
def test_polly_synthesize_creates_mp3(
    mock_boto_client: MagicMock, mock_audio_segment: MagicMock, tmp_path: Path
):
    mock_polly = MagicMock()
    mock_boto_client.return_value = mock_polly
    mock_polly.synthesize_speech.return_value = {
        "AudioStream": MagicMock(read=MagicMock(return_value=b"fake-audio"))
    }

    mock_segment = MagicMock()
    mock_audio_segment.from_mp3.return_value = mock_segment
    mock_segment.__add__ = MagicMock(return_value=mock_segment)

    tts = PollyTTS(voice="Lea", output_dir=str(tmp_path))
    ssml = "<speak>Bonjour.</speak>"
    result = tts.synthesize(ssml, "test-briefing")

    assert result.suffix == ".mp3"
    mock_polly.synthesize_speech.assert_called_once()
    mock_segment.export.assert_called_once()


@patch("src.audio.polly.AudioSegment")
@patch("src.audio.polly.boto3.client")
def test_polly_retries_on_failure(
    mock_boto_client: MagicMock, mock_audio_segment: MagicMock, tmp_path: Path
):
    mock_polly = MagicMock()
    mock_boto_client.return_value = mock_polly
    mock_polly.synthesize_speech.side_effect = [
        Exception("Transient error"),
        {"AudioStream": MagicMock(read=MagicMock(return_value=b"audio"))},
    ]

    mock_segment = MagicMock()
    mock_audio_segment.from_mp3.return_value = mock_segment

    tts = PollyTTS(voice="Lea", output_dir=str(tmp_path))
    result = tts.synthesize("<speak>Test.</speak>", "retry-test")

    assert mock_polly.synthesize_speech.call_count == 2
