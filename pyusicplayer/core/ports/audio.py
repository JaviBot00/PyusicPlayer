"""Audio playback port - Protocol for audio backend adapters."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Protocol


class PlaybackState(Enum):
    """Current playback state."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class AudioPort(Protocol):
    """Protocol for audio playback adapters."""

    def initialize(self) -> None:
        """Initialize the audio backend."""
        ...

    def shutdown(self) -> None:
        """Shutdown the audio backend and release resources."""
        ...

    def load(self, file_path: str) -> None:
        """Load an audio file for playback (does not start playback)."""
        ...

    def play(self) -> None:
        """Start or resume playback."""
        ...

    def pause(self) -> None:
        """Pause playback."""
        ...

    def stop(self) -> None:
        """Stop playback and reset position to 0."""
        ...

    def seek(self, position_seconds: float) -> None:
        """Seek to a specific position in the currently loaded track."""
        ...

    def get_position(self) -> float:
        """Get current playback position in seconds."""
        ...

    def get_duration(self) -> float:
        """Get duration in seconds of the loaded track, or 0.0 if unknown."""
        ...

    def get_state(self) -> PlaybackState:
        """Get current playback state."""
        ...

    def set_volume(self, volume: float) -> None:
        """Set playback volume, 0.0 (mute) to 1.0 (max)."""
        ...

    def get_volume(self) -> float:
        """Get current volume level."""
        ...

    def is_track_loaded(self) -> bool:
        """Check if a track is currently loaded."""
        ...

    def on_track_end(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the loaded track finishes playing naturally.

        Must NOT fire on an explicit stop() call.
        """
        ...

    def poll(self) -> None:
        """Pump the backend's event loop. Must be called periodically by the host UI
        for on_track_end callbacks to fire. No-op for backends that don't need it.
        """
        ...
