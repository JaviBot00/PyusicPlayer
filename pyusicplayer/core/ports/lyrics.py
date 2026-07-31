"""Lyrics port - Protocol for lyrics fetching and storage."""

from typing import Protocol, Optional, List
from dataclasses import dataclass
from enum import Enum


class LyricsSource(Enum):
    """Source of lyrics."""
    LOCAL = "local"
    LRCLIB = "lrclib"
    EMBEDDED = "embedded"


@dataclass
class LRCLine:
    """A single line of synchronized lyrics."""
    
    timestamp: float  # Seconds
    text: str


@dataclass
class LyricsResult:
    """Result from lyrics search."""
    
    source: LyricsSource
    artist: str
    title: str
    album: Optional[str] = None
    synchronized: bool = False
    plain_text: Optional[str] = None
    lrc_text: Optional[str] = None
    duration: Optional[float] = None


class LyricsPort(Protocol):
    """Protocol for lyrics adapters.
    
    Implementations must provide lyrics fetching from online sources
    and local .lrc file parsing.
    """

    def search(self, artist: str, title: str, album: Optional[str] = None) -> List[LyricsResult]:
        """Search for lyrics by artist and title.
        
        Args:
            artist: Artist name.
            title: Song title.
            album: Optional album name for better matching.
        
        Returns:
            List of LyricsResult objects found.
        """
        ...

    def fetch(self, result: LyricsResult) -> Optional[str]:
        """Fetch full lyrics from a search result.
        
        Args:
            result: The LyricsResult to fetch lyrics for.
        
        Returns:
            Plain text lyrics or None if not available.
        """
        ...

    def parse_lrc(self, lrc_content: str) -> List[LRCLine]:
        """Parse LRC format lyrics into structured lines.
        
        Args:
            lrc_content: Raw LRC format string.
        
        Returns:
            List of LRCLine objects sorted by timestamp.
        """
        ...

    def find_local(self, file_path: str) -> Optional[str]:
        """Find and load local .lrc file for an audio file.
        
        Args:
            file_path: Path to the audio file.
        
        Returns:
            LRC content as string or None if not found.
        """
        ...

    def get_synchronized_line(self, lines: List[LRCLine], position: float) -> Optional[int]:
        """Get the index of the current synchronized line.
        
        Args:
            lines: List of parsed LRC lines.
            position: Current playback position in seconds.
        
        Returns:
            Index of the current line or None if no match.
        """
        ...
