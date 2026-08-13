"""TruecolorBlockCoverRenderer - Pillow-based half-block truecolor rendering.

Uses the "▀" (upper half block) trick: each terminal cell paints two source
pixels at once, foreground color = top pixel, background color = bottom
pixel. This is why the image is resized to height*2 rows before sampling -
it's the same aspect-ratio correction AsciiCoverRenderer uses, since a
terminal cell is roughly 2:1 tall and a naive 1:1 resize would squash the
image vertically.

Deliberately does NOT catch decode errors - see FallbackCoverRenderer for
where the "never raise" guarantee for the overall feature actually lives.
Terminal truecolor *capability* (COLORTERM) is checked at selection time in
factory.py, not here - by the time this class's render() runs, the caller
has already decided the terminal can display 24-bit color.
"""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image
from rich.style import Style
from rich.text import Text

_HALF_BLOCK = "\u2580"  # ▀


class TruecolorBlockCoverRenderer:
    def render(
        self,
        cover_data: Optional[bytes],
        cover_mime: Optional[str],
        width: int,
        height: int,
    ) -> Text:
        image = Image.open(io.BytesIO(cover_data)).convert("RGB")
        image = image.resize((width, height * 2))
        pixels = image.load()

        text = Text()
        for row in range(height):
            for col in range(width):
                top = pixels[col, row * 2]
                bottom = pixels[col, row * 2 + 1]
                style = Style(color=self._rgb(top), bgcolor=self._rgb(bottom))
                text.append(_HALF_BLOCK, style=style)
            if row < height - 1:
                text.append("\n")
        return text

    @staticmethod
    def _rgb(pixel: tuple[int, int, int]) -> str:
        r, g, b = pixel
        return f"rgb({r},{g},{b})"
