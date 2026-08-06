"""Pygame audio adapter implementation.

IMPORTANT — verified empirically against pygame 2.6.1 / SDL 2.28.4 (mp3, ogg, wav):

1. pygame.mixer.music.set_pos() does NOT change playback position for any of
   mp3/ogg/wav in this environment; it is silently a no-op. The only reliable
   seek mechanism is reloading the file and calling
   play(loops, start=position_seconds).
2. pygame.mixer.music.get_pos() returns milliseconds *since the last play()
   call*, and it freezes automatically during pause() and resumes linearly
   on unpause() without ever resetting to 0 on its own (verified with 4
   consecutive pause/resume cycles). This means it is ALREADY the correct
   cumulative position within a play() session — this adapter's own
   `_position_offset` must only be set on load()/seek()/fresh play(), never
   re-derived inside pause(). An earlier version of this adapter re-summed
   offset + get_pos() back into offset on every pause() call, which
   double-counted elapsed time on each pause/resume cycle (confirmed bug,
   fixed here, covered by tests/adapters/test_pygame_adapter.py).
3. Detecting natural track-end requires the *full* pygame.init() (not just
   mixer.init()) plus set_endevent()+event pump, because SDL's event queue
   needs the video subsystem initialized. On Linux without a DISPLAY (e.g. a
   TUI run over plain SSH), this raises "video system not initialized" unless
   SDL_VIDEODRIVER=dummy is set first. This adapter sets that fallback only
   when no DISPLAY is present, so it does not affect real desktop sessions.
4. pygame/SDL fires the SAME end-of-track event on an explicit stop() as it
   does on natural completion (found by a test written before this fix, not
   by manual testing). Without suppressing it, pressing Stop would trigger
   PlayerService's auto-advance-to-next-track exactly as if the song had
   finished on its own. stop() sets a one-shot suppress flag that poll()
   consumes silently. seek()'s reload+play() was checked too and does NOT
   fire a spurious event, so it needed no such guard.
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
        self._suppress_next_end_event = False

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

        pygame.mixer.music.pause()
        self._state = PlaybackState.PAUSED

    def stop(self) -> None:
        import pygame

        # pygame/SDL fires the same end-of-track event on an explicit stop()
        # as it does on natural completion (verified empirically) - without
        # this flag, pressing Stop would spuriously trigger auto-advance.
        self._suppress_next_end_event = True
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
        """Position accumulated since the current file was loaded/seeked.

        pygame's get_pos() freezes automatically during pause() and resumes
        linearly on unpause() (verified empirically) — no manual pause
        bookkeeping needed here, only _position_offset for post-seek baseline.
        """
        import pygame

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
            if event.type == self._end_event_id:
                if self._suppress_next_end_event:
                    self._suppress_next_end_event = False
                    continue
                if self._on_track_end:
                    self._on_track_end()
