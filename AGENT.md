# PyusicPlayer - Agent Context

## Project Overview

An interactive music player built in Python that runs in both TUI (Terminal User Interface) and GUI (Graphical User Interface) modes, with an optional API server for web and Android clients.

**Current reality check (read this before trusting anything below):** this
document describes the full original vision. The TUI playback path, config
persistence, and the SQLite library layer (schema + full `LibraryPort`
implementation, not yet wired into the TUI's UI) are actually implemented
right now (see "Implementation Status" at the bottom, which is kept honest
on purpose). Everything about GUI, API server, downloader, lyrics,
visualizer, notifications, and i18n is still just plan, not code. Treat the
sections above "Implementation Status" as target design, not a description
of what exists.

## Core Features

### Player Controls
- Play, Pause, Resume, Stop
- Loop modes: single track, entire playlist, or random/shuffle
- Skip forward/backward, next/previous track
- Seek (advance/rewind within a song)
- **"Double-tap previous"**: pressing Previous restarts the current track
  from 0 if more than `PREVIOUS_TRACK_RESTART_THRESHOLD_SECONDS` (default
  5.0s) have elapsed; only within that window does it actually go to the
  prior track. Standard media-player convention.

### Media Display (Always Visible)
- Player controls and progress bar
- Current track info (title, artist, album)
- **Cover art**: embedded album art shown fixed alongside the artist/title
  block (placeholder if the file has none). NOT a toggleable alternate
  view - it's always present, same as title/artist. Decided over the
  original "cover as one of 3 alternating views" design because two
  representations of the same image in a terminal UI is redundant and
  wastes scarce space.

### Alternate Views (Independent Toggles)
- **Lyrics**: Synchronized lyrics display (or message if not available)
- **Audio Spectrum Analyzer**: Real-time frequency visualization with 5 styles

Cover art is intentionally NOT in this list anymore (see "Media Display"
above) - only Lyrics and Visualizer remain as alternating views.

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
- Portable configuration (`./data/config.json`)
- Layout configuration (side-by-side or stacked) — future phase
- Alternate view toggles — future phase

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
│  Connections are made in the ENTRY POINT (__main__.py).      │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Flow

```
__main__.py (entry point)
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
| **Strategy** | core/models.py (Playlist) | Switch between sequential/shuffle/loop without if/else |
| **Observer** | core/services.py (PlayerService) | Notify UI on playback state/track change via `on_state_change`/`on_track_change` callbacks |
| **Factory** | di/container.py | Build and wire concrete adapters behind ports |
| **Adapter** | adapters/* | Wrap external libraries (pygame, mutagen) behind interfaces |
| **Repository** | adapters/library/sqlite_adapter.py (SqliteLibraryAdapter) | CRUD + search over Artist/Album/Song/Collection behind `LibraryPort`, hiding SQL from the rest of the app |

The Template Method (visualizer FFT) pattern listed in earlier drafts of
this doc applies to a feature that is not built yet - removed from this
table until real code exists to point at.

## Technology Stack

### Core (Business Logic)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Audio Backend | pygame (primary), VLC (alternative) | pygame is simple, VLC supports all formats |
| Metadata | mutagen + EasyID3 | Multi-format, actively maintained |
| Lyrics | LRCLIB API + local .lrc files | Free, offline fallback |
| Visualizer | numpy (FFT) | Fast numerical processing |
| Config | JSON (`./data/config.json`) | Portable, human-readable, zero extra deps |
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
| Database | SQLite (`./data/library.db`) | Portable, no server needed |
| Downloads | yt-dlp + ffmpeg | Best quality, opus format |
| Notifications | Native (notify-send/osascript) | Zero dependencies |
| Testing | pytest + pytest-asyncio | Real fixtures over mocks where feasible; see Testing section below |

### Audio Formats Supported

- **Primary**: Opus (download format)
- **Supported**: MP3, OGG, WAV, FLAC, M4A, AAC, WMA
- All formats supported by pygame/VLC. Metadata tag extraction (not just
  duration) is currently implemented for MP3/FLAC/OGG/Opus/M4A; WAV and WMA
  only report duration (see adapters/metadata/mutagen_adapter.py docstring
  for why).

## Project Structure

```
PyusicPlayer/
├── pyusicplayer/
│   ├── __init__.py                # Package init with version
│   ├── __main__.py                # Entry point (--tui implemented; --gui/--server exit with a clear "not implemented" message)
│   │
│   ├── core/                      # Business logic (NO dependencies)
│   │   ├── __init__.py
│   │   ├── models.py              # Track, Playlist, PlaylistMode (Fisher-Yates shuffle)
│   │   ├── services.py            # PlayerService
│   │   └── ports/                 # Protocol interfaces
│   │       ├── __init__.py        # Exports AudioPort, MetadataPort, LibraryPort (+ Artist/Album/Song/Collection); ConfigPort wired separately in di/container.py
│   │       ├── audio.py           # AudioPort Protocol (implemented)
│   │       ├── metadata.py        # MetadataPort Protocol (implemented)
│   │       ├── config.py          # ConfigPort Protocol + AppConfig dataclass (implemented)
│   │       ├── library.py         # LibraryPort Protocol (implemented — SqliteLibraryAdapter)
│   │       ├── lyrics.py          # LyricsPort Protocol (defined, no adapter, not wired)
│   │       ├── notifications.py   # NotificationsPort Protocol (defined, no adapter, not wired)
│   │       ├── downloader.py      # DownloaderPort Protocol (defined, no adapter, not wired)
│   │       └── visualizer.py      # VisualizerPort Protocol (defined, no adapter, not wired)
│   │
│   ├── adapters/                  # Concrete implementations
│   │   ├── __init__.py
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   └── pygame_adapter.py  # Real pygame backend: seek, position tracking, track-end detection all verified against real audio (see module docstring for the empirically-found quirks)
│   │   ├── metadata/
│   │   │   ├── __init__.py
│   │   │   └── mutagen_adapter.py # Mutagen reader: MP3/FLAC/OGG/Opus/M4A full tags, WAV/WMA duration-only
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── json_adapter.py    # JsonConfigAdapter: load/save AppConfig to ./data/config.json, atomic write via os.replace()
│   │   ├── library/
│   │   │   ├── __init__.py
│   │   │   └── sqlite_adapter.py  # SqliteLibraryAdapter: full LibraryPort — Artist/Album/Song/Collection CRUD, import_directory, get_stats. Constructor requires a MetadataPort.
│   │   ├── lyrics/                # empty stub, future phase
│   │   ├── notifications/         # empty stub, future phase
│   │   ├── downloader/            # empty stub, future phase
│   │   └── visualizer/            # empty stub, future phase
│   │
│   ├── interfaces/                # UI layer
│   │   ├── __init__.py
│   │   ├── tui/
│   │   │   ├── __init__.py
│   │   │   └── app.py             # Textual TUI: play/pause/stop/next/prev/seek/volume, now-playing highlight, mode/shuffle indicator bar
│   │   └── gui/                   # empty stub, future phase
│   │
│   └── di/
│       ├── __init__.py
│       └── container.py           # Container with register/resolve; create_container() wires AudioPort, MetadataPort, ConfigPort, LibraryPort (factory, lazy — only touches ./data/library.db when resolved). DATA_DIR = ./data/
│
├── tests/                         # pytest suite - see "Testing" section below
│   ├── conftest.py                # audio_fixtures (ffmpeg-generated), container fixtures
│   ├── core/                      # fast, no-I/O unit tests (models, services w/ fakes)
│   ├── adapters/                  # real pygame/mutagen/config tests
│   ├── di/                        # container wiring tests
│   └── interfaces/                # Textual App.run_test() integration tests
│
├── data/                          # Runtime-generated, gitignored
│   ├── config.json                # Persistent config (volume, repeat_mode, shuffle, last_playlist_path)
│   └── library.db                 # SQLite library — future phase
│
├── pytest.ini
├── requirements.txt                # runtime deps
├── requirements-dev.txt            # pytest + pytest-asyncio
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

Note: there is no `main.py` at the project root. An earlier draft of this
doc called it "legacy entry point (to be replaced)" - it has since been
removed entirely. The only entry point is `python -m pyusicplayer`.

## Keyboard Shortcuts

### Playback (implemented)
- `Space` - Play/Pause
- `S` - Stop
- `N` - Next track
- `P` - Previous track
- `←/→` - Seek backward/forward
- `↑/↓` - Volume up/down

### Playback Modes (implemented)
- `1` - Sequential
- `L` - Loop one
- `L` (uppercase, i.e. Shift+L on the physical key) - Loop all
- `R` - Shuffle

Note: the binding for loop-all is declared as `"L"` (uppercase), not
`"shift+l"`. Bug found in production: terminals send uppercase letters as
the character `L`, not as a `shift+l` modifier combination, so Textual
never matched the old `"shift+l"` binding - it was dead code. Regression
test drives this through `pilot.press("L")`, not by calling the action
method directly, so it can't pass while the binding itself is broken.

### Not implemented yet (documented for future phases)
- `M` - Mute
- `Y` / `V` - Toggle Lyrics/Visualizer (cover art is always visible, not a toggle - see "Media Display" above)
- `Ctrl+V` - Cycle visualizer style
- `F1` or `?` - Help
- `/` - Search library

## API Endpoints (FastAPI) — NOT IMPLEMENTED, future phase

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stream/{song_id}` | Stream audio with Range requests (seek) |
| GET | `/api/cover/{song_id}` | Get album art as image |
| GET | `/api/lyrics/{song_id}` | Get synchronized lyrics JSON |
| GET | `/api/library` | List songs with filters |
| GET | `/api/search?q=` | Search songs |
| POST | `/api/download` | Download audio from URL |

## Database Schema (SQLite) — IMPLEMENTED

Lives at `./data/library.db`, built by `SqliteLibraryAdapter`
(`adapters/library/sqlite_adapter.py`). Deliberately diverges from the
original draft schema above the "Implementation Status" section used to show
here: no `collections.path`/`last_scan`, no `songs.collection_id`,
`songs.duration_ms`, `songs.has_lyrics`, `songs.has_cover` — none of those
matched what `LibraryPort` (`core/ports/library.py`) actually specifies.

```sql
CREATE TABLE artists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_name TEXT,
    image_path TEXT
);

