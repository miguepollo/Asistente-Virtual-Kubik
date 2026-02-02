"""
Thread-safe state management for webserver.
"""
import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class DownloadStatus:
    """Thread-safe download status."""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    downloading: bool = False
    model: Optional[str] = None
    progress: int = 0
    error: Optional[str] = None
    type: Optional[str] = None  # "llm" or "tts"
    started_at: Optional[datetime] = None

    def update(self, **kwargs):
        """Thread-safe update."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def get_snapshot(self) -> dict:
        """Thread-safe snapshot."""
        with self._lock:
            return {
                "downloading": self.downloading,
                "model": self.model,
                "progress": self.progress,
                "error": self.error,
                "type": self.type,
                "started_at": self.started_at.isoformat() if self.started_at else None
            }


# Singleton instance
_download_status = DownloadStatus()


def get_download_status() -> DownloadStatus:
    """Get the download status singleton."""
    return _download_status
