from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class HomeAssistantPublisher:
    """Publishes MP3 to S3 and triggers playback via Home Assistant."""

    def __init__(
        self,
        ha_media_dir: str,
        ha_url: str,
        ha_token: str,
        media_player_entities: tuple[str, ...],
        s3_bucket: str = "",
    ) -> None:
        self.ha_media_dir = Path(ha_media_dir)
        self.ha_url = ha_url.rstrip("/")
        self.ha_token = ha_token
        self.media_player_entities = media_player_entities
        self.s3_bucket = s3_bucket

    def publish(self, mp3_path: Path) -> Path:
        """Copy MP3 to HA media directory."""
        self.ha_media_dir.mkdir(parents=True, exist_ok=True)
        target = self.ha_media_dir / mp3_path.name
        shutil.copy2(mp3_path, target)
        logger.info("Published %s to %s", mp3_path.name, target)
        return target

    def publish_and_play(self, mp3_path: Path) -> None:
        """Upload to S3, then trigger playback on Echo via HA."""
        from src.publisher.s3 import upload_to_s3, cleanup_s3

        if not self.s3_bucket:
            logger.warning("No S3 bucket configured — skipping upload and playback")
            self.publish(mp3_path)
            return

        s3_url = upload_to_s3(mp3_path, self.s3_bucket)
        cleanup_s3(self.s3_bucket)

        # Also keep local copy
        self.publish(mp3_path)

        # Trigger playback via HA API
        self._play_on_echo(s3_url)

    def play_tts(self, text: str) -> None:
        """Send briefing text via notify.alexa_media TTS to all entities."""
        url = f"{self.ha_url}/api/services/notify/alexa_media"
        for entity in self.media_player_entities:
            try:
                response = requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.ha_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "message": text,
                        "target": entity,
                        "data": {"type": "tts"},
                    },
                    timeout=30,
                )
                response.raise_for_status()
                logger.info("TTS triggered on %s (%d chars)", entity, len(text))
            except requests.exceptions.HTTPError:
                logger.error("TTS failed on %s: HTTP %s", entity, response.status_code)
            except requests.exceptions.RequestException:
                logger.error("TTS failed on %s: connection error", entity, exc_info=True)

    def fire_event(self, event_type: str, event_data: dict | None = None) -> None:
        """Fire a custom event on HA event bus."""
        url = f"{self.ha_url}/api/events/{event_type}"
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json",
                },
                json=event_data or {},
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Event %s fired", event_type)
        except Exception:
            logger.error("Failed to fire event %s", event_type, exc_info=True)

    def notify_failure(self, message: str) -> None:
        """Send a persistent notification via HA API."""
        url = f"{self.ha_url}/api/services/notify/persistent_notification"
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "title": "Veille Techno - Erreur",
                    "message": message,
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Failure notification sent to HA")
        except Exception:
            logger.error("Failed to send notification to HA")

    def cleanup(self, retention_days: int = 7) -> None:
        """Remove MP3 files older than retention_days."""
        if not self.ha_media_dir.exists():
            return
        cutoff = time.time() - (retention_days * 86400)
        for mp3_file in self.ha_media_dir.glob("briefing-*.mp3"):
            if mp3_file.stat().st_mtime < cutoff:
                mp3_file.unlink()
                logger.info("Cleaned up old file: %s", mp3_file.name)