CREATE TABLE albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    year INTEGER,
    cover_path TEXT,
    disk_count INTEGER NOT NULL DEFAULT 1,
    UNIQUE (title, artist_id)
);

CREATE TABLE songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    title TEXT,
    artist_id INTEGER REFERENCES artists(id),
    album_id INTEGER REFERENCES albums(id),
    track_number INTEGER,
    disc_number INTEGER,
    duration REAL,             -- seconds, matches Track.duration elsewhere
    format TEXT,
    size INTEGER,
    last_modified TEXT,        -- ISO 8601 string; SQLite has no datetime type
    last_scanned TEXT
);

CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    is_smart INTEGER NOT NULL DEFAULT 0,
    query TEXT
);

-- Many-to-many: a song can belong to more than one collection at once
-- (e.g. a manual playlist AND a smart list). Deliberate deviation from a
-- songs.collection_id column, which would only allow one.
CREATE TABLE collection_songs (
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    song_id INTEGER NOT NULL REFERENCES songs(id),
    PRIMARY KEY (collection_id, song_id)
);
```

Design notes worth knowing before touching this code:
- `UNIQUE(title, artist_id)` on `albums` does **not** stop duplicate titles
  when `artist_id IS NULL` — SQLite treats every `NULL` as distinct in a
  UNIQUE index. Dedup for that case is application-level only, inside
  `get_or_create_album`. Covered explicitly by
  `TestSchemaConstraints::test_duplicate_album_title_with_null_artist_is_not_caught_by_db`.
- Case-insensitive search (`search_artists`/`search_albums`/`search_songs`)
  uses Python `str.casefold()` in application code, not SQL
  `LIKE ... COLLATE NOCASE` — `COLLATE NOCASE` only folds ASCII A-Z and
  misses accented case pairs (`Ä` U+00C4 → `ä` U+00E4), which matters for a
  library with ES/EN content.
- `add_song` is insert-only; a duplicate `file_path` (UNIQUE at the schema
  level) raises `ValueError`, not a raw `sqlite3.IntegrityError`. Re-scans
  go through `update_song` via `import_directory`, never through `add_song`
  twice.
- `import_directory` requires a `MetadataPort` (constructor-injected into
  `SqliteLibraryAdapter`). Re-scans are idempotent: a file whose filesystem
  mtime hasn't advanced past the stored `last_modified` is skipped; a
  changed file is updated via `update_song`; only genuinely new files count
  toward the returned total. A file that fails to parse (unsupported format,
  or a supported extension with corrupt content) is skipped with a
  `logging.WARNING` record naming the file, and the scan continues.
- `get_stats()` returns a fixed key set:
  `{"songs", "albums", "artists", "collections", "total_duration"}`.
  `total_duration` sums `songs.duration`, `NULL`s excluded by SQL `SUM()`
  semantics (not zero-padded), coalesced to `0.0` on an empty library so the
  return type is always `float`, never `None`.

## Configuration Schema — IMPLEMENTED

Config is persisted to `./data/config.json`. Phase 1 fields only:

```json
{
  "volume": 0.7,
  "repeat_mode": "none",
  "shuffle": false,
  "last_playlist_path": null
}
```

`AppConfig` dataclass lives in `core/ports/config.py`. The adapter
(`JsonConfigAdapter`) writes atomically via `os.replace()` on a `.tmp`
sibling. Unknown keys in the file are silently ignored (forward-compat).
Out-of-range volume is clamped to [0.0, 1.0] on load.

Future fields (layout, visualizer style, alternate views, etc.) will be
added to `AppConfig` when those phases are implemented.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Audio format | Opus (downloads) | Best quality/size ratio, document alternatives |
| Data directory | `./data/` (portable) | All runtime-generated files in one place; gitignored |
| Config file | `./data/config.json` | Human-readable, zero deps, atomic write via os.replace() |
| Database location | `./data/library.db` | Consistent with config location |
| API framework | FastAPI | Streaming + community + simplicity |
| Frontend | GUI + TUI + API | Full coverage |
| Lyrics | LRCLIB + local .lrc | Free + offline fallback |
| Visualizer | numpy FFT | Fast numerical processing |
| Visualizer styles | 5 styles | Full customization from start |
| i18n | gettext + Babel | Industry standard |
| Duration source | Track.duration (metadata), not AudioPort.get_duration() | pygame cannot report duration reliably for every format; AudioPort.get_duration() is a documented fallback stub only |
| Seek mechanism (pygame) | reload + `play(start=X)` | `pygame.mixer.music.set_pos()` was verified to be a silent no-op in this environment for mp3/ogg/wav |
| Test-first workflow | pytest, real audio fixtures over mocks where feasible | Two real bugs (pause double-counting, stop() firing a spurious end-event) were only caught this way - see Testing section |
| Previous-track restart threshold | 5.0s, `PlayerService.PREVIOUS_TRACK_RESTART_THRESHOLD_SECONDS` | Named constant, not a magic number, so it's trivial to retune later without hunting through the codebase |
| Shuffle bag exhaustion vs `mode` | shuffle only changes order; `mode` alone decides stop/loop-one/loop-all at bag exhaustion | Bug found in production: shuffle was implicitly looping forever regardless of `mode=NONE`. Fixed with a `_shuffle_bag_initialized` flag to distinguish "never filled" (first advance, must still play something) from "exhausted after a full cycle" (must stop unless `mode=ALL`) |
| Collection membership | many-to-many (`collection_songs` join table), not `songs.collection_id` | `LibraryPort.add_to_collection`/`get_collection_songs` only make sense if a song can be in more than one collection at once (playlist + smart list) |
| Library search case-folding | Python `str.casefold()` in application code, not SQL `COLLATE NOCASE` | `COLLATE NOCASE` only folds ASCII A-Z; misses accented case pairs (Ä→ä), which matters for ES/EN content |
| `add_song` on duplicate `file_path` | raises `ValueError`, insert-only | `update_song` is the separate, explicit path for changes; silent upsert would hide re-scan bugs |
| `import_directory` re-scan | idempotent by filesystem mtime vs stored `last_modified`: skip unchanged, `update_song` changed, only new files counted | Re-running an import over an unchanged library must be a cheap no-op, not a pile of duplicate-path errors |
| `import_directory` per-file failures | skip + `logging.WARNING` with the file path, scan continues | One corrupt file in a library of hundreds must not abort the whole import |

## Important Notes

- **Architecture over playability**: Prioritize perfect architecture over something playable — in practice this produced a fully-designed skeleton with zero working adapters at one point; the current codebase corrects that by keeping ports/adapters minimal but real and working end-to-end before adding more surface area.
- **Modular design**: Any component should be swappable without breaking others
- **Cross-platform**: Linux, Windows, macOS support (only tested on Linux so far)
- **Notifications**: planned, not implemented
- **GUI as background process**: planned, not implemented
- **Alternate views**: planned, not implemented
- **Layout configurable**: planned, not implemented

## Testing

Tests live under `tests/`, mirroring the `pyusicplayer/` package layout.

**Workflow going forward: write the test first, watch it fail for the right
reason, then write the code that makes it pass.** This isn't retroactive
busywork - it already found a real bug during this project's own test-writing
pass (`pygame.mixer.music.stop()` fires the same end-of-track event as
natural completion, which would have made the Stop key spuriously
auto-advance to the next track; the test written for the "does NOT fire on
explicit stop" case caught it before it shipped).

### Running tests

```bash
pip install -r requirements-dev.txt

