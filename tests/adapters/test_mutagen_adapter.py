"""Tests for adapters.metadata.mutagen_adapter.MutagenMetadataAdapter against
real (synthetic) audio files. Requires ffmpeg to build fixtures.
"""

from __future__ import annotations

import pytest

from pyusicplayer.adapters.metadata.mutagen_adapter import MutagenMetadataAdapter


@pytest.fixture()
def adapter() -> MutagenMetadataAdapter:
    return MutagenMetadataAdapter()


class TestExtractErrors:
    def test_missing_file_raises_file_not_found(self, adapter: MutagenMetadataAdapter):
        with pytest.raises(FileNotFoundError):
            adapter.extract("/nonexistent/song.mp3")

    def test_unsupported_extension_raises_value_error(self, adapter: MutagenMetadataAdapter, tmp_path):
        bogus = tmp_path / "not_audio.txt"
        bogus.write_text("hello")
        with pytest.raises(ValueError):
            adapter.extract(str(bogus))


class TestDurationAcrossFormats:
    """Duration must be extracted correctly for every declared supported
    format, including WAV, which previously crashed silently (the
    `except Exception: pass` masked an UnboundLocalError and returned an
    empty AudioMetadata instead of raising or working)."""

    @pytest.mark.parametrize("fmt", ["mp3", "ogg", "flac", "m4a", "wav"])
    def test_duration_is_extracted(self, adapter: MutagenMetadataAdapter, audio_fixtures, fmt):
        meta = adapter.extract(str(audio_fixtures[fmt]))
        assert meta.duration is not None
        assert 4.5 <= meta.duration <= 5.5

    def test_wav_does_not_raise_and_returns_partial_metadata(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        """Explicit regression guard for the original silent-failure bug."""
        meta = adapter.extract(str(audio_fixtures["wav"]))
        assert meta.duration is not None
        # WAV tag support is intentionally not implemented (see adapter
        # docstring) - title/artist are expected to be None, not garbage.
        assert meta.title is None
        assert meta.artist is None


class TestTagExtraction:
    def test_flac_tags_are_extracted(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        meta = adapter.extract(str(audio_fixtures["flac"]))
        assert meta.title == "Test Title"
        assert meta.artist == "Test Artist"
        assert meta.album == "Test Album"
        assert meta.track_number == 3


class TestSupportsFormat:
    def test_supports_known_formats(self, adapter: MutagenMetadataAdapter):
        for ext in ("song.mp3", "song.flac", "song.ogg", "song.m4a", "song.wav", "song.wma"):
            assert adapter.supports_format(ext)

    def test_rejects_unknown_formats(self, adapter: MutagenMetadataAdapter):
        assert not adapter.supports_format("song.txt")
        assert not adapter.supports_format("song.pdf")
