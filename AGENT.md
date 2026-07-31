# PyusicPlayer - Agent Context

## Project Overview

An interactive music player built in Python that runs in both TUI (Terminal User Interface) and GUI (Graphical User Interface) modes, with an optional API server for web and Android clients.

## Core Features

### Player Controls
- Play, Pause, Resume, Stop
- Loop modes: single track, entire playlist, or random/shuffle
- Skip forward/backward, next/previous track
- Seek (advance/rewind within a song)

### Media Display (Always Visible)
- Player controls and progress bar
- Current track info (title, artist, album)

### Alternate Views (Independent Toggles)
- **Lyrics**: Synchronized lyrics display (or message if not available)
- **Cover Art**: Album art visualization (or placeholder if not available)
- **Audio Spectrum Analyzer**: Real-time frequency visualization with 5 styles

### Audio Spectrum Visualizer
- 5 visualization styles:
  - **Bars Vertical**: Classic equalizer bars (CAVA/Winamp style)
  - **Bars Horizontal**: Modern horizontal bars
  - **Waveform**: Real-time waveform display
  - **Radial**: Circular/radial visualization
  - **Particles**: Beat-reactive particle effects
- Cycle through styles with keyboard shortcut (Ctrl+V)
- Configurable: bars count, smoothing, sensitivity

### Help System
- TUI: F1 opens ModalScreen with all shortcuts
- GUI: Help menu + F1 opens dialog
- Comprehensive list of controls and keybindings

### Configuration
- Customizable settings
- Restore to defaults
- Portable configuration (local JSON) + global (XDG compliant)
- Layout configuration (side-by-side or stacked)
- Alternate view toggles

### Download Support
- Download audio from YouTube/SoundCloud/etc via yt-dlp
- Format: Opus (optimal quality/size ratio)
- Embed metadata and thumbnail

### Library Management
- Index and organize music library in SQLite database
- Filter by artist, album, folder
- Import multiple folders recursively
- Separate collections management
- Refresh detection for changes

### Multi-Interface
- **TUI**: Terminal-based interface using Textual framework
- **GUI**: Desktop interface using CustomTkinter
- **API**: REST server using FastAPI for web/Android clients

## Architecture Principles

### Ports & Adapters (Hexagonal Architecture)

The core principle: **Never import concrete implementations in business logic. Only import Protocol interfaces.**

```
┌─────────────────────────────────────────────────────────────┐
│                    GOLDEN RULE                              │
│  A module NEVER imports concrete implementations.           │
│  It only imports PROTOCOLS (interfaces).                   │
│  Connections are made in the ENTRY POINT (main.py).         │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Flow

```
main.py (entry point)
    ↓
container.py (dependency injection / wiring)
    ↓
services (business logic) ← NEVER imports adapters
    ↓
ports (interfaces) ← NEVER imports implementations

