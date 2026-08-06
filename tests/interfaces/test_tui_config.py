"""Integration tests for TUI ↔ ConfigPort.

Tests que el app restaura volumen/modo/shuffle al arrancar
y los persiste al salir.

No necesitan audio real — usan un container con JsonConfigAdapter
apuntando a tmp_path, y un music_folder vacío (cero tracks cargados
es válido para probar config sin reproducción).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyusicplayer.adapters.config.json_adapter import JsonConfigAdapter
from pyusicplayer.core.models import PlaylistMode
from pyusicplayer.core.ports.config import AppConfig, ConfigPort
from pyusicplayer.di.container import Container, create_container
from pyusicplayer.interfaces.tui.app import PyusicPlayerApp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_container_with_config(config_path: Path) -> Container:
    """Container real pero con ConfigPort apuntando a tmp_path."""
    container = create_container()
    container.register_singleton(ConfigPort, JsonConfigAdapter(config_path=config_path))
    return container


def empty_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "music"
    folder.mkdir()
    return folder


# ---------------------------------------------------------------------------
# Restore on startup
# ---------------------------------------------------------------------------

class TestRestoreOnMount:
    @pytest.mark.asyncio
    async def test_restores_volume_from_config(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        JsonConfigAdapter(cfg_path).save(AppConfig(volume=0.3))

        app = PyusicPlayerApp(make_container_with_config(cfg_path), empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert abs(app.player.volume - 0.3) < 0.01

    @pytest.mark.asyncio
    async def test_restores_shuffle_from_config(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        JsonConfigAdapter(cfg_path).save(AppConfig(shuffle=True))

        app = PyusicPlayerApp(make_container_with_config(cfg_path), empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.player.playlist.shuffle is True

    @pytest.mark.asyncio
    async def test_restores_repeat_mode_loop_all(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        JsonConfigAdapter(cfg_path).save(AppConfig(repeat_mode="all"))

        app = PyusicPlayerApp(make_container_with_config(cfg_path), empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.player.playlist.mode == PlaylistMode.ALL

    @pytest.mark.asyncio
    async def test_restores_repeat_mode_loop_one(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        JsonConfigAdapter(cfg_path).save(AppConfig(repeat_mode="one"))

        app = PyusicPlayerApp(make_container_with_config(cfg_path), empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.player.playlist.mode == PlaylistMode.ONE

    @pytest.mark.asyncio
    async def test_uses_defaults_when_no_config_file(self, tmp_path):
        cfg_path = tmp_path / "config.json"  # no existe

        app = PyusicPlayerApp(make_container_with_config(cfg_path), empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert abs(app.player.volume - 0.7) < 0.01
            assert app.player.playlist.shuffle is False
            assert app.player.playlist.mode == PlaylistMode.NONE


# ---------------------------------------------------------------------------
# Persist on exit
# ---------------------------------------------------------------------------

class TestPersistOnUnmount:
    @pytest.mark.asyncio
    async def test_saves_volume_on_exit(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        container = make_container_with_config(cfg_path)

        app = PyusicPlayerApp(container, empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            app.player.volume = 0.42
            await pilot.pause()

        config = JsonConfigAdapter(cfg_path).load()
        assert abs(config.volume - 0.42) < 0.01

    @pytest.mark.asyncio
    async def test_saves_shuffle_on_exit(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        container = make_container_with_config(cfg_path)

        app = PyusicPlayerApp(container, empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_toggle_shuffle()
            await pilot.pause()

        config = JsonConfigAdapter(cfg_path).load()
        assert config.shuffle is True

    @pytest.mark.asyncio
    async def test_saves_repeat_mode_on_exit(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        container = make_container_with_config(cfg_path)

        app = PyusicPlayerApp(container, empty_folder(tmp_path))
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_mode_loop_all()
            await pilot.pause()

        config = JsonConfigAdapter(cfg_path).load()
        assert config.repeat_mode == "all"
