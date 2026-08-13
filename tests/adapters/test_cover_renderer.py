"""Tests for adapters.cover_renderer.* - CoverRendererPort implementations.

Requires Pillow (added to requirements.txt in this slice: `pip install -r
requirements.txt` before running, or these fail at collection with
ModuleNotFoundError for PIL, which is NOT the same as these tests being red
for the right reason). Unlike the mutagen extraction tests, these need REAL
decodable images (Pillow raises on the fake APIC bytes used for extraction
tests in test_mutagen_adapter.py), so fixtures are built with PIL directly,
not mutagen or ffmpeg.
"""

from __future__ import annotations

import io

import pytest
from rich.text import Text

from pyusicplayer.core.ports.cover_renderer import CoverRenderMode


def _make_image_bytes(color=(200, 50, 50), size=(8, 8), fmt="PNG") -> bytes:
    from PIL import Image

    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture()
def sample_png() -> bytes:
    return _make_image_bytes()


@pytest.fixture()
def corrupt_image_bytes() -> bytes:
    return b"not a real image, just garbage bytes"


class TestPlaceholderCoverRenderer:
    def test_renders_something_with_no_cover_data(self):
        from pyusicplayer.adapters.cover_renderer.placeholder_renderer import PlaceholderCoverRenderer

        renderer = PlaceholderCoverRenderer()
        result = renderer.render(None, None, width=20, height=10)
        assert result is not None

    def test_renders_without_raising_even_with_cover_data(self, sample_png):
        """Placeholder mode ignores cover_data entirely by design - it's
        selected explicitly by the user, not just a fallback in this path."""
        from pyusicplayer.adapters.cover_renderer.placeholder_renderer import PlaceholderCoverRenderer

        renderer = PlaceholderCoverRenderer()
        result = renderer.render(sample_png, "image/png", width=20, height=10)
        assert result is not None


class TestAsciiCoverRenderer:
    def test_renders_expected_dimensions(self, sample_png):
        from pyusicplayer.adapters.cover_renderer.ascii_renderer import AsciiCoverRenderer

        renderer = AsciiCoverRenderer()
        result = renderer.render(sample_png, "image/png", width=10, height=5)
        assert isinstance(result, Text)
        lines = result.plain.split("\n")
        assert len(lines) == 5
        assert all(len(line) == 10 for line in lines)

    def test_raises_on_corrupt_image_data(self, corrupt_image_bytes):
        """AsciiCoverRenderer itself is allowed to raise on bad input - the
        never-raise guarantee for the whole feature lives in
        FallbackCoverRenderer, not in each primary adapter, so each adapter
        stays simple and the fallback logic isn't duplicated three times."""
        from pyusicplayer.adapters.cover_renderer.ascii_renderer import AsciiCoverRenderer

        renderer = AsciiCoverRenderer()
        with pytest.raises(Exception):
            renderer.render(corrupt_image_bytes, "image/jpeg", width=10, height=5)


class TestTruecolorBlockCoverRenderer:
    def test_renders_expected_line_count(self, sample_png):
        from pyusicplayer.adapters.cover_renderer.truecolor_renderer import TruecolorBlockCoverRenderer

        renderer = TruecolorBlockCoverRenderer()
        result = renderer.render(sample_png, "image/png", width=10, height=5)
        assert isinstance(result, Text)
        assert result.plain.count("\n") == 4  # 5 rows -> 4 newlines

    def test_uses_half_block_character(self, sample_png):
        from pyusicplayer.adapters.cover_renderer.truecolor_renderer import TruecolorBlockCoverRenderer

        renderer = TruecolorBlockCoverRenderer()
        result = renderer.render(sample_png, "image/png", width=10, height=5)
        assert "▀" in result.plain

    def test_raises_on_corrupt_image_data(self, corrupt_image_bytes):
        from pyusicplayer.adapters.cover_renderer.truecolor_renderer import TruecolorBlockCoverRenderer

        renderer = TruecolorBlockCoverRenderer()
        with pytest.raises(Exception):
            renderer.render(corrupt_image_bytes, "image/jpeg", width=10, height=5)


