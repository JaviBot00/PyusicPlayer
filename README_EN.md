# PyusicPlayer

An interactive music player written in Python with TUI (Terminal) and GUI (Graphical) interfaces, plus an API server for Web and Android clients.

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

## Installation

### Requirements

- Python 3.10+
- ffmpeg (for audio download and conversion)

### Dependencies

```bash
pip install -r requirements.txt
```

### Optional

```bash
# VLC as alternative audio backend
pip install python-vlc
```

## Usage

### TUI Mode (Terminal)

```bash
python main.py --tui
```

### GUI Mode (Desktop)

```bash
python main.py --gui
```

### Server Mode (API)

```bash
python main.py --server --port 8000
```

### Combined (GUI + API)

```bash
python main.py --gui --api
```

## Keyboard Shortcuts

### Playback

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `S` | Stop |
| `N` | Next track |
| `P` | Previous track |
| `←/→` | Seek backward/forward |
| `↑/↓` | Volume up/down |
| `M` | Mute |

### Playback Modes

| Key | Action |
|-----|--------|
| `1` | Sequential |
| `L` | Loop one |
| `Shift+L` | Loop all |
| `R` | Shuffle |

### Alternate Views (Independent On/Off)

| Key | Action |
|-----|--------|
| `Y` | Toggle Lyrics on/off |
| `C` | Toggle Cover on/off |
| `V` | Toggle Visualizer on/off |

### Visualizer

| Key | Action |
|-----|--------|
| `Ctrl+V` | Cycle visualizer style (5 styles) |

### Layout

| Key | Action |
|-----|--------|
| `Shift+L` | Cycle layout (side_by_side / stacked) |

### Utilities

| Key | Action |
|-----|--------|
| `F1` or `?` | Help |
| `/` | Search library |
| `Q` | Quit |

## Project Structure

```
PyusicPlayer/
├── main.py                    # Entry point
├── pyusicplayer/
│   ├── core/                  # Business logic (no external dependencies)
│   │   ├── ports/             # Interfaces (Protocol classes)
│   │   ├── domain/            # Data models
│   │   └── services/          # Business logic
│   ├── adapters/              # Concrete implementations
│   │   ├── audio/             # Audio backends (pygame, vlc)
│   │   ├── metadata/          # Metadata readers (mutagen)
│   │   ├── lyrics/            # Lyrics providers (LRCLIB, local)
│   │   ├── notifications/     # OS notifications
│   │   ├── config/            # Configuration
│   │   ├── library/           # SQLite indexing
│   │   ├── downloader/        # yt-dlp downloads
│   │   └── visualizer/        # Spectrum visualizers (5 styles)
│   ├── interfaces/            # UI layer
│   │   ├── tui/               # Terminal interface (Textual)
│   │   │   ├── screens/       # ModalScreen for help
│   │   │   └── widgets/       # Alternate view widgets
│   │   ├── gui/               # Desktop GUI (CustomTkinter)
│   │   │   ├── widgets/       # Alternate view frames
│   │   │   └── menus/         # Help menu
│   │   └── api/               # FastAPI server
│   ├── i18n/                  # Internationalization
│   └── di/                    # Dependency injection
├── data/                      # Portable data (gitignored)
│   ├── config.json
│   └── library.db
├── assets/
│   └── placeholder.png
├── CONCEPT.md                 # Original concept
├── AGENT.md                   # Agent context
├── SPEC.md                    # Technical specification
├── README.md                  # Documentation (ES)
├── README_EN.md               # This documentation (EN)
├── INDEX.md                   # Documentation index
├── LEARNING.md                # Learning guide (ES)
└── LICENSE
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
> Connections are made in the ENTRY POINT (main.py).

## Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Audio | pygame / VLC | Audio playback |
| Metadata | mutagen | ID3 tag reading |
| TUI | Textual | Modern terminal interface |
| GUI | CustomTkinter | Desktop graphical interface |
| API | FastAPI | Streaming server |
| DB | SQLite | Library indexing |
| Downloads | yt-dlp | Audio download |
| Visualizer | numpy (FFT) | Numerical processing |
| i18n | gettext + Babel | Internationalization |

## Supported Audio Formats

- **Primary**: Opus (for downloads)
- **Supported**: MP3, OGG, WAV, FLAC, M4A, AAC
- All formats supported by pygame/VLC

## Configuration

Configuration is stored in two locations:

1. **Portable**: `./data/config.json` (next to project)
2. **Global**: `~/.config/pyusicplayer/config.json` (XDG standard)

Portable configuration takes priority over global.

### Visualization Settings

```json
{
  "alternate_views": {
    "lyrics_enabled": false,
    "cover_enabled": false,
    "visualizer_enabled": false,
    "visualizer_style": "BARS_VERTICAL"
  },
  "layout": {
    "mode": "side_by_side",
    "alternate_position": "right",
    "split_ratio": 60
  },
  "visualizer": {
    "num_bars": 32,
    "smoothing": 0.3,
    "sensitivity": 1.0,
    "peak_hold": true
  }
}
```

## API Endpoints

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
| [AGENT.md](AGENT.md) | Agent context |
| [SPEC.md](SPEC.md) | Technical specification |
| [README.md](README.md) | Documentation (ES) |
| [README_EN.md](README_EN.md) | This documentation (EN) |
| [INDEX.md](INDEX.md) | Documentation index |
| [LEARNING.md](LEARNING.md) | Learning guide (ES) |

## License

[MIT License](LICENSE)

## Author

[HotGuy]
