# PyusicPlayer

An interactive music player written in Python with TUI (Terminal) and GUI (Graphical) interfaces, plus an API server for Web and Android clients.

> **Actual project status:** of everything described in this document, only
> TUI playback is implemented and tested today. GUI, API, library database,
> lyrics, visualizer, notifications, downloads, i18n, and config persistence
> are target design, not existing code. The exact breakdown of what's done
> lives in [AGENT.md](AGENT.md#implementation-status), which is kept
> up to date on purpose so this documentation doesn't repeat the problem it
> used to have (claiming things were "completed" when they were really just
> a disconnected skeleton).

## Features

- **Playback**: Play, pause, resume, stop, seek
- **Playback modes**: Sequential, single loop, full playlist loop, shuffle
- **Alternate views** (independent toggles):
  - **Lyrics**: Synchronized via LRCLIB or local .lrc files
  - **Album art**: Extracted from ID3 tags or cover.jpg/png file
  - **Audio spectrum analyzer**: Real-time frequency visualization with 5 styles
- **5 visualization styles**:
  - Vertical bars (classic equalizer CAVA/Winamp style)
  - Horizontal bars
  - Waveform display
  - Radial (circular)
  - Beat-reactive particles
- **Help system**: F1 shows keyboard shortcuts and controls
- **Configurable layout**: Side-by-side or stacked, changeable via settings and shortcuts
- **Library management**: SQLite indexing with filters by artist, album, folder
- **Downloads**: Download audio from YouTube/SoundCloud via yt-dlp
- **Multi-interface**: TUI (terminal), GUI (desktop), API (web/mobile)
- **Portable**: Configuration and database in project folder
- **Cross-platform**: Linux, Windows, macOS

_(Full target feature list. See the status note above for what's actually implemented.)_

## Installation

### Requirements

- Python 3.10+
- ffmpeg (also needed to generate audio test fixtures)

### Dependencies

```bash
pip install -r requirements.txt

# Only if you're running tests or contributing code:
pip install -r requirements-dev.txt
```

## Usage

### TUI Mode (Terminal) — working today

```bash
python -m pyusicplayer --tui
python -m pyusicplayer --music-dir /path/to/your/music --tui
```

### GUI Mode / API Server — not implemented yet

```bash
python -m pyusicplayer --gui     # exits with a "not implemented" message
python -m pyusicplayer --server  # exits with a "not implemented" message
```

## Tests

```bash
pip install -r requirements-dev.txt

pytest                  # full suite
pytest -m "not audio"   # fast loop: skips real pygame/mutagen tests
pytest tests/core/      # just one layer
```

Real-audio tests (`@pytest.mark.audio`) generate their own fixture files
with `ffmpeg` at test-session start (`tests/conftest.py`); if `ffmpeg`
isn't installed, those tests are skipped with a clear reason instead of
failing. See the "Testing" section of [AGENT.md](AGENT.md#testing) for
what each layer covers and why (including two real bugs that were only
caught by writing tests, not by manual testing).

## Keyboard Shortcuts

### Playback (implemented)

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `S` | Stop |
| `N` | Next track |
| `P` | Previous track |
| `←/→` | Seek backward/forward (±5s) |
| `↑/↓` | Volume up/down |

### Playback Modes (implemented)

| Key | Action |
|-----|--------|
| `1` | Sequential |
| `L` | Loop one |
| `Shift+L` | Loop all |
| `R` | Shuffle |

### Not implemented yet (future design)

| Key | Action |
|-----|--------|
| `M` | Mute |
| `Y` / `C` / `V` | Lyrics / Cover / Visualizer toggle |
| `Ctrl+V` | Cycle visualizer style |
| `F1` or `?` | Help |
| `/` | Search library |

## Project Structure

```
PyusicPlayer/
├── pyusicplayer/
│   ├── __main__.py             # Entry point (--tui works; --gui/--server warn they're missing)
│   ├── core/                   # Business logic (no external dependencies)
│   │   ├── models.py           # Track, Playlist (Fisher-Yates shuffle)
│   │   ├── services.py         # PlayerService
│   │   └── ports/              # Protocol interfaces (only Audio/Metadata have a real adapter)
│   ├── adapters/
│   │   ├── audio/pygame_adapter.py       # Implemented and tested
│   │   ├── metadata/mutagen_adapter.py   # Implemented and tested
│   │   ├── lyrics/ notifications/ config/ library/ downloader/ visualizer/  # empty stubs, future phases
│   ├── interfaces/
│   │   ├── tui/app.py          # Implemented and tested (Textual)
│   │   └── gui/                # empty stub, future phase
│   └── di/container.py         # Real wiring of the two implemented adapters
│
├── tests/                      # pytest: core/ (fast, no I/O) + adapters/di/interfaces/ (real audio via ffmpeg)
├── pytest.ini
├── requirements.txt             # runtime dependencies
├── requirements-dev.txt         # pytest + pytest-asyncio
│
├── music/                       # Sample music
├── CONCEPT.md                   # Original concept (full vision)
├── AGENT.md                     # Agent context — actual status kept here
├── SPEC.md                      # Full technical specification (vision, not all implemented)
├── README.md / README_EN.md
├── INDEX.md
└── LEARNING.md
```

## Architecture

The project follows the **Ports & Adapters** (Hexagonal Architecture) pattern:

- **Ports**: Interfaces defined as `Protocol` classes
- **Adapters**: Concrete implementations of each interface
- **Services**: Business logic that only depends on ports
- **Container**: Connects ports with adapters at the entry point

### Key Principle

> A module NEVER imports concrete implementations.
> It only imports PROTOCOLS (interfaces).
> Connections are made in the ENTRY POINT (`__main__.py`).

## Technologies

| Component | Technology | Status |
|-----------|------------|--------|
| Audio | pygame | Implemented |
| Metadata | mutagen | Implemented |
| TUI | Textual | Implemented |
| Tests | pytest + pytest-asyncio | Implemented |
| GUI | CustomTkinter | Planned |
| API | FastAPI | Planned |
| DB | SQLite | Planned |
| Downloads | yt-dlp | Planned |
| Visualizer | numpy (FFT) | Planned |
| i18n | gettext + Babel | Planned |

## Supported Audio Formats

- **Playback**: MP3, OGG, WAV, FLAC, M4A, WMA — all via pygame
- **Full tag metadata** (title/artist/album/track): MP3, FLAC, OGG, Opus, M4A
- **Duration only** (no tags): WAV, WMA — see the docstring in
  `adapters/metadata/mutagen_adapter.py` for why

## Configuration

**Not implemented yet.** Volume, playback mode, shuffle, and last playlist
all reset to defaults on every run. Planned alongside the SQLite library
adapter (see AGENT.md).

## API Endpoints — not implemented, future design

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stream/{id}` | Audio streaming with Range requests |
| GET | `/api/cover/{id}` | Album art as image |
| GET | `/api/lyrics/{id}` | Synchronized lyrics as JSON |
| GET | `/api/library` | Song list with filters |
| GET | `/api/search?q=` | Song search |
| POST | `/api/download` | Download audio from URL |

## Documentation

| File | Content |
|------|---------|
| [CONCEPT.md](CONCEPT.md) | Original project concept |
| [AGENT.md](AGENT.md) | Agent context — actual implementation status |
| [SPEC.md](SPEC.md) | Full technical specification (vision) |
| [README.md](README.md) | Documentation (ES) |
| [README_EN.md](README_EN.md) | This documentation (EN) |
| [INDEX.md](INDEX.md) | Documentation index |
| [LEARNING.md](LEARNING.md) | Learning guide (ES) |

## License

[MIT License](LICENSE)

## Author

[HotGuy]
