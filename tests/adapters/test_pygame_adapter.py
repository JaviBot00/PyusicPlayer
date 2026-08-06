"""Tests for adapters.audio.pygame_adapter.PygameAudioAdapter against real
(synthetic) audio files. Requires ffmpeg to build fixtures; skipped otherwise.

These are slower than the core unit tests (real pygame mixer, real sleeps)
so they're marked with the "audio" marker (see pytest.ini) in case you want
to exclude them from a fast local loop with `-m "not audio"`.
"""

from __future__ import annotations

import time

import pytest

from pyusicplayer.adapters.audio.pygame_adapter import PygameAudioAdapter
from pyusicplayer.core.ports.audio import PlaybackState

pytestmark = pytest.mark.audio


@pytest.fixture()
def adapter():
    a = PygameAudioAdapter()
    a.initialize()
    yield a
    a.shutdown()


class TestLoadErrors:
    def test_load_missing_file_raises_file_not_found(self, adapter: PygameAudioAdapter):
        with pytest.raises(FileNotFoundError):
            adapter.load("/nonexistent/path/song.mp3")


class TestBasicPlayback:
    def test_play_transitions_to_playing(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.play()
        assert adapter.get_state() == PlaybackState.PLAYING

    def test_position_advances_while_playing(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.play()
        time.sleep(0.4)
        assert adapter.get_position() > 0.2

    def test_stop_resets_position(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.play()
        time.sleep(0.3)
        adapter.stop()
        assert adapter.get_position() == 0.0
        assert adapter.get_state() == PlaybackState.STOPPED


class TestPauseResumeRegression:
    """Regression test for a real bug found in manual testing: pause() used
    to re-derive _position_offset from the already-cumulative get_pos(),
    doubling the elapsed time on every pause/resume cycle. get_pos() itself
    already freezes correctly on pause and resumes linearly on unpause
    without ever needing that extra bookkeeping."""

    def test_position_frozen_during_a_single_pause(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.play()
        time.sleep(0.3)
        adapter.pause()
        pos1 = adapter.get_position()
        time.sleep(0.2)
        pos2 = adapter.get_position()
        assert abs(pos2 - pos1) < 0.05

    def test_no_drift_across_repeated_pause_resume_cycles(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.play()
        for _ in range(4):
            time.sleep(0.3)
            pos_before_pause = adapter.get_position()
            adapter.pause()
            time.sleep(0.15)
            pos_while_paused = adapter.get_position()
            # The core regression check: pausing must not add time on top of
            # what was already elapsed.
            assert abs(pos_while_paused - pos_before_pause) < 0.05, (
                f"position drifted on pause: {pos_before_pause} -> {pos_while_paused}"
            )
            adapter.play()  # resume

        final_position = adapter.get_position()
        # ~4 * 0.3s = 1.2s of actual playback time elapsed; a healthy margin
        # around that catches gross double-counting (which would show ~2x+).
        assert 0.9 <= final_position <= 2.0, f"expected ~1.2s, got {final_position}"


class TestSeek:
    def test_seek_moves_position_near_target(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.play()
        adapter.seek(3.0)
        assert 2.8 <= adapter.get_position() <= 3.3

    def test_position_keeps_advancing_after_seek(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.play()
        adapter.seek(3.0)
        pos_after_seek = adapter.get_position()
        time.sleep(0.3)
        assert adapter.get_position() > pos_after_seek

    def test_seek_while_stopped_leaves_paused_state(self, adapter: PygameAudioAdapter, audio_fixtures):
        adapter.load(str(audio_fixtures["mp3"]))
        adapter.seek(2.0)
        assert adapter.get_state() == PlaybackState.PAUSED


class TestTrackEndDetection:
    def test_on_track_end_fires_after_natural_completion(self, adapter: PygameAudioAdapter, audio_fixtures):
        ended = []
        adapter.on_track_end(lambda: ended.append(True))
        adapter.load(str(audio_fixtures["short_mp3"]))  # ~1s clip
        adapter.play()

        start = time.time()
        while time.time() - start < 2.5 and not ended:
            adapter.poll()
            time.sleep(0.05)

        assert ended, "on_track_end callback never fired within 2.5s for a ~1s clip"

    def test_on_track_end_does_not_fire_on_explicit_stop(self, adapter: PygameAudioAdapter, audio_fixtures):
        """Regression test: pygame/SDL fires the SAME end-of-track event on
        an explicit stop() as it does on natural completion. Discovered by
        this test (written before the fix), not by manual testing."""
        ended = []
        adapter.on_track_end(lambda: ended.append(True))
        adapter.load(str(audio_fixtures["mp3"]))  # ~5s clip
        adapter.play()
        time.sleep(0.2)
        adapter.stop()
        adapter.poll()
        assert not ended


class TestVolume:
    def test_volume_is_clamped(self, adapter: PygameAudioAdapter):
        adapter.set_volume(1.5)
        assert adapter.get_volume() == 1.0
        adapter.set_volume(-0.5)
        assert adapter.get_volume() == 0.0
