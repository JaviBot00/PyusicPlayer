"""Tests for core.services.PlayerService using fake AudioPort/MetadataPort
test doubles. These are pure business-logic tests: no pygame, no mutagen,
no filesystem I/O, so they run in milliseconds and don't need audio fixtures.

Real-backend behavior (pygame quirks, mutagen format handling) is covered
separately in tests/adapters/.
"""

from __future__ import annotations

from typing import Callable, Optional

import pytest

from pyusicplayer.core.ports import AudioMetadata, PlaybackState
from pyusicplayer.core.services import PlayerService


class FakeAudioPort:
    """In-memory AudioPort double: tracks state without touching real audio."""

    def __init__(self) -> None:
        self.loaded_file: Optional[str] = None
        self.state = PlaybackState.STOPPED
        self.position = 0.0
        self.volume = 0.7
        self._on_track_end: Optional[Callable[[], None]] = None
        self.play_calls = 0
        self.pause_calls = 0
        self.stop_calls = 0

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def load(self, file_path: str) -> None:
        self.loaded_file = file_path
        self.position = 0.0
        self.state = PlaybackState.STOPPED

    def play(self) -> None:
        self.play_calls += 1
        self.state = PlaybackState.PLAYING

    def pause(self) -> None:
        self.pause_calls += 1
        self.state = PlaybackState.PAUSED

    def stop(self) -> None:
        self.stop_calls += 1
        self.state = PlaybackState.STOPPED
        self.position = 0.0

    def seek(self, position_seconds: float) -> None:
        self.position = position_seconds

    def get_position(self) -> float:
        return self.position

    def get_duration(self) -> float:
        return 0.0  # matches the real pygame adapter's documented contract

    def get_state(self) -> PlaybackState:
        return self.state

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def get_volume(self) -> float:
        return self.volume

    def is_track_loaded(self) -> bool:
        return self.loaded_file is not None

    def on_track_end(self, callback: Callable[[], None]) -> None:
        self._on_track_end = callback

    def poll(self) -> None:
        pass

    def simulate_track_end(self) -> None:
        """Test helper: fire the registered end-of-track callback."""
        if self._on_track_end:
            self._on_track_end()


class FakeMetadataPort:
    """In-memory MetadataPort double with a pre-seeded duration table."""

    def __init__(self, durations: Optional[dict[str, float]] = None) -> None:
        self.durations = durations or {}

    def extract(self, file_path: str) -> AudioMetadata:
        if file_path == "missing.mp3":
            raise FileNotFoundError(file_path)
        if file_path.endswith(".xyz"):
            raise ValueError("unsupported")
        return AudioMetadata(file_path=file_path, duration=self.durations.get(file_path, 100.0))

    def get_cover(self, file_path: str):
        return None

    def supports_format(self, file_path: str) -> bool:
        return not file_path.endswith(".xyz")


@pytest.fixture()
def fake_audio() -> FakeAudioPort:
    return FakeAudioPort()


@pytest.fixture()
def service(fake_audio: FakeAudioPort) -> PlayerService:
    return PlayerService(audio=fake_audio, metadata=FakeMetadataPort())


class TestAddFiles:
    def test_add_files_skips_missing_and_unsupported(self, service: PlayerService):
        added = service.add_files(["a.mp3", "missing.mp3", "b.xyz", "c.mp3"])
        assert added == 2
        assert service.playlist.length == 2

    def test_add_files_populates_track_duration_from_metadata(self):
        audio = FakeAudioPort()
        svc = PlayerService(audio=audio, metadata=FakeMetadataPort({"a.mp3": 42.0}))
        svc.add_files(["a.mp3"])
        assert svc.playlist.tracks[0].duration == 42.0


