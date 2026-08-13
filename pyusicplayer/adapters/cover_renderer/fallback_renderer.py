"""FallbackCoverRenderer - Decorator giving any primary renderer the
"cover art is always visible" guarantee.

Two cases route straight to the fallback (PlaceholderCoverRenderer by
default) without ever touching the primary:
  - cover_data is None (no embedded art - the common case, not an error)
  - primary.render() raises anything (corrupt/undecodable image, unexpected
    format quirk, etc.)

This is where the port's "must never raise" contract is actually enforced;
individual primary adapters (Ascii/Truecolor) are deliberately allowed to
raise so that contract isn't duplicated three times.
"""

from __future__ import annotations

from typing import Optional

from rich.console import RenderableType

from pyusicplayer.adapters.cover_renderer.placeholder_renderer import PlaceholderCoverRenderer
from pyusicplayer.core.ports.cover_renderer import CoverRendererPort


class FallbackCoverRenderer:
    def __init__(self, primary: CoverRendererPort, fallback: Optional[CoverRendererPort] = None) -> None:
        self.primary = primary
        self.fallback = fallback or PlaceholderCoverRenderer()

    def render(
        self,
        cover_data: Optional[bytes],
        cover_mime: Optional[str],
        width: int,
        height: int,
    ) -> RenderableType:
        if cover_data is None:
            return self.fallback.render(cover_data, cover_mime, width, height)
        try:
            return self.primary.render(cover_data, cover_mime, width, height)
        except Exception:
            return self.fallback.render(cover_data, cover_mime, width, height)