# Full suite
pytest

# Fast loop while developing (skips real pygame/mutagen audio tests)
pytest -m "not audio"

# Just one layer
pytest tests/core/
```

### Layout and philosophy

| Layer | What it tests | Real I/O? |
|-------|---------------|-----------|
| `tests/core/test_models.py` | `Track`, `Playlist` (Fisher-Yates shuffle, sequential/loop modes) | No - pure logic |
| `tests/core/test_services.py` | `PlayerService` against `FakeAudioPort`/`FakeMetadataPort` test doubles | No - fast, in-memory |
| `tests/adapters/test_pygame_adapter.py` | Real `pygame.mixer.music` against ffmpeg-generated audio: seek, position tracking, pause/resume drift, track-end detection | Yes - real (headless/dummy-driver) pygame |
| `tests/adapters/test_mutagen_adapter.py` | Real `mutagen` extraction across every supported format | Yes - real files |
| `tests/adapters/test_config_adapter.py` | `JsonConfigAdapter`: load/save/defaults/corruption/clamping/atomicity | No - tmp_path only |
| `tests/adapters/test_sqlite_library_adapter.py` | `SqliteLibraryAdapter`: full `LibraryPort` — lifecycle, Artist/Album/Song/Collection CRUD, schema UNIQUE constraints, `import_directory` (real `MutagenMetadataAdapter` + ffmpeg fixtures, idempotent re-scan, per-file failure isolation), `get_stats` — 89 tests | Import tests: yes, real ffmpeg-generated audio. Everything else: tmp_path only |
| `tests/di/test_container.py` | `create_container()` actually wires adapters (this is what was broken before: an empty container that resolved nothing) | No |
| `tests/interfaces/test_tui_app.py` | Full Textual `App.run_test()` harness: playlist loading, now-playing highlight, mode bar, pause/resume regression at the app level | Yes - real pygame + real Textual event loop |
| `tests/interfaces/test_tui_config.py` | TUI restores volume/shuffle/repeat_mode from `ConfigPort` on mount, persists them on unmount; falls back to defaults if no config file | No - tmp_path only, empty playlist folder (no audio needed) |

`tests/core/test_models.py::TestPlaylistShuffleRespectsMode` and
`tests/interfaces/test_tui_app.py::test_loop_all_keybinding_actually_triggers_via_keypress`
are the regression tests for the two bugs above - both were written first,
confirmed red for the right reason, then fixed.

Audio-backed tests are marked `@pytest.mark.audio` (or module-level
`pytestmark = pytest.mark.audio`) and are skipped, not failed, if `ffmpeg`
isn't on `PATH` - fixture generation happens once per test session in
`tests/conftest.py::audio_fixtures`, not from committed binary files.

### What isn't covered yet

No tests exist for the empty adapter stubs (lyrics/notifications/downloader/
visualizer) or the GUI/API interfaces, because none of that code exists yet
either. When those get implemented, tests are written first, per the
workflow above - not bundled in afterward. Note `test_container.py`
deliberately does not resolve `LibraryPort` through the shared `container`
fixture, for the same reason it never resolved `ConfigPort` that way: the
factory points at the real `./data/library.db` path, and resolving it would
create/touch that file as a side effect of running the test suite.

## Implementation Status

### Completed and tested
- [x] Core domain models: `Track`, `Playlist` with Fisher-Yates shuffle bag, sequential/loop-one/loop-all modes
- [x] `PlayerService`: playback orchestration, duration-from-metadata (not audio backend), auto-advance on track end, seek clamping, volume clamping, double-tap-previous restart threshold
- [x] `Playlist.next_index()`: shuffle bag exhaustion now correctly respects `mode` (stop on NONE, refill+loop on ALL) instead of always looping regardless of mode
- [x] `AudioPort` + `MetadataPort` + `ConfigPort` protocols
- [x] `PygameAudioAdapter`: real seek (reload+`play(start=X)`, since `set_pos()` doesn't work), position tracking, pause/resume without double-counting, track-end detection without false positives on explicit stop
- [x] `MutagenMetadataAdapter`: full tag extraction for MP3/FLAC/OGG/Opus/M4A, duration-only for WAV/WMA, no silent failures
- [x] `JsonConfigAdapter`: load/save `AppConfig` to `./data/config.json`, atomic write, defaults on missing/corrupt file, volume clamping, forward-compat unknown-key tolerance — 11 tests
- [x] TUI reads/writes config on startup/exit: volume/shuffle/repeat_mode restored in `on_mount`, persisted in `on_unmount` — 8 tests
- [x] `SqliteLibraryAdapter`: full `LibraryPort` — lifecycle, Artist/Album/Song/Collection CRUD (many-to-many collection membership, DB-level UNIQUE constraints, Unicode-correct case-insensitive search), `import_directory` (idempotent re-scan, per-file failure isolation with logging, real `MutagenMetadataAdapter` integration), `get_stats` — 89 tests
- [x] `Container`/`create_container()`: wires AudioPort, MetadataPort, ConfigPort, LibraryPort (lazy factory)
- [x] TUI (`interfaces/tui/app.py`, Textual): playlist from folder scan, play/pause/stop/next/prev/seek/volume, now-playing highlight, mode/shuffle indicator bar
- [x] `python -m pyusicplayer --tui` entry point; `--gui`/`--server` exit with an explicit "not implemented" message instead of crashing
- [x] Test suite: 197 tests across core/adapters/di/interfaces layers

### Not started (planned, no code, no adapters, no wiring)
- [ ] Cover art extraction (mutagen embedded APIC/covr) + fixed display in the artist/title block
- [ ] Lyrics adapter (LRCLIB + local .lrc)
- [ ] Notifications adapter
- [ ] Visualizer (FFT, 5 styles)
- [ ] Downloader (yt-dlp)
- [ ] GUI (CustomTkinter)
- [ ] FastAPI server
- [ ] i18n translations

### Next steps (in the order they'll likely be tackled)
1. Cover art extraction (mutagen embedded APIC/covr) + fixed display in the artist/title block — test-first
2. Visualizer (FFT) — test-first
3. Lyrics adapter — test-first
4. Notifications adapter — test-first
5. GUI (CustomTkinter) — test-first
6. FastAPI server — test-first
7. i18n translations
