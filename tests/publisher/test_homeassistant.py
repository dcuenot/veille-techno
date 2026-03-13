import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.publisher.homeassistant import HomeAssistantPublisher


def test_publish_copies_file(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_mp3 = source_dir / "briefing-2026-03-12.mp3"
    source_mp3.write_bytes(b"fake mp3 data")
    target_dir = tmp_path / "ha_media"
    target_dir.mkdir()
    publisher = HomeAssistantPublisher(
        ha_media_dir=str(target_dir),
        ha_url="http://localhost:8123",
        ha_token="test-token",
        media_player_entity="media_player.echo",
    )
    publisher.publish(source_mp3)
    target_file = target_dir / "briefing-2026-03-12.mp3"
    assert target_file.exists()
    assert target_file.read_bytes() == b"fake mp3 data"


@patch("src.publisher.homeassistant.requests.post")
def test_notify_failure_calls_ha_api(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=200)
    publisher = HomeAssistantPublisher(
        ha_media_dir="/tmp",
        ha_url="http://localhost:8123",
        ha_token="test-token",
        media_player_entity="media_player.echo",
    )
    publisher.notify_failure("Pipeline failed: API error")
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "notify" in call_kwargs[0][0]


@patch("src.publisher.homeassistant.requests.post")
def test_notify_failure_handles_request_exception(mock_post: MagicMock):
    mock_post.side_effect = Exception("connection refused")
    publisher = HomeAssistantPublisher(
        ha_media_dir="/tmp",
        ha_url="http://localhost:8123",
        ha_token="test-token",
        media_player_entity="media_player.echo",
    )
    # Should not raise even when requests.post raises
    publisher.notify_failure("some error")


def test_cleanup_old_files(tmp_path: Path):
    import time
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    old_file = media_dir / "briefing-2026-03-01.mp3"
    old_file.write_bytes(b"old")
    new_file = media_dir / "briefing-2026-03-12.mp3"
    new_file.write_bytes(b"new")
    publisher = HomeAssistantPublisher(
        ha_media_dir=str(media_dir),
        ha_url="http://localhost:8123",
        ha_token="test-token",
        media_player_entity="media_player.echo",
    )
    import os
    old_time = time.time() - (10 * 86400)
    os.utime(old_file, (old_time, old_time))
    publisher.cleanup(retention_days=7)
    assert not old_file.exists()
    assert new_file.exists()
