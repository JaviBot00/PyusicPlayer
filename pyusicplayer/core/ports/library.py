"""Library port - Protocol for music library database."""

from typing import Protocol, Optional, List
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime


@dataclass
class Artist:
    """Artist database record."""
    
    id: Optional[int] = None
    name: str = ""
    sort_name: Optional[str] = None
    image_path: Optional[str] = None


@dataclass
class Album:
    """Album database record."""
    
    id: Optional[int] = None
    title: str = ""
    artist_id: Optional[int] = None
    artist_name: Optional[str] = None
    year: Optional[int] = None
    cover_path: Optional[str] = None
    disk_count: int = 1


@dataclass
class Song:
    """Song database record."""
    
    id: Optional[int] = None
    file_path: str = ""
    title: Optional[str] = None
    artist_id: Optional[int] = None
    artist_name: Optional[str] = None
    album_id: Optional[int] = None
    album_title: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    size: Optional[int] = None
    last_modified: Optional[datetime] = None
    last_scanned: Optional[datetime] = None


@dataclass
class Collection:
    """Collection (playlist/smartlist) database record."""
    
    id: Optional[int] = None
    name: str = ""
    is_smart: bool = False
    query: Optional[str] = None
    song_ids: List[int] = None
    
    def __post_init__(self):
        if self.song_ids is None:
            self.song_ids = []


class LibraryPort(Protocol):
    """Protocol for library database adapters.
    
    Implementations must provide CRUD operations for artists,
    albums, songs, and collections, plus search functionality.
    """

    def initialize(self) -> None:
        """Initialize database connection and create tables if needed."""
        ...

    def close(self) -> None:
        """Close database connection."""
        ...

    # Artists
    def get_artist(self, artist_id: int) -> Optional[Artist]:
        """Get artist by ID."""
        ...

    def get_or_create_artist(self, name: str) -> Artist:
        """Get existing artist or create new one."""
        ...

    def search_artists(self, query: str) -> List[Artist]:
        """Search artists by name."""
        ...

    # Albums
    def get_album(self, album_id: int) -> Optional[Album]:
        """Get album by ID."""
        ...

    def get_or_create_album(self, title: str, artist_id: Optional[int] = None) -> Album:
        """Get existing album or create new one."""
        ...

    def search_albums(self, query: str) -> List[Album]:
        """Search albums by title."""
        ...

    # Songs
    def get_song(self, song_id: int) -> Optional[Song]:
        """Get song by ID."""
        ...

    def add_song(self, song: Song) -> int:
        """Add a new song to the library.
        
        Returns:
            ID of the inserted song.
        """
        ...

    def update_song(self, song: Song) -> bool:
        """Update an existing song.
        
        Returns:
            True if updated, False if not found.
        """
        ...

    def delete_song(self, song_id: int) -> bool:
        """Delete a song from the library.
        
        Returns:
            True if deleted, False if not found.
        """
        ...

    def get_all_songs(self) -> List[Song]:
        """Get all songs in the library."""
        ...

    def search_songs(self, query: str) -> List[Song]:
        """Search songs by title, artist, or album."""
        ...

    def get_songs_by_artist(self, artist_id: int) -> List[Song]:
        """Get all songs by an artist."""
        ...

    def get_songs_by_album(self, album_id: int) -> List[Song]:
        """Get all songs in an album."""
        ...

    # Collections
    def get_collection(self, collection_id: int) -> Optional[Collection]:
        """Get collection by ID."""
        ...

    def create_collection(self, name: str, is_smart: bool = False) -> Collection:
        """Create a new collection."""
        ...

    def add_to_collection(self, collection_id: int, song_id: int) -> bool:
        """Add a song to a collection.
        
        Returns:
            True if added, False if already exists.
        """
        ...

    def remove_from_collection(self, collection_id: int, song_id: int) -> bool:
        """Remove a song from a collection.
        
        Returns:
            True if removed, False if not found.
        """
        ...

    def get_collection_songs(self, collection_id: int) -> List[Song]:
        """Get all songs in a collection."""
        ...

    # Import
    def import_directory(self, dir_path: str, recursive: bool = True) -> int:
        """Import a directory into the library.
        
        Args:
            dir_path: Path to directory to import.
            recursive: Whether to scan subdirectories.
        
        Returns:
            Number of songs imported.
        """
        ...

    def get_stats(self) -> dict:
        """Get library statistics.
        
        Returns:
            Dict with counts of songs, albums, artists, etc.
        """
        ...
