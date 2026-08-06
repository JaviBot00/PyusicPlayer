"""Config port — Protocol for configuration persistence.

Phase 1 scope: volume, repeat_mode, shuffle, last_playlist_path.
Extend AppConfig fields in future phases (layout, visualizer, i18n, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol


@dataclass
class AppConfig:
    """Persistent application state."""

    volume: float = 0.7
    repeat_mode: str = "none"   # "none" | "one" | "all"
    shuffle: bool = False
    last_playlist_path: Optional[str] = None


class ConfigPort(Protocol):
    """Adapter interface for config persistence."""

    def load(self) -> AppConfig:
        """Load config from disk. Returns defaults if file missing."""
        ...

    def save(self, config: AppConfig) -> None:
        """Atomically persist config to disk."""
        ...

    def get_config_path(self) -> Path:
        """Path to the config file (for diagnostics / tests)."""
        ...
