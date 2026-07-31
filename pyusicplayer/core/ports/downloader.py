"""Downloader port - Protocol for yt-dlp audio download."""

from typing import Protocol, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class DownloadStatus(Enum):
    """Download status states."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Download progress information."""
    
    status: DownloadStatus
    url: str
    title: Optional[str] = None
    artist: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    speed: Optional[float] = None  # bytes per second
    eta: Optional[float] = None  # seconds remaining
    file_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DownloadRequest:
    """Request for audio download."""
    
    url: str
    output_dir: str = "./downloads"
    quality: str = "opus"  # opus, mp3, flac, m4a
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    title: Optional[str] = None
    artist: Optional[str] = None


# Callback type for progress updates
ProgressCallback = Callable[[DownloadProgress], None]


class DownloaderPort(Protocol):
    """Protocol for audio download adapters.
    
    Implementations must provide yt-dlp based audio download
    with metadata embedding and progress tracking.
    """

    def download(self, request: DownloadRequest, callback: Optional[ProgressCallback] = None) -> str:
        """Download audio from URL.
        
        Args:
            request: Download request with URL and options.
            callback: Optional callback for progress updates.
        
        Returns:
            Path to the downloaded file.
        
        Raises:
            ValueError: If the URL is invalid.
            RuntimeError: If the download fails.
        """
        ...

    def get_info(self, url: str) -> dict:
        """Get video/audio information without downloading.
        
        Args:
            url: URL to get info for.
        
        Returns:
            Dict with video metadata (title, artist, duration, etc.).
        """
        ...

    def cancel(self, url: str) -> bool:
        """Cancel an active download.
        
        Args:
            url: URL of the download to cancel.
        
        Returns:
            True if cancelled, False if not found.
        """
        ...

    def get_active_downloads(self) -> list:
        """Get list of active downloads.
        
        Returns:
            List of DownloadProgress objects.
        """
        ...

    def is_available(self) -> bool:
        """Check if yt-dlp is available on the system.
        
        Returns:
            True if yt-dlp is installed and accessible.
        """
        ...
