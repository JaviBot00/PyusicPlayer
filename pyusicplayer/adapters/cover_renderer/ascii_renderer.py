"""AsciiCoverRenderer - Pillow-based grayscale ASCII rendering.

Shares the decode/resize half of its pipeline with TruecolorBlockCoverRenderer
(see that module's docstring): both sample 2 vertical pixel rows per terminal
row to correct for the ~2:1 tall aspect ratio of a terminal cell. This
renderer discards color and maps luminance to a fixed character ramp instead.

Deliberately does NOT catch decode errors - see FallbackCoverRenderer for
where the "never raise" guarantee for the overall feature actually lives.
"""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image
from rich.text import Text

_RAMP = " .:-=+*#%@"


class AsciiCoverRenderer:
    def render(
        self,
        cover_data: Optional[bytes],
        cover_mime: Optional[str],
        width: int,
        height: int,
    ) -> Text:
        image = Image.open(io.BytesIO(cover_data)).convert("L")
        image = image.resize((width, height * 2))
        pixels = list(image.getdata())

        lines = []
        for row in range(height):
            chars = []
            for col in range(width):
                top = pixels[(row * 2) * width + col]
                bottom = pixels[(row * 2 + 1) * width + col]
                luminance = (top + bottom) // 2
                idx = min(len(_RAMP) - 1, luminance * len(_RAMP) // 256)
                chars.append(_RAMP[idx])
            lines.append("".join(chars))
        return Text("\n".join(lines))
