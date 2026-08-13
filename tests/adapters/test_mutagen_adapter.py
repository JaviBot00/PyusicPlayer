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


class TestCoverExtraction:
    """extract() must populate cover_data/cover_mime inline (not just the
    separate get_cover() method) for formats where embedded art is
    supported: mp3 (APIC), flac (Picture), m4a (covr). Formats without
    cover support (ogg/opus/wav/wma) must leave both fields None, not
    raise."""

    def test_mp3_extract_populates_cover_data_and_mime(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        meta = adapter.extract(str(audio_fixtures["mp3_cover"]))
        assert meta.cover_data == b"\xff\xd8\xff\xe0FAKEJPEGDATA_FOR_TESTS_ONLY\xff\xd9"
        assert meta.cover_mime == "image/jpeg"

    def test_flac_extract_populates_cover_data_and_mime(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        meta = adapter.extract(str(audio_fixtures["flac_cover"]))
        assert meta.cover_data == b"\x89PNG\r\n\x1a\nFAKEPNGDATA_FOR_TESTS_ONLY"
        assert meta.cover_mime == "image/png"

    def test_m4a_extract_populates_cover_data_and_mime(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        meta = adapter.extract(str(audio_fixtures["m4a_cover"]))
        assert meta.cover_data == b"\x89PNG\r\n\x1a\nFAKEPNGDATA_FOR_TESTS_ONLY"
        assert meta.cover_mime == "image/png"

    def test_mp3_without_cover_leaves_fields_none(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        meta = adapter.extract(str(audio_fixtures["mp3"]))
        assert meta.cover_data is None
        assert meta.cover_mime is None

    def test_flac_without_cover_leaves_fields_none(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        meta = adapter.extract(str(audio_fixtures["flac"]))
        assert meta.cover_data is None
        assert meta.cover_mime is None

    @pytest.mark.parametrize("fmt", ["ogg", "wav"])
    def test_formats_without_cover_support_leave_fields_none(
        self, adapter: MutagenMetadataAdapter, audio_fixtures, fmt
    ):
        meta = adapter.extract(str(audio_fixtures[fmt]))
        assert meta.cover_data is None
        assert meta.cover_mime is None

    def test_get_cover_still_returns_bytes_for_mp3(self, adapter: MutagenMetadataAdapter, audio_fixtures):
        """Public get_cover() must keep working standalone (e.g. for a
        library adapter that stores tracks without re-extracting full
        metadata), sharing implementation with extract() rather than
        diverging."""
        cover = adapter.get_cover(str(audio_fixtures["mp3_cover"]))
        assert cover == b"\xff\xd8\xff\xe0FAKEJPEGDATA_FOR_TESTS_ONLY\xff\xd9"


class TestSupportsFormat:
    def test_supports_known_formats(self, adapter: MutagenMetadataAdapter):
        for ext in ("song.mp3", "song.flac", "song.ogg", "song.m4a", "song.wav", "song.wma"):
            assert adapter.supports_format(ext)

    def test_rejects_unknown_formats(self, adapter: MutagenMetadataAdapter):
        assert not adapter.supports_format("song.txt")
        assert not adapter.supports_format("song.pdf")
