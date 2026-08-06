"""Tests for JsonConfigAdapter.

All tests use tmp_path — no real filesystem side effects.
"""

import json
import pytest
from pathlib import Path

from pyusicplayer.adapters.config.json_adapter import JsonConfigAdapter
from pyusicplayer.core.ports.config import AppConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_adapter(tmp_path: Path) -> JsonConfigAdapter:
    return JsonConfigAdapter(config_path=tmp_path / "config.json")


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------

class TestLoad:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        adapter = make_adapter(tmp_path)
        config = adapter.load()
        assert isinstance(config, AppConfig)
        assert config.volume == 0.7
        assert config.repeat_mode == "none"
        assert config.shuffle is False
        assert config.last_playlist_path is None

    def test_loads_saved_values(self, tmp_path):
        adapter = make_adapter(tmp_path)
        original = AppConfig(volume=0.5, repeat_mode="all", shuffle=True,
                             last_playlist_path="/music/rock.m3u")
        adapter.save(original)

        loaded = adapter.load()
        assert loaded.volume == 0.5
        assert loaded.repeat_mode == "all"
        assert loaded.shuffle is True
        assert loaded.last_playlist_path == "/music/rock.m3u"

    def test_unknown_keys_in_file_are_ignored(self, tmp_path):
        """Forward-compat: future keys must not crash older code."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "volume": 0.3,
            "future_key_not_in_dataclass": "ignored",
        }))
        adapter = JsonConfigAdapter(config_path=config_file)
        config = adapter.load()
        assert config.volume == 0.3

    def test_corrupted_file_returns_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("{ not valid json }")
        adapter = JsonConfigAdapter(config_path=config_file)
        config = adapter.load()
        assert config.volume == 0.7  # default

    def test_volume_clamped_on_load(self, tmp_path):
        """Out-of-range values written externally must be clamped."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"volume": 2.5}))
        adapter = JsonConfigAdapter(config_path=config_file)
        config = adapter.load()
        assert 0.0 <= config.volume <= 1.0


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------

class TestSave:
    def test_file_is_created(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.save(AppConfig())
        assert adapter.get_config_path().exists()

    def test_save_is_valid_json(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.save(AppConfig(volume=0.4))
        raw = adapter.get_config_path().read_text()
        data = json.loads(raw)
        assert data["volume"] == pytest.approx(0.4)

    def test_save_overwrites_previous(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.save(AppConfig(volume=0.1))
        adapter.save(AppConfig(volume=0.9))
        loaded = adapter.load()
        assert loaded.volume == pytest.approx(0.9)

    def test_save_is_atomic(self, tmp_path):
        """Partial write must not corrupt existing config.

        We can't easily simulate a crash mid-write, but we verify
        that get_config_path() is NOT the temp file (i.e. rename happened).
        """
        adapter = make_adapter(tmp_path)
        adapter.save(AppConfig(volume=0.6))
        path = adapter.get_config_path()
        assert path.suffix == ".json"
        assert path.exists()
        # No stray .tmp files
        assert not any(tmp_path.glob("*.tmp"))


# ---------------------------------------------------------------------------
# get_config_path()
# ---------------------------------------------------------------------------

class TestGetConfigPath:
    def test_returns_path_object(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert isinstance(adapter.get_config_path(), Path)

    def test_path_ends_with_json(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.get_config_path().suffix == ".json"
