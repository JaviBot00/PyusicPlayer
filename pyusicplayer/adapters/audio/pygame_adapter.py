"""Pygame audio adapter implementation.

IMPORTANT — verified empirically against pygame 2.6.1 / SDL 2.28.4 (mp3, ogg, wav):

1. pygame.mixer.music.set_pos() does NOT change playback position for any of
   mp3/ogg/wav in this environment; it is silently a no-op. The only reliable
   seek mechanism is reloading the file and calling
   play(loops, start=position_seconds).
2. pygame.mixer.music.get_pos() returns milliseconds *since the last play()
   or unpause() call*, NOT the absolute position in the track. It resets to 0
   every time play() is called (including for a seek-reload). This adapter
   therefore keeps its own `_position_offset` and adds get_pos() on top of it.
3. pause()/unpause() (without reloading) DO preserve true position correctly —
   verified: get_pos() continues linearly across a pause/unpause cycle. Only
   seeking requires the reload workaround above.
4. Detecting natural track-end requires the *full* pygame.init() (not just
   mixer.init()) plus set_endevent()+event pump, because SDL's event queue
   needs the video subsystem initialized. On Linux without a DISPLAY (e.g. a
   TUI run over plain SSH), this raises "video system not initialized" unless
   SDL_VIDEODRIVER=dummy is set first. This adapter sets that fallback only
   when no DISPLAY is present, so it does not affect real desktop sessions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from ...core.ports.audio import PlaybackState


def _ensure_headless_video_driver() -> None:
    """Avoid 'video system not initialized' when run without a display."""
    if os.environ.get("SDL_VIDEODRIVER"):
        return
    if os.name == "posix" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ["SDL_VIDEODRIVER"] = "dummy"


class PygameAudioAdapter:
    """Audio adapter using pygame.mixer.music for playback."""

    def __init__(self) -> None:
        self._initialized = False
        self._current_file = ""
        self._state = PlaybackState.STOPPED
        self._volume = 0.7
        self._position_offset = 0.0
        self._on_track_end: Optional[Callable[[], None]] = None
        self._end_event_id: Optional[int] = None

    def initialize(self) -> None:
        if self._initialized:
            return
        _ensure_headless_video_driver()
        import pygame

        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        self._end_event_id = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self._end_event_id)
        self._initialized = True

    def shutdown(self) -> None:
        if not self._initialized:
            return
        import pygame

        pygame.mixer.music.stop()
        pygame.mixer.quit()
        pygame.quit()
        self._initialized = False

    def load(self, file_path: str) -> None:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        import pygame

        try:
            pygame.mixer.music.load(file_path)
        except pygame.error as e:
            raise ValueError(f"Cannot load file '{file_path}': {e}") from e
        self._current_file = file_path
        self._state = PlaybackState.STOPPED
        self._position_offset = 0.0

    def play(self) -> None:
        import pygame

        if self._state == PlaybackState.PAUSED:
            pygame.mixer.music.unpause()
        else:
            self._position_offset = 0.0
            pygame.mixer.music.play()
        self._state = PlaybackState.PLAYING

    def pause(self) -> None:
        if self._state != PlaybackState.PLAYING:
            return
        import pygame

        self._position_offset = self._raw_position()
        pygame.mixer.music.pause()
        self._state = PlaybackState.PAUSED

    def stop(self) -> None:
        import pygame

        pygame.mixer.music.stop()
        self._state = PlaybackState.STOPPED
        self._position_offset = 0.0

    def seek(self, position_seconds: float) -> None:
        """Reload the track and start it from position_seconds (see module docstring)."""
        if not self._current_file:
            return
        import pygame

        was_playing = self._state != PlaybackState.STOPPED
        pygame.mixer.music.load(self._current_file)
        pygame.mixer.music.play(0, start=max(0.0, position_seconds))
        self._position_offset = max(0.0, position_seconds)
        self._state = PlaybackState.PLAYING
        if not was_playing:
            pygame.mixer.music.pause()
            self._state = PlaybackState.PAUSED

    def _raw_position(self) -> float:
        """Position accumulated during the current play()/unpause() run."""
        import pygame

        if self._state == PlaybackState.PAUSED:
            return self._position_offset
        pos_ms = pygame.mixer.music.get_pos()
        elapsed = pos_ms / 1000.0 if pos_ms >= 0 else 0.0
        return self._position_offset + elapsed

    def get_position(self) -> float:
        return self._raw_position() if self._current_file else 0.0

    def get_duration(self) -> float:
        # pygame cannot report duration; PlayerService uses Track.duration
        # (from MetadataPort) instead and only falls back to this stub.
        return 0.0

    def get_state(self) -> PlaybackState:
        if self._state == PlaybackState.PLAYING:
            import pygame

            if not pygame.mixer.music.get_busy():
                self._state = PlaybackState.STOPPED
        return self._state

    def set_volume(self, volume: float) -> None:
        import pygame

        self._volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self._volume)

    def get_volume(self) -> float:
        return self._volume

    def is_track_loaded(self) -> bool:
        return bool(self._current_file)

    def on_track_end(self, callback: Callable[[], None]) -> None:
        self._on_track_end = callback

    def poll(self) -> None:
        """Pump SDL's event queue so the registered end-of-track event can fire."""
        if not self._initialized:
            return
        import pygame

        for event in pygame.event.get():
            if event.type == self._end_event_id and self._on_track_end:
                self._on_track_end()
