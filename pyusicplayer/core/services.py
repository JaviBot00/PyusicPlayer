"""Core services - business logic layer. Depends only on ports, never adapters."""

from __future__ import annotations

from typing import Callable, Optional

from .models import Playlist, Track
from .ports import AudioPort, MetadataPort, PlaybackState


class PlayerService:
    """Coordinates the audio backend with playlist state.

    Duration is authoritative from Track.duration (populated by MetadataPort at
    add-time), NOT from AudioPort.get_duration(): several audio backends (pygame
    included) cannot report duration for all formats. get_duration() here falls
    back to the audio backend only if the track's own metadata is missing.
    """

    #: previous_track() restarts the current track (seek to 0) instead of
    #: actually moving to the prior track when playback position is beyond
    #: this many seconds - mirrors the "double-tap previous" convention used
    #: by most media players. Change freely; nothing else depends on 5.0.
    PREVIOUS_TRACK_RESTART_THRESHOLD_SECONDS: float = 5.0

    def __init__(self, audio: AudioPort, metadata: MetadataPort):
        self._audio = audio
        self._metadata = metadata
        self._playlist = Playlist()
        self._volume = 0.7
        self._on_track_change: Optional[Callable[[Track], None]] = None
        self._on_state_change: Optional[Callable[[PlaybackState], None]] = None
        self._audio.on_track_end(self._handle_track_end)

    @property
    def playlist(self) -> Playlist:
        return self._playlist

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))
        self._audio.set_volume(self._volume)

    def on_track_change(self, callback: Callable[[Track], None]) -> None:
        self._on_track_change = callback

    def on_state_change(self, callback: Callable[[PlaybackState], None]) -> None:
        self._on_state_change = callback

    def initialize(self) -> None:
        self._audio.initialize()
        self._audio.set_volume(self._volume)

    def shutdown(self) -> None:
        self._audio.shutdown()

    def poll(self) -> None:
        """Must be called periodically by the UI event loop (drives on_track_end)."""
        self._audio.poll()

    def add_files(self, file_paths: list[str]) -> int:
        """Extract metadata and add tracks to the playlist. Returns count added."""
        added = 0
        for path in file_paths:
            try:
                meta = self._metadata.extract(path)
            except (FileNotFoundError, ValueError):
                continue
            track = Track(
                file_path=path,
                title=meta.title,
                artist=meta.artist,
                album=meta.album,
                duration=meta.duration,
                track_number=meta.track_number,
                disc_number=meta.disc_number,
            )
            self._playlist.add_track(track)
            added += 1
        return added

    def clear_playlist(self) -> None:
        self.stop()
        self._playlist.clear()

    def _load_and_play(self, track: Track) -> None:
        self._audio.load(track.file_path)
        if self._on_track_change:
            self._on_track_change(track)
        self.play()

    def play_index(self, index: int) -> Optional[Track]:
        if 0 <= index < self._playlist.length:
            self._playlist.current_index = index
            track = self._playlist.current_track
            if track:
                self._load_and_play(track)
                return track
        return None

    def next_track(self) -> Optional[Track]:
        idx = self._playlist.advance()
        if idx < 0:
            return None
        track = self._playlist.current_track
        if track:
            self._load_and_play(track)
        return track

    def previous_track(self) -> Optional[Track]:
        """Go to the previous track, UNLESS we're more than
        PREVIOUS_TRACK_RESTART_THRESHOLD_SECONDS into the current one, in
        which case restart the current track instead (standard "double-tap
        previous" behavior). Restarting does NOT fire on_track_change -
        it's the same track, nothing new to display."""
        current = self._playlist.current_track
        if current is not None and self.get_position() > self.PREVIOUS_TRACK_RESTART_THRESHOLD_SECONDS:
            self._audio.seek(0.0)
            return current

        idx = self._playlist.previous_index()
        if idx < 0:
            return None
        self._playlist.current_index = idx
        track = self._playlist.current_track
        if track:
            self._load_and_play(track)
        return track

    def play(self) -> None:
        self._audio.play()
        if self._on_state_change:
            self._on_state_change(PlaybackState.PLAYING)

    def pause(self) -> None:
        self._audio.pause()
        if self._on_state_change:
            self._on_state_change(PlaybackState.PAUSED)

    def stop(self) -> None:
        self._audio.stop()
        if self._on_state_change:
            self._on_state_change(PlaybackState.STOPPED)

    def toggle_play_pause(self) -> None:
        if self._audio.get_state() == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()

    def seek(self, position_seconds: float) -> None:
        duration = self.get_duration()
        clamped = max(0.0, min(position_seconds, duration)) if duration else max(0.0, position_seconds)
        self._audio.seek(clamped)

    def get_position(self) -> float:
        return self._audio.get_position()

    def get_duration(self) -> float:
        track = self._playlist.current_track
        if track and track.duration:
            return track.duration
        return self._audio.get_duration()

    def get_state(self) -> PlaybackState:
        return self._audio.get_state()

    def _handle_track_end(self) -> None:
        """Called by the audio backend when a track finishes on its own."""
        if self.next_track() is None:
            self.stop()
