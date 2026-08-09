"""Protocol interfaces (ports) for the hexagonal architecture.

Only Protocol/Enum/dataclass definitions live here. Never import a concrete
adapter from this package.

NOTE: LyricsPort, NotificationsPort, ConfigPort, DownloaderPort,
VisualizerPort existed in a previous iteration but had no adapters and no
consumers — they were removed from this __init__ to stop the DI container
from silently wiring interfaces nothing implements. The .py stub files with
those Protocol definitions still exist under core/ports/ and can be
reintroduced explicitly in a later phase (visualizer/GUI/API work).
LibraryPort was in that same list until SqliteLibraryAdapter was implemented
(see adapters/library/sqlite_adapter.py) - it's back below.
"""

from .audio import AudioPort, PlaybackState
from .library import Album, Artist, Collection, LibraryPort, Song
from .metadata import AudioMetadata, MetadataPort

__all__ = [
    "AudioPort",
    "PlaybackState",
    "AudioMetadata",
    "MetadataPort",
    "LibraryPort",
    "Artist",
    "Album",
    "Song",
    "Collection",
]
