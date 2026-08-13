"""Cover renderer port - Protocol for rendering embedded cover art to a
terminal-displayable form (Rich renderable, since the only consumer today
is the Textual TUI, which is Rich-based).

Three render modes are user-selectable (see AGENT.md "Cover render backend
selection"): truecolor half-block, ASCII monochrome, placeholder text.
Adapters must NEVER raise - any decode/format/capability failure must
degrade to a placeholder rendering internally (or via FallbackCoverRenderer),
since cover art is always-visible UI, not a toggleable view that can just
be hidden on error.
"""

from __future__ import annotations

from typing import Optional, Protocol

from rich.console import RenderableType


class CoverRenderMode:
    """String constants for AppConfig.cover_render_mode - plain strings,
    not an Enum, matching the existing repeat_mode convention in
    core/ports/config.py."""

    TRUECOLOR = "truecolor"
    ASCII = "ascii"
    PLACEHOLDER = "placeholder"


class CoverRendererPort(Protocol):
    """Adapter interface for rendering cover art to the terminal."""

    def render(
        self,
        cover_data: Optional[bytes],
        cover_mime: Optional[str],
        width: int,
        height: int,
    ) -> RenderableType:
        """Render cover art sized to fit width x height terminal cells.

        cover_data=None (no embedded art) must render a placeholder, not
        raise or return None. Must never raise on malformed/undecodable
        image bytes either - fall back to a placeholder rendering.
        """
        ...
