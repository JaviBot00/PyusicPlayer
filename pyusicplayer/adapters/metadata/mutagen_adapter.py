"""Mutagen metadata adapter implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from ...core.ports.metadata import AudioMetadata

# Formats with a simple dict-like tag interface (EasyID3, VComment, MP4 tags
# all expose .get("title"), etc. with mostly-matching key names).
_DICT_TAG_FORMATS = {".mp3", ".flac", ".ogg", ".opus", ".m4a"}


class MutagenMetadataAdapter:
    """Metadata adapter using mutagen for extraction.

    WAV and WMA are intentionally limited to duration only: WAV rarely carries
    tags and, when it does, via a non-standard ID3 chunk; WMA (ASF) uses a
    completely different tag-key vocabulary (Title/Author/WM/AlbumTitle) that
    would need its own mapping. Extending either is future work, not silently
    pretended to work.
    """

    SUPPORTED_FORMATS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".wma"}

    def extract(self, file_path: str) -> AudioMetadata:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not self.supports_format(file_path):
            raise ValueError(f"Unsupported format: {path.suffix}")

        ext = path.suffix.lower()
        metadata = AudioMetadata(file_path=file_path)

        if ext == ".wav":
            info = WAVE(file_path).info
            metadata.duration = info.length
            metadata.sample_rate = info.sample_rate
            return metadata

        if ext == ".wma":
            from mutagen.asf import ASF

            audio = ASF(file_path)
            metadata.duration = audio.info.length
            metadata.sample_rate = audio.info.sample_rate
            if audio.tags:
                metadata.title = self._asf_tag(audio, "Title")
                metadata.artist = self._asf_tag(audio, "Author")
                metadata.album = self._asf_tag(audio, "WM/AlbumTitle")
            return metadata

        # --- Formats with dict-like tags below ---
        if ext == ".mp3":
            mp3 = MP3(file_path)
            metadata.duration = mp3.info.length
            metadata.bitrate = mp3.info.bitrate
            metadata.sample_rate = mp3.info.sample_rate
            metadata.cover_data, metadata.cover_mime = self._cover_from_mp3(mp3)
            try:
                audio = EasyID3(file_path)
            except ID3NoHeaderError:
                audio = {}
        elif ext == ".flac":
            audio = FLAC(file_path)
            metadata.duration = audio.info.length
            metadata.sample_rate = audio.info.sample_rate
            metadata.cover_data, metadata.cover_mime = self._cover_from_flac(audio)
        elif ext == ".opus":
            audio = OggOpus(file_path)
            metadata.duration = audio.info.length
            metadata.sample_rate = audio.info.sample_rate
        elif ext == ".ogg":
            audio = OggVorbis(file_path)
            metadata.duration = audio.info.length
            metadata.sample_rate = audio.info.sample_rate
        elif ext == ".m4a":
            audio = MP4(file_path)
            metadata.duration = audio.info.length
            metadata.sample_rate = audio.info.sample_rate
            metadata.cover_data, metadata.cover_mime = self._cover_from_mp4(audio)
        else:
            # Unreachable: supports_format() already filtered the extension.
            raise ValueError(f"Unsupported format: {ext}")

        self._fill_common_tags(metadata, audio)
        return metadata

    @staticmethod
    def _asf_tag(audio, key: str) -> Optional[str]:
        values = audio.tags.get(key)
        return str(values[0]) if values else None

    @staticmethod
    def _cover_from_mp3(mp3) -> tuple[Optional[bytes], Optional[str]]:
        if not mp3.tags:
            return None, None
        covers = mp3.tags.getall("APIC")
        if not covers:
            return None, None
        return covers[0].data, covers[0].mime

    @staticmethod
    def _cover_from_flac(audio) -> tuple[Optional[bytes], Optional[str]]:
        if not audio.pictures:
            return None, None
        return audio.pictures[0].data, audio.pictures[0].mime

    @staticmethod
    def _cover_from_mp4(audio) -> tuple[Optional[bytes], Optional[str]]:
        if not audio.tags or "covr" not in audio.tags:
            return None, None
        cover = audio.tags["covr"][0]
        mime = "image/png" if cover.imageformat == cover.FORMAT_PNG else "image/jpeg"
        return bytes(cover), mime

    @staticmethod
    def _fill_common_tags(metadata: AudioMetadata, audio) -> None:
        """Best-effort tag extraction. Missing/malformed individual tags are
        skipped, but this never masks a structural read failure (that already
        happened above, outside this method)."""
        if "title" in audio:
            metadata.title = str(audio["title"][0])
        if "artist" in audio:
            metadata.artist = str(audio["artist"][0])
        if "album" in audio:
            metadata.album = str(audio["album"][0])
        if "albumartist" in audio:
            metadata.album_artist = str(audio["albumartist"][0])
        if "tracknumber" in audio:
            try:
                metadata.track_number = int(str(audio["tracknumber"][0]).split("/")[0])
            except (ValueError, IndexError):
                pass
        if "discnumber" in audio:
            try:
                metadata.disc_number = int(str(audio["discnumber"][0]).split("/")[0])
            except (ValueError, IndexError):
                pass
        if "date" in audio:
            try:
                metadata.year = int(str(audio["date"][0])[:4])
            except (ValueError, IndexError):
                pass
        if "genre" in audio:
            metadata.genre = str(audio["genre"][0])

    def get_cover(self, file_path: str) -> Optional[bytes]:
        ext = Path(file_path).suffix.lower()
        try:
            if ext == ".mp3":
                data, _mime = self._cover_from_mp3(MP3(file_path))
                return data
            elif ext == ".flac":
                data, _mime = self._cover_from_flac(FLAC(file_path))
                return data
            elif ext == ".m4a":
                data, _mime = self._cover_from_mp4(MP4(file_path))
                return data
        except Exception:
            return None
        return None

    def supports_format(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.SUPPORTED_FORMATS