class TestDurationFallback:
    """Regression guard: duration MUST come from Track metadata, not the
    audio backend, since pygame (and possibly other backends) can't report
    it reliably for every format."""

    def test_get_duration_prefers_track_metadata(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3"])
        service.play_index(0)
        assert service.get_duration() == 100.0  # from FakeMetadataPort, not fake_audio (which returns 0.0)

    def test_get_duration_falls_back_to_audio_backend_if_track_has_none(self, fake_audio: FakeAudioPort):
        metadata = FakeMetadataPort({"a.mp3": None})
        # simulate a track with no duration info at all
        svc = PlayerService(audio=fake_audio, metadata=metadata)
        svc.add_files(["a.mp3"])
        svc.playlist.tracks[0].duration = None
        svc.play_index(0)
        assert svc.get_duration() == 0.0  # from fake_audio.get_duration()


class TestPlaybackTransitions:
    def test_play_index_loads_and_plays(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3", "b.mp3"])
        service.play_index(1)
        assert fake_audio.loaded_file == "b.mp3"
        assert fake_audio.state == PlaybackState.PLAYING
        assert service.playlist.current_index == 1

    def test_play_index_out_of_range_returns_none(self, service: PlayerService):
        service.add_files(["a.mp3"])
        assert service.play_index(5) is None

    def test_toggle_play_pause_pauses_when_playing(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3"])
        service.play_index(0)
        service.toggle_play_pause()
        assert fake_audio.state == PlaybackState.PAUSED

    def test_toggle_play_pause_resumes_when_paused(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3"])
        service.play_index(0)
        service.pause()
        service.toggle_play_pause()
        assert fake_audio.state == PlaybackState.PLAYING

    def test_next_track_at_end_of_sequential_playlist_stops(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3"])
        service.play_index(0)
        result = service.next_track()
        assert result is None
        # PlayerService itself doesn't auto-stop on manual next_track();
        # only the on_track_end handler does that (tested below).

    def test_volume_is_clamped(self, service: PlayerService):
        service.volume = 1.5
        assert service.volume == 1.0
        service.volume = -0.3
        assert service.volume == 0.0


class TestSeekClamping:
    def test_seek_clamps_to_duration(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3"])  # duration 100.0 from FakeMetadataPort
        service.play_index(0)
        service.seek(500.0)
        assert fake_audio.position == 100.0

    def test_seek_clamps_negative_to_zero(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3"])
        service.play_index(0)
        service.seek(-10.0)
        assert fake_audio.position == 0.0


class TestAutoAdvanceOnTrackEnd:
    def test_track_end_advances_to_next_track(self, service: PlayerService, fake_audio: FakeAudioPort):
        service.add_files(["a.mp3", "b.mp3"])
        service.play_index(0)
        fake_audio.simulate_track_end()
        assert service.playlist.current_index == 1
        assert fake_audio.loaded_file == "b.mp3"

    def test_track_end_at_last_track_stops_instead_of_crashing(
        self, service: PlayerService, fake_audio: FakeAudioPort
    ):
        service.add_files(["a.mp3"])
        service.play_index(0)
        fake_audio.simulate_track_end()
        assert fake_audio.state == PlaybackState.STOPPED

    def test_track_end_with_loop_all_wraps_around(self, fake_audio: FakeAudioPort):
        from pyusicplayer.core.models import PlaylistMode

        svc = PlayerService(audio=fake_audio, metadata=FakeMetadataPort())
        svc.add_files(["a.mp3", "b.mp3"])
        svc.playlist.mode = PlaylistMode.ALL
        svc.play_index(1)
        fake_audio.simulate_track_end()
        assert svc.playlist.current_index == 0
        assert fake_audio.state == PlaybackState.PLAYING


class TestPreviousTrackRestartThreshold:
    """previous_track() behavior depends on playback position:
      - position > PREVIOUS_TRACK_RESTART_THRESHOLD_SECONDS -> restart current track (seek to 0)
      - position <= threshold -> go to the actual previous track
    """

    def test_beyond_threshold_restarts_current_track_instead_of_going_back(
        self, service: PlayerService, fake_audio: FakeAudioPort
    ):
        service.add_files(["a.mp3", "b.mp3"])
        service.play_index(1)
        fake_audio.position = 6.0  # > 5s threshold

        service.previous_track()

        assert service.playlist.current_index == 1  # stayed on b.mp3
        assert fake_audio.loaded_file == "b.mp3"  # not reloaded
        assert fake_audio.position == 0.0  # seeked to start

    def test_within_threshold_goes_to_actual_previous_track(
        self, service: PlayerService, fake_audio: FakeAudioPort
    ):
        service.add_files(["a.mp3", "b.mp3"])
        service.play_index(1)
        fake_audio.position = 3.0  # <= 5s threshold

        service.previous_track()

        assert service.playlist.current_index == 0  # moved to a.mp3
        assert fake_audio.loaded_file == "a.mp3"

    def test_exactly_at_threshold_goes_to_actual_previous_track(
        self, service: PlayerService, fake_audio: FakeAudioPort
    ):
        service.add_files(["a.mp3", "b.mp3"])
        service.play_index(1)
        fake_audio.position = 5.0  # == threshold, inclusive -> goes back

        service.previous_track()

        assert service.playlist.current_index == 0

    def test_restart_does_not_fire_on_track_change_callback(
        self, service: PlayerService, fake_audio: FakeAudioPort
    ):
        """Restarting the current track is NOT a track change - no new
        metadata to show, no playlist highlight to move."""
        service.add_files(["a.mp3", "b.mp3"])
        service.play_index(1)
        fake_audio.position = 6.0

        received = []
        service.on_track_change(lambda track: received.append(track.file_path))
        service.previous_track()

        assert received == []

    def test_previous_at_first_track_beyond_threshold_still_restarts(
        self, service: PlayerService, fake_audio: FakeAudioPort
    ):
        """Even with no earlier track to go back to, restarting is still
        correct if we're past the threshold."""
        service.add_files(["a.mp3"])
        service.play_index(0)
        fake_audio.position = 6.0

        service.previous_track()

        assert service.playlist.current_index == 0
        assert fake_audio.position == 0.0

    def test_previous_at_first_track_within_threshold_reloads_same_track(
        self, service: PlayerService, fake_audio: FakeAudioPort
    ):
        """With a single track, previous_index() clamps to 0 (existing
        Playlist behavior, unrelated to this feature) - so it reloads track
        0, it doesn't return None. Documenting this so it isn't mistaken
        for a regression later."""
        service.add_files(["a.mp3"])
        service.play_index(0)
        fake_audio.position = 1.0

        result = service.previous_track()

        assert result is not None
        assert service.playlist.current_index == 0

    def test_no_current_track_returns_none(self, service: PlayerService):
        """Empty playlist, nothing loaded - previous_index() returns -1."""
        result = service.previous_track()
        assert result is None


class TestCallbacks:
    def test_on_track_change_fires_with_the_new_track(self, service: PlayerService):
        received = []
        service.on_track_change(lambda track: received.append(track.file_path))
        service.add_files(["a.mp3"])
        service.play_index(0)
        assert received == ["a.mp3"]

    def test_on_state_change_fires_on_play_pause_stop(self, service: PlayerService):
        states = []
        service.on_state_change(lambda s: states.append(s))
        service.add_files(["a.mp3"])
        service.play_index(0)  # -> PLAYING
        service.pause()  # -> PAUSED
        service.stop()  # -> STOPPED
        assert states == [PlaybackState.PLAYING, PlaybackState.PAUSED, PlaybackState.STOPPED]
