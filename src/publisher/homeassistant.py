from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class HomeAssistantPublisher:
    """Publishes MP3 to Home Assistant and manages cleanup."""

    def __init__(
        self,
        ha_media_dir: str,
        ha_url: str,
        ha_token: str,
        media_player_entity: str,
    ) -> None:
        self.ha_media_dir = Path(ha_media_dir)
        self.ha_url = ha_url.rstrip("/")
        self.ha_token = ha_token
        self.media_player_entity = media_player_entity

    def publish(self, mp3_path: Path) -> Path:
        """Copy MP3 to HA media directory."""
        self.ha_media_dir.mkdir(parents=True, exist_ok=True)
        target = self.ha_media_dir / mp3_path.name
        shutil.copy2(mp3_path, target)
        logger.info("Published %s to %s", mp3_path.name, target)
        return target

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
