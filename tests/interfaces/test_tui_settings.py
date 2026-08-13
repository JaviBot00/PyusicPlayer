"""Integration tests for the settings screen: changing cover_render_mode
at runtime, persisting it, and having the cover widget reflect it
immediately (no restart required).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.text import Text

from pyusicplayer.adapters.config.json_adapter import JsonConfigAdapter
from pyusicplayer.core.ports.config import AppConfig, ConfigPort
from pyusicplayer.core.ports.cover_renderer import CoverRenderMode
from pyusicplayer.di.container import Container, create_container
from pyusicplayer.interfaces.tui.app import PyusicPlayerApp
from pyusicplayer.interfaces.tui.screens.settings_screen import SettingsScreen

pytestmark = pytest.mark.audio

_PLACEHOLDER_MARKER = "\u266a"


def isolated_container(tmp_path: Path, cover_render_mode: str = CoverRenderMode.PLACEHOLDER) -> Container:
    container = create_container()
    cfg_path = tmp_path / "config.json"
    container.register_singleton(ConfigPort, JsonConfigAdapter(config_path=cfg_path))
    JsonConfigAdapter(config_path=cfg_path).save(AppConfig(cover_render_mode=cover_render_mode))
    return container


@pytest.fixture()
def real_cover_folder(audio_fixtures, tmp_path) -> Path:
    folder = tmp_path / "music"
    folder.mkdir()
    (folder / "track0.mp3").write_bytes(audio_fixtures["mp3_real_cover"].read_bytes())
    return folder


class TestOpenSettings:
    @pytest.mark.asyncio
    async def test_keybinding_opens_settings_screen(self, real_cover_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path), real_cover_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press(",")
            await pilot.pause()
            assert isinstance(app.screen, SettingsScreen)

    @pytest.mark.asyncio
    async def test_escape_closes_settings_without_changing_mode(self, real_cover_folder, tmp_path):
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.PLACEHOLDER), real_cover_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press(",")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert app._cover_render_mode == CoverRenderMode.PLACEHOLDER


class TestChangingModeAtRuntime:
    @pytest.mark.asyncio
    async def test_keyboard_driven_selection_updates_app_mode(self, real_cover_folder, tmp_path):
        """Regression-shaped test: drives selection through real keypresses,
        not by calling _on_settings_closed directly, since this project has
        already been bitten once (loop-all/Shift+L) by a binding that worked
        when the action was called directly but never fired for real input.
        Starts at PLACEHOLDER (index 2 in _MODE_OPTIONS); one 'up' reaches
        ASCII (index 1).
        """
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.PLACEHOLDER), real_cover_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press(",")
            await pilot.pause()
            await pilot.press("up")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app._cover_render_mode == CoverRenderMode.ASCII

    @pytest.mark.asyncio
    async def test_selecting_a_mode_persists_to_disk(self, real_cover_folder, tmp_path):
        cfg_path = tmp_path / "config.json"
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.PLACEHOLDER), real_cover_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(SettingsScreen(app._cover_render_mode), app._on_settings_closed)
            await pilot.pause()
            app.screen.dismiss(CoverRenderMode.ASCII)
            await pilot.pause()

        saved = JsonConfigAdapter(config_path=cfg_path).load()
        assert saved.cover_render_mode == CoverRenderMode.ASCII

    @pytest.mark.asyncio
    async def test_selecting_a_mode_rerenders_current_track_immediately(self, real_cover_folder, tmp_path):
        """No restart needed: switching to ascii mode while a track with a
        real cover is already playing must re-render right away."""
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.PLACEHOLDER), real_cover_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.play_index(0)
            await pilot.pause()
            assert _PLACEHOLDER_MARKER in app.cover_render_text.plain  # placeholder mode, as configured

            app.push_screen(SettingsScreen(app._cover_render_mode), app._on_settings_closed)
            await pilot.pause()
            app.screen.dismiss(CoverRenderMode.ASCII)
            await pilot.pause()

            assert _PLACEHOLDER_MARKER not in app.cover_render_text.plain

    @pytest.mark.asyncio
    async def test_cancelling_settings_does_not_touch_disk(self, real_cover_folder, tmp_path):
        cfg_path = tmp_path / "config.json"
        app = PyusicPlayerApp(isolated_container(tmp_path, CoverRenderMode.PLACEHOLDER), real_cover_folder)
        async with app.run_test() as pilot:
            await pilot.pause()
            before_mtime = cfg_path.stat().st_mtime_ns
            app.push_screen(SettingsScreen(app._cover_render_mode), app._on_settings_closed)
            await pilot.pause()
            app.screen.dismiss(None)  # cancelled
            await pilot.pause()
            after_mtime = cfg_path.stat().st_mtime_ns
            assert before_mtime == after_mtime
