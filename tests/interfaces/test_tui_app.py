"""Integration tests for the Textual TUI, using Textual's own test harness
(App.run_test()) instead of mocking the framework. Requires ffmpeg-built
audio fixtures like the adapter tests.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from pyusicplayer.adapters.config.json_adapter import JsonConfigAdapter
from pyusicplayer.core.ports.config import ConfigPort
from pyusicplayer.di.container import Container, create_container
from pyusicplayer.interfaces.tui.app import PyusicPlayerApp, TrackListItem
from textual.widgets import ListView

pytestmark = pytest.mark.audio


def isolated_container(tmp_path: Path) -> Container:
    """create_container() but with ConfigPort pointed at tmp_path, so tests
    never read/write the real project's ./data/config.json (which may hold
    state - e.g. shuffle=True - left over from manual runs)."""
    container = create_container()
    container.register_singleton(
        ConfigPort, JsonConfigAdapter(config_path=tmp_path / "config.json")
    )
    return container


@pytest.fixture()
def music_folder(audio_fixtures, tmp_path) -> Path:
    """A folder containing a couple of the generated fixtures, laid out like
    a real music library so scan_music_folder() has something to find."""
    folder = tmp_path / "music"
    folder.mkdir()
    for i, fmt in enumerate(["mp3", "ogg", "flac", "m4a"]):
        target = folder / f"song{i}.{fmt}"
        target.write_bytes(audio_fixtures[fmt].read_bytes())
    return folder


@pytest.fixture()
def short_music_folder(audio_fixtures, tmp_path) -> Path:
    """Two ~1s clips, for auto-advance-on-track-end tests."""
    folder = tmp_path / "short_music"
    folder.mkdir()
    (folder / "a.mp3").write_bytes(audio_fixtures["short_mp3"].read_bytes())
    (folder / "b.mp3").write_bytes(audio_fixtures["short_mp3_2"].read_bytes())
    return folder


class TestPlaylistLoading:
    @pytest.mark.asyncio
    async def test_scans_and_loads_all_tracks(self, music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.player.playlist.length == 4


class TestNowPlayingIndicator:
    @pytest.mark.asyncio
    async def test_playing_track_gets_highlighted(self, music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(0)
            await pilot.pause()

            list_view = app.query_one("#playlist-view", ListView)
            items = [c for c in list_view.children if isinstance(c, TrackListItem)]
            assert items[0].has_class("now-playing")
            assert not items[1].has_class("now-playing")

    @pytest.mark.asyncio
    async def test_highlight_moves_when_track_changes(self, music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(0)
            await pilot.pause()
            app.player.next_track()
            await pilot.pause()

            list_view = app.query_one("#playlist-view", ListView)
            items = [c for c in list_view.children if isinstance(c, TrackListItem)]
            assert not items[0].has_class("now-playing")
            assert items[1].has_class("now-playing")


class TestModeShuffleIndicatorBar:
    @pytest.mark.asyncio
    async def test_sequential_is_active_by_default(self, music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "[reverse]" in app.mode_bar_text
            assert "Seq" in app.mode_bar_text

    @pytest.mark.asyncio
    async def test_toggling_shuffle_updates_bar_immediately(self, music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_toggle_shuffle()
            await pilot.pause()
            assert "[reverse]" in app.mode_bar_text and "Shuffle" in app.mode_bar_text

    @pytest.mark.asyncio
    async def test_switching_mode_updates_bar_immediately(self, music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_mode_loop_all()
            await pilot.pause()
            assert "[reverse] \U0001F501 All [/]" in app.mode_bar_text

    @pytest.mark.asyncio
    async def test_loop_all_keybinding_actually_triggers_via_keypress(self, music_folder, tmp_path):
        """Regression: the Shift+L binding never fired for real keypresses -
        action_mode_loop_all() worked fine when called directly (as the test
        above does), but the BINDINGS entry itself was dead. This test must
        drive it through pilot.press(), not call the action method directly,
        or it would pass even with the bug present."""
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("L")
            await pilot.pause()
            assert "[reverse] \U0001F501 All [/]" in app.mode_bar_text

    @pytest.mark.asyncio
    async def test_loop_one_keybinding_still_works_via_keypress(self, music_folder, tmp_path):
        """Sanity check that lowercase l (loop one) keeps working after the
        fix - the two bindings must not clash with each other."""
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()
            assert "[reverse] \U0001F502 One [/]" in app.mode_bar_text


class TestPauseResumeAtAppLevel:
    """Same double-counting regression as the adapter-level test, but
    exercised through the actual app/service stack a real user drives via
    the space bar, not just the raw adapter."""

    @pytest.mark.asyncio
    async def test_no_drift_across_toggle_play_cycles(self, music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(0)
            await pilot.pause()

            for _ in range(3):
                await asyncio.sleep(0.3)
                pos_before = app.player.get_position()
                app.action_toggle_play()  # pause
                await pilot.pause()
                await asyncio.sleep(0.15)
                pos_paused = app.player.get_position()
                assert abs(pos_paused - pos_before) < 0.05
                app.action_toggle_play()  # resume
                await pilot.pause()


class TestAutoAdvance:
    @pytest.mark.asyncio
    async def test_short_tracks_auto_advance_and_stop_at_end(self, short_music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), short_music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(0)
            await pilot.pause()

            start = time.time()
            while time.time() - start < 2.5:
                app._tick()
                await asyncio.sleep(0.05)

            assert app.player.playlist.current_index == 1
