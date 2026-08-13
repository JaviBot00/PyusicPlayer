"""PlaceholderCoverRenderer - the mandatory fallback renderer.

Renders no image at all, just a fixed text marker. Used directly when
cover_render_mode="placeholder", and used internally by FallbackCoverRenderer
whenever the truecolor/ascii pipeline can't produce something usable (no
cover_data, decode failure, or missing terminal capability).
"""

from __future__ import annotations

from typing import Optional

from rich.text import Text


class PlaceholderCoverRenderer:
    """Ignores cover_data/cover_mime entirely - always renders the same
    fixed placeholder, sized to width x height."""

    MARKER = "\u266a"  # eighth note

    def render(
        self,
        cover_data: Optional[bytes],
        cover_mime: Optional[str],
        width: int,
        height: int,
    ) -> Text:
        label = f"{self.MARKER} No Cover {self.MARKER}"
        if len(label) > width:
            label = self.MARKER
        pad_left = max(0, (width - len(label)) // 2)
        line = (" " * pad_left + label).ljust(width)[:width]
        blank = " " * width
        middle_row = height // 2
        rows = [line if row == middle_row else blank for row in range(height)]
        return Text("\n".join(rows))
