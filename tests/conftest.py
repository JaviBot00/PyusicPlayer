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

    return files


@pytest.fixture()
def container():
    """Fresh, fully-wired DI container for each test (real adapters)."""
    from pyusicplayer.di.container import create_container

    return create_container()
