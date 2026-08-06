"""JSON-backed config adapter.

Write strategy: write to .tmp sibling, then os.replace() — atomic on POSIX,
best-effort on Windows (os.replace is atomic there too since Python 3.3+).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, fields
from pathlib import Path
from typing import Optional

from ...core.ports.config import AppConfig, ConfigPort


class JsonConfigAdapter:
    """Persists AppConfig as a JSON file."""

    def __init__(self, config_path: Path) -> None:
        self._path = config_path

    # ------------------------------------------------------------------
    # ConfigPort implementation
    # ------------------------------------------------------------------

    def load(self) -> AppConfig:
        if not self._path.exists():
            return AppConfig()

        try:
            raw = self._path.read_text(encoding="utf-8")
            data: dict = json.loads(raw)
        except Exception:
            return AppConfig()

        # Only pass keys that AppConfig actually knows about.
        known = {f.name for f in fields(AppConfig)}
        filtered = {k: v for k, v in data.items() if k in known}

        config = AppConfig(**filtered)
        config.volume = max(0.0, min(1.0, config.volume))
        return config

    def save(self, config: AppConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(asdict(config), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp, self._path)
        finally:
            # Clean up .tmp if os.replace failed
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def get_config_path(self) -> Path:
        return self._path
