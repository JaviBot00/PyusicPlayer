"""create_cover_renderer() - selects a CoverRendererPort adapter by
AppConfig.cover_render_mode.

Terminal truecolor capability (COLORTERM) is checked HERE, at selection
time, not inside TruecolorBlockCoverRenderer.render(). A session without
24-bit color support should never even attempt the truecolor pipeline -
see AGENT.md "Cover render fallback" for why this is a hard requirement,
not just a nicety.
"""

from __future__ import annotations

import os

from pyusicplayer.adapters.cover_renderer.ascii_renderer import AsciiCoverRenderer
from pyusicplayer.adapters.cover_renderer.fallback_renderer import FallbackCoverRenderer
from pyusicplayer.adapters.cover_renderer.placeholder_renderer import PlaceholderCoverRenderer
from pyusicplayer.adapters.cover_renderer.truecolor_renderer import TruecolorBlockCoverRenderer
from pyusicplayer.core.ports.cover_renderer import CoverRenderMode, CoverRendererPort

_TRUECOLOR_COLORTERM_VALUES = {"truecolor", "24bit"}


def _terminal_supports_truecolor() -> bool:
    return os.environ.get("COLORTERM", "").lower() in _TRUECOLOR_COLORTERM_VALUES


def create_cover_renderer(mode: str) -> CoverRendererPort:
    if mode == CoverRenderMode.TRUECOLOR:
        if _terminal_supports_truecolor():
            return FallbackCoverRenderer(TruecolorBlockCoverRenderer())
        return PlaceholderCoverRenderer()
    if mode == CoverRenderMode.ASCII:
        return FallbackCoverRenderer(AsciiCoverRenderer())
    return PlaceholderCoverRenderer()
