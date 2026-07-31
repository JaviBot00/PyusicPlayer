"""Metadata port - Protocol for audio metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class AudioMetadata:
    """Audio file metadata container."""

    file_path: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    duration: Optional[float] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    cover_data: Optional[bytes] = None
    cover_mime: Optional[str] = None


class MetadataPort(Protocol):
    """Protocol for metadata extraction adapters."""

    def extract(self, file_path: str) -> AudioMetadata:
        """Extract metadata from an audio file.

        Never raises on malformed tags: returns best-effort partial metadata.
        Raises FileNotFoundError if the file does not exist, ValueError if
        the format is unsupported.
        """
        ...

    def get_cover(self, file_path: str) -> Optional[bytes]:
        """Extract embedded cover art, or None if unavailable."""
        ...

    def supports_format(self, file_path: str) -> bool:
        """Check if the format is supported for metadata operations."""
        ...
