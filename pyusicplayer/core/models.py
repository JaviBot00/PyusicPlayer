"""Core domain models. No external dependencies (pure business logic)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PlaylistMode(Enum):
    """Playlist playback modes."""
    NONE = "none"
    ONE = "one"
    ALL = "all"


@dataclass
class Track:
    """Represents a single audio track."""

    file_path: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[float] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    cover_data: Optional[bytes] = None

    def __post_init__(self) -> None:
        if not self.title:
            self.title = Path(self.file_path).stem

    @property
    def display_name(self) -> str:
        parts = [p for p in (self.artist, self.title) if p]
        return " - ".join(parts) if parts else Path(self.file_path).stem

    @property
    def format_duration(self) -> str:
        if self.duration is None:
            return "--:--"
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes:02d}:{seconds:02d}"


@dataclass
class Playlist:
    """Represents a playlist of tracks with playback-order strategies."""

    name: str = ""
    tracks: list[Track] = field(default_factory=list)
    current_index: int = -1
    mode: PlaylistMode = PlaylistMode.NONE
    shuffle: bool = False

    _shuffle_bag: list[int] = field(default_factory=list, repr=False, compare=False)
    _shuffle_bag_initialized: bool = field(default=False, repr=False, compare=False)

    @property
    def current_track(self) -> Optional[Track]:
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None

    @property
    def is_empty(self) -> bool:
        return len(self.tracks) == 0

    @property
    def length(self) -> int:
        return len(self.tracks)

    @property
    def total_duration(self) -> float:
        return sum(t.duration or 0 for t in self.tracks)

    def add_track(self, track: Track) -> None:
        self.tracks.append(track)

    def remove_track(self, index: int) -> Optional[Track]:
        if 0 <= index < len(self.tracks):
            track = self.tracks.pop(index)
            if self.current_index >= len(self.tracks):
                self.current_index = len(self.tracks) - 1
            return track
        return None

    def clear(self) -> None:
        self.tracks.clear()
        self.current_index = -1
        self._shuffle_bag.clear()
        self._shuffle_bag_initialized = False

    def _refill_shuffle_bag(self) -> None:
        """Fisher-Yates shuffle of all indices except the current one."""
        indices = [i for i in range(len(self.tracks)) if i != self.current_index]
        for i in range(len(indices) - 1, 0, -1):
            j = random.randint(0, i)
            indices[i], indices[j] = indices[j], indices[i]
        self._shuffle_bag = indices
        self._shuffle_bag_initialized = True

    def next_index(self) -> int:
        """Get the next track index based on mode. Does not mutate state."""
        if self.is_empty:
            return -1

        if self.mode == PlaylistMode.ONE:
            return self.current_index if self.current_index >= 0 else 0

        if self.shuffle:
            if self._shuffle_bag:
                return self._shuffle_bag[0]
            if self._shuffle_bag_initialized and self.mode != PlaylistMode.ALL:
                # Bag was consumed to empty on a previous advance() and this
                # isn't loop-all: shuffle only changes ORDER, not whether the
                # playlist stops or loops - same decision sequential mode
                # makes at the end of the list.
                return -1
            self._refill_shuffle_bag()
            if not self._shuffle_bag:
                # Only one track total.
                return self.current_index if self.current_index >= 0 else 0
            return self._shuffle_bag[0]

        next_idx = self.current_index + 1
        if next_idx >= len(self.tracks):
            return 0 if self.mode == PlaylistMode.ALL else -1
        return next_idx

    def advance(self) -> int:
        """Compute and commit the move to the next index, consuming the shuffle bag."""
        idx = self.next_index()
        if self.shuffle and self._shuffle_bag and idx == self._shuffle_bag[0]:
            self._shuffle_bag.pop(0)
        if idx >= 0:
            self.current_index = idx
        return idx

    def previous_index(self) -> int:
        if self.is_empty:
            return -1
        prev_idx = self.current_index - 1
        if prev_idx < 0:
            return len(self.tracks) - 1 if self.mode == PlaylistMode.ALL else 0
        return prev_idx