class TestFallbackCoverRenderer:
    def test_delegates_to_primary_on_success(self, sample_png):
        from pyusicplayer.adapters.cover_renderer.fallback_renderer import FallbackCoverRenderer

        class StubPrimary:
            def __init__(self):
                self.called = False

            def render(self, cover_data, cover_mime, width, height):
                self.called = True
                return Text("primary-result")

        primary = StubPrimary()
        renderer = FallbackCoverRenderer(primary)
        result = renderer.render(sample_png, "image/png", width=10, height=5)
        assert primary.called is True
        assert result.plain == "primary-result"

    def test_falls_back_to_placeholder_when_primary_raises(self, sample_png):
        from pyusicplayer.adapters.cover_renderer.fallback_renderer import FallbackCoverRenderer

        class RaisingPrimary:
            def render(self, cover_data, cover_mime, width, height):
                raise ValueError("cannot decode")

        renderer = FallbackCoverRenderer(RaisingPrimary())
        result = renderer.render(sample_png, "image/png", width=10, height=5)
        assert result is not None  # placeholder, not a propagated exception

    def test_skips_primary_entirely_when_cover_data_is_none(self):
        """No embedded art at all is not an error case to recover from -
        it's the expected common case, so it should never even reach the
        primary renderer's decode pipeline."""
        from pyusicplayer.adapters.cover_renderer.fallback_renderer import FallbackCoverRenderer

        class StubPrimary:
            def __init__(self):
                self.called = False

            def render(self, cover_data, cover_mime, width, height):
                self.called = True
                return Text("primary-result")

        primary = StubPrimary()
        renderer = FallbackCoverRenderer(primary)
        renderer.render(None, None, width=10, height=5)
        assert primary.called is False


class TestCreateCoverRenderer:
    def test_placeholder_mode_returns_placeholder_renderer_directly(self):
        from pyusicplayer.adapters.cover_renderer.factory import create_cover_renderer
        from pyusicplayer.adapters.cover_renderer.placeholder_renderer import PlaceholderCoverRenderer

        renderer = create_cover_renderer(CoverRenderMode.PLACEHOLDER)
        assert isinstance(renderer, PlaceholderCoverRenderer)

    def test_ascii_mode_returns_fallback_wrapped_ascii_renderer(self):
        from pyusicplayer.adapters.cover_renderer.ascii_renderer import AsciiCoverRenderer
        from pyusicplayer.adapters.cover_renderer.factory import create_cover_renderer
        from pyusicplayer.adapters.cover_renderer.fallback_renderer import FallbackCoverRenderer

        renderer = create_cover_renderer(CoverRenderMode.ASCII)
        assert isinstance(renderer, FallbackCoverRenderer)
        assert isinstance(renderer.primary, AsciiCoverRenderer)

    def test_truecolor_mode_with_colorterm_support_returns_fallback_wrapped_truecolor(self, monkeypatch):
        from pyusicplayer.adapters.cover_renderer.factory import create_cover_renderer
        from pyusicplayer.adapters.cover_renderer.fallback_renderer import FallbackCoverRenderer
        from pyusicplayer.adapters.cover_renderer.truecolor_renderer import TruecolorBlockCoverRenderer

        monkeypatch.setenv("COLORTERM", "truecolor")
        renderer = create_cover_renderer(CoverRenderMode.TRUECOLOR)
        assert isinstance(renderer, FallbackCoverRenderer)
        assert isinstance(renderer.primary, TruecolorBlockCoverRenderer)

    def test_truecolor_mode_without_colorterm_support_falls_back_to_placeholder(self, monkeypatch):
        """Terminal capability check happens at selection time, not render
        time: a session without 24-bit color support (e.g. some SSH/tmux
        setups) should never even attempt the truecolor pipeline."""
        from pyusicplayer.adapters.cover_renderer.factory import create_cover_renderer
        from pyusicplayer.adapters.cover_renderer.placeholder_renderer import PlaceholderCoverRenderer

        monkeypatch.delenv("COLORTERM", raising=False)
        renderer = create_cover_renderer(CoverRenderMode.TRUECOLOR)
        assert isinstance(renderer, PlaceholderCoverRenderer)
