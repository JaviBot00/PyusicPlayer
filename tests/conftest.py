"""Shared pytest fixtures.

Audio playback tests need real audio files and a real (but headless) pygame
mixer. We generate small synthetic files with ffmpeg once per test session
instead of committing binary fixtures to the repo. If ffmpeg is not on PATH,
every test that needs audio fixtures is skipped (not failed) with a clear
reason, since that's an environment gap, not a code regression.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import pytest

# Must be set before pygame is imported anywhere, including by adapter code
# under test, so playback tests run headless in CI/sandboxes without a
# sound device.
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

HAS_FFMPEG = shutil.which("ffmpeg") is not None

# Fake but well-formed-enough cover bytes for extraction tests: mutagen does
# not validate pixel content for APIC/Picture/covr, only the declared mime,
# so these don't need to be real decodable images. Real-image decoding
# (Pillow) is out of scope for the extraction slice.
_COVER_JPEG = b"\xff\xd8\xff\xe0FAKEJPEGDATA_FOR_TESTS_ONLY\xff\xd9"
_COVER_PNG = b"\x89PNG\r\n\x1a\nFAKEPNGDATA_FOR_TESTS_ONLY"


def _write_sine_wav(path: Path, duration_s: float, freq: int = 440, sample_rate: int = 44100) -> None:
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for i in range(int(sample_rate * duration_s)):
            value = int(3000 * math.sin(2 * math.pi * freq * i / sample_rate))
            w.writeframes(struct.pack("<h", value))


@pytest.fixture(scope="session")
def audio_fixtures(tmp_path_factory) -> dict[str, Path]:
    """One ~5s tone in every supported format, plus a 1s clip for
    end-of-track tests. Skips (not fails) if ffmpeg is unavailable."""
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not available: cannot generate audio fixtures")

    out_dir = tmp_path_factory.mktemp("audio_fixtures")
    wav_path = out_dir / "tone.wav"
    _write_sine_wav(wav_path, duration_s=5.0)

    files: dict[str, Path] = {"wav": wav_path}

    conversions = {
        "mp3": ["-codec:a", "libmp3lame", "-b:a", "128k"],
        "ogg": ["-codec:a", "libvorbis", "-q:a", "4"],
        "flac": [
            "-codec:a", "flac",
            "-metadata", "title=Test Title",
            "-metadata", "artist=Test Artist",
            "-metadata", "album=Test Album",
            "-metadata", "track=3",
        ],
        "m4a": ["-codec:a", "aac"],
    }
    for ext, args in conversions.items():
        target = out_dir / f"tone.{ext}"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), *args, str(target)],
            check=True,
            capture_output=True,
        )
        files[ext] = target

    short_wav = out_dir / "short.wav"
    _write_sine_wav(short_wav, duration_s=1.0)
    short_mp3 = out_dir / "short.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(short_wav), "-codec:a", "libmp3lame", str(short_mp3)],
        check=True,
        capture_output=True,
    )
    files["short_mp3"] = short_mp3

    short_mp3_2 = out_dir / "short2.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(short_wav), "-codec:a", "libmp3lame", str(short_mp3_2)],
        check=True,
        capture_output=True,
    )
    files["short_mp3_2"] = short_mp3_2

    _embed_covers(files, out_dir)

    return files


def _embed_covers(files: dict[str, Path], out_dir: Path) -> None:
    """Add cover-embedded copies of the mp3/flac/m4a fixtures under new keys
    (mp3_cover/flac_cover/m4a_cover), leaving the original no-cover files
    untouched so existing tag/duration tests are unaffected. ogg/opus/wav/wma
    intentionally get no cover fixture: MutagenMetadataAdapter doesn't (yet)
    implement cover extraction for those formats."""
    import shutil as _shutil

    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import APIC, ID3
    from mutagen.mp4 import MP4, MP4Cover

    mp3_cover = out_dir / "tone_cover.mp3"
    _shutil.copy(files["mp3"], mp3_cover)
    try:
        tags = ID3(mp3_cover)
    except Exception:
        tags = ID3()
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=_COVER_JPEG))
    tags.save(mp3_cover)
    files["mp3_cover"] = mp3_cover

    flac_cover = out_dir / "tone_cover.flac"
    _shutil.copy(files["flac"], flac_cover)
    flac_audio = FLAC(flac_cover)
    pic = Picture()
    pic.type = 3
    pic.mime = "image/png"
    pic.data = _COVER_PNG
    flac_audio.add_picture(pic)
    flac_audio.save()
    files["flac_cover"] = flac_cover

    m4a_cover = out_dir / "tone_cover.m4a"
    _shutil.copy(files["m4a"], m4a_cover)
    mp4_audio = MP4(m4a_cover)
    mp4_audio["covr"] = [MP4Cover(_COVER_PNG, imageformat=MP4Cover.FORMAT_PNG)]
    mp4_audio.save()
    files["m4a_cover"] = m4a_cover

    # A REAL Pillow-decodable cover, unlike the fake bytes above. Needed for
    # TUI tests that exercise the actual ascii/truecolor decode pipeline
    # rather than just the FallbackCoverRenderer no-op-on-garbage path.
    import io as _io

    from PIL import Image as _Image

    real_cover_buf = _io.BytesIO()
    _Image.new("RGB", (16, 16), (180, 40, 40)).save(real_cover_buf, format="PNG")
    real_cover_bytes = real_cover_buf.getvalue()

    mp3_real_cover = out_dir / "tone_real_cover.mp3"
    _shutil.copy(files["mp3"], mp3_real_cover)
    try:
        real_tags = ID3(mp3_real_cover)
    except Exception:
        real_tags = ID3()
    real_tags.add(APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=real_cover_bytes))
    real_tags.save(mp3_real_cover)
    files["mp3_real_cover"] = mp3_real_cover


@pytest.fixture()
def container():
    """Fresh, fully-wired DI container for each test (real adapters)."""
    from pyusicplayer.di.container import create_container

    return create_container()
