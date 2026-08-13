"""Integration tests for the TUI's always-visible cover art widget.

Requires ffmpeg audio fixtures like test_tui_app.py. Three cover variants
are used from tests/conftest.py::audio_fixtures:
  - mp3 (no cover key)     -> track has no embedded art at all
  - mp3_cover               -> fake, non-decodable bytes (extraction-slice fixture)
  - mp3_real_cover          -> genuine Pillow-decodable PNG (this slice's addition)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.text import Text
from textual.widgets import Static

from pyusicplayer.adapters.config.json_adapter import JsonConfigAdapter
from pyusicplayer.core.ports.config import AppConfig, ConfigPort
from pyusicplayer.core.ports.cover_renderer import CoverRenderMode
from pyusicplayer.di.container import Container, create_container
from pyusicplayer.interfaces.tui.app import PyusicPlayerApp

pytestmark = pytest.mark.audio

_PLACEHOLDER_MARKER = "\u266a"  # matches PlaceholderCoverRenderer.MARKER


def isolated_container(tmp_path: Path, cover_render_mode: str = CoverRenderMode.PLACEHOLDER) -> Container:
    container = create_container()
    container.register_singleton(
        ConfigPort,
        JsonConfigAdapter(config_path=tmp_path / "config.json"),
    )
    JsonConfigAdapter(config_path=tmp_path / "config.json").save(
        AppConfig(cover_render_mode=cover_render_mode)
    )
    return container


@pytest.fixture()
def cover_music_folder(audio_fixtures, tmp_path) -> Path:
    """track0 = no cover, track1 = fake/non-decodable cover, track2 = real
    decodable cover - covers the three wiring paths the widget must handle."""
    folder = tmp_path / "music"
    folder.mkdir()
    (folder / "track0.mp3").write_bytes(audio_fixtures["mp3"].read_bytes())
    (folder / "track1.mp3").write_bytes(audio_fixtures["mp3_cover"].read_bytes())
    (folder / "track2.mp3").write_bytes(audio_fixtures["mp3_real_cover"].read_bytes())
    return folder


def _cover_text(app: PyusicPlayerApp) -> Text:
    text = app.cover_render_text
    assert isinstance(text, Text)
    return text


class TestCoverWidgetPresence:
    @pytest.mark.asyncio
    async def test_cover_widget_exists_on_mount(self, cover_music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), cover_music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one("#cover-art", Static)  # must not raise


class TestCoverWidgetNoTrackOrNoCover:
    @pytest.mark.asyncio
    async def test_shows_placeholder_before_any_track_plays(self, cover_music_folder, tmp_path):
        """'Always visible' means visible even at startup with nothing
        playing yet - not just after the first track loads."""
        app = PyusicPlayerApp(isolated_container(tmp_path), cover_music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert _PLACEHOLDER_MARKER in _cover_text(app).plain

    @pytest.mark.asyncio
    async def test_shows_placeholder_when_playing_track_without_cover_data(self, cover_music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.ASCII), cover_music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(0)  # track0.mp3 has no embedded cover at all
            await pilot.pause()
            assert _PLACEHOLDER_MARKER in _cover_text(app).plain


class TestCoverWidgetPlaceholderModeIgnoresRealCover:
    @pytest.mark.asyncio
    async def test_default_mode_shows_placeholder_even_with_real_cover_track(self, cover_music_folder, tmp_path):
        """Placeholder is the default AppConfig.cover_render_mode - even a
        track with a perfectly good embedded cover must not suddenly start
        decoding images the user didn't opt into."""
        app = PyusicPlayerApp(isolated_container(tmp_path), cover_music_folder)  # default mode
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(2)  # track2.mp3 = real decodable cover
            await pilot.pause()
            assert _PLACEHOLDER_MARKER in _cover_text(app).plain


class TestCoverWidgetAsciiMode:
    @pytest.mark.asyncio
    async def test_renders_real_cover_in_ascii_mode(self, cover_music_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.ASCII), cover_music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(2)  # real decodable cover
            await pilot.pause()
            text = _cover_text(app).plain
            assert _PLACEHOLDER_MARKER not in text  # real ascii pipeline ran, not the fallback

    @pytest.mark.asyncio
    async def test_ascii_mode_falls_back_to_placeholder_for_undecodable_cover(self, cover_music_folder, tmp_path):
        """track1's APIC bytes are fake (from the extraction-slice fixture) -
        Pillow cannot decode them, so FallbackCoverRenderer must catch that
        and show the placeholder instead of crashing the app."""
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.ASCII), cover_music_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(1)  # fake/non-decodable cover bytes
            await pilot.pause()
            assert _PLACEHOLDER_MARKER in _cover_text(app).plain