adapters (implementations) → ports (implements the contract)
```

### Design Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Strategy** | playlist_service.py | Switch between sequential/shuffle/loop without if/else |
| **Observer** | player_service.py | Notify UI and notifications on state change |
| **Factory** | container.py | Create adapters based on config/OS |
| **Adapter** | adapters/* | Wrap external libraries behind interfaces |
| **Repository** | library SQLite | Data access abstraction |
| **Template Method** | visualizer/base.py | Base FFT processing with style-specific render |

## Technology Stack

### Core (Business Logic)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Audio Backend | pygame (primary), VLC (alternative) | pygame is simple, VLC supports all formats |
| Metadata | mutagen + EasyID3 | Multi-format, actively maintained |
| Lyrics | LRCLIB API + local .lrc files | Free, offline fallback |
| Visualizer | numpy (FFT) | Fast numerical processing |
| Config | JSON files | Portable + global |
| i18n | gettext + Babel | Industry standard, ES/EN |

### Interfaces

| Component | Technology | Rationale |
|-----------|------------|-----------|
| TUI | Textual | Modern, CSS styling, mouse support, 36k stars |
| GUI | CustomTkinter | Simple, modern look, MIT license |
| API | FastAPI | Async streaming, OpenAPI docs, large community |

### Infrastructure

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Database | SQLite | Portable, no server needed |
| Downloads | yt-dlp + ffmpeg | Best quality, opus format |
| Notifications | Native (notify-send/osascript) | Zero dependencies |

### Audio Formats Supported

- **Primary**: Opus (download format)
- **Supported**: MP3, OGG, WAV, FLAC, M4A, AAC
- All formats supported by pygame/VLC

## Project Structure

```
PyusicPlayer/
├── main.py                        # Legacy entry point (to be replaced)
├── pyusicplayer/
│   ├── __init__.py                # Package init with version
│   ├── __main__.py                # Entry point (--tui, --gui, --server)
│   │
│   ├── core/                      # Business logic (NO dependencies)
│   │   ├── __init__.py
│   │   ├── models.py              # Track, Playlist, PlaylistMode
│   │   ├── services.py            # PlayerService, LibraryService
│   │   └── ports/                 # Protocol interfaces
│   │       ├── __init__.py
│   │       ├── audio.py           # AudioPort Protocol
│   │       ├── metadata.py        # MetadataPort Protocol
│   │       ├── lyrics.py          # LyricsPort Protocol
│   │       ├── notifications.py   # NotificationsPort Protocol
│   │       ├── config.py          # ConfigPort Protocol
│   │       ├── library.py         # LibraryPort Protocol
│   │       ├── downloader.py      # DownloaderPort Protocol
│   │       └── visualizer.py      # VisualizerPort Protocol
│   │
│   ├── adapters/                  # Concrete implementations
│   │   ├── __init__.py
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   └── pygame_adapter.py  # Pygame audio backend
│   │   ├── metadata/
│   │   │   ├── __init__.py
│   │   │   └── mutagen_adapter.py # Mutagen metadata reader
│   │   ├── lyrics/
│   │   │   ├── __init__.py
│   │   │   └── (to be implemented)
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   └── (to be implemented)
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── (to be implemented)
│   │   ├── library/
│   │   │   ├── __init__.py
│   │   │   └── (to be implemented)
│   │   ├── downloader/
│   │   │   ├── __init__.py
│   │   │   └── (to be implemented)
│   │   └── visualizer/
│   │       ├── __init__.py
│   │       └── (to be implemented)
│   │
│   ├── interfaces/                # UI layer
│   │   ├── __init__.py
│   │   ├── tui/                   # Textual TUI
│   │   │   └── __init__.py
│   │   └── gui/                   # CustomTkinter GUI
│   │       └── __init__.py
│   │
│   ├── di/                        # Dependency Injection
│   │   ├── __init__.py
│   │   └── container.py           # Container with register/resolve
│   │
│   └── i18n/                      # Internationalization
│       └── __init__.py            # setup_i18n(), get_translation()
│
├── data/                          # Portable data (gitignored)
│   ├── config.json
│   └── library.db
│
├── i18n/                          # Translation files
│   ├── es.po
│   └── en.po
│
├── music/                         # Sample music files
│
├── AGENT.md                       # This file
├── CONCEPT.md
├── SPEC.md
├── README.md                      # Spanish
├── README_EN.md                   # English
├── LEARNING.md
└── INDEX.md
```

## Keyboard Shortcuts

### Playback
- `Space` - Play/Pause
- `S` - Stop
- `N` - Next track
- `P` - Previous track
- `←/→` - Seek backward/forward
- `↑/↓` - Volume up/down
- `M` - Mute

### Playback Modes
- `1` - Sequential
- `L` - Loop one
- `Shift+L` - Loop all
- `R` - Shuffle

### Alternate Views (Independent Toggles)
- `Y` - Toggle Lyrics on/off
- `C` - Toggle Cover on/off
- `V` - Toggle Visualizer on/off

### Visualizer
- `Ctrl+V` - Cycle visualizer style (5 styles)

### Layout
- `Shift+L` - Cycle layout (side_by_side / stacked)

### Utilities
- `F1` or `?` - Help
- `/` - Search library
- `Q` - Quit

## API Endpoints (FastAPI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stream/{song_id}` | Stream audio with Range requests (seek) |
| GET | `/api/cover/{song_id}` | Get album art as image |
| GET | `/api/lyrics/{song_id}` | Get synchronized lyrics JSON |
| GET | `/api/library` | List songs with filters |
| GET | `/api/search?q=` | Search songs |
| POST | `/api/download` | Download audio from URL |

## Database Schema (SQLite)

```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    last_scan TIMESTAMP
);

CREATE TABLE artists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE albums (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    year INTEGER
);

CREATE TABLE songs (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    album_id INTEGER REFERENCES albums(id),
    collection_id INTEGER REFERENCES collections(id),
    file_path TEXT NOT NULL UNIQUE,
    duration_ms INTEGER,
    format TEXT,
    has_lyrics BOOLEAN DEFAULT FALSE,
    has_cover BOOLEAN DEFAULT FALSE
);
```

## Configuration Schema

```json
{
  "version": 1,
  "player": {
    "volume": 80,
    "loop_mode": "none",
    "shuffle": false
  },
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

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Audio format | Opus (downloads) | Best quality/size ratio, document alternatives |
| Database location | Portable (`./data/library.db`) | Full portability |
| API framework | FastAPI | Streaming + community + simplicity |
| Frontend | GUI + TUI + API | Full coverage |
| Config | Portable + global XDG | Best of both worlds |
| Lyrics | LRCLIB + local .lrc | Free + offline fallback |
| Visualizer | numpy FFT | Fast numerical processing |
| Visualizer styles | 5 styles | Full customization from start |
| i18n | gettext + Babel | Industry standard |

## Important Notes

- **Architecture over playability**: Prioritize perfect architecture over something playable
- **Modular design**: Any component should be swappable without breaking others
- **Cross-platform**: Linux, Windows, macOS support
- **Notifications**: Pop-up notifications when player window is not focused
- **GUI as background process**: No terminal window required
- **Alternate views**: Independent toggles (Y=Lyrics, C=Cover, V=Visualizer)
- **Layout configurable**: Side-by-side or stacked, changeable via settings/shortcuts

## Implementation Status

### Completed
- [x] Port protocols defined (Audio, Metadata, Lyrics, Notifications, Config, Library, Downloader, Visualizer)
- [x] Core domain models (Track, Playlist, PlaylistMode)
- [x] Core services (PlayerService, LibraryService)
- [x] DI Container implementation
- [x] Pygame audio adapter (basic)
- [x] Mutagen metadata adapter (extraction)
- [x] Package structure created
- [x] Entry point with CLI arguments

### In Progress
- [ ] Implement remaining adapters (Config, Library, Lyrics, Notifications, Visualizer, Downloader)
- [ ] Implement TUI interface (Textual)
- [ ] Implement GUI interface (CustomTkinter)
- [ ] Implement FastAPI server
- [ ] Create i18n translations

### Next Steps
1. Implement SQLite library adapter
2. Implement JSON config adapter
3. Implement LRCLIB lyrics adapter
4. Implement platform-specific notifications
5. Implement visualizer with FFT processing
6. Create TUI interface with Textual
7. Create GUI interface with CustomTkinter
