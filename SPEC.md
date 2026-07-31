# PyusicPlayer - Technical Specification

## 1. Overview

PyusicPlayer is a modular, cross-platform music player written in Python. It supports multiple interfaces (TUI, GUI, API) and uses a Ports & Adapters architecture to ensure component swappability without side effects.

## 2. Functional Requirements

### 2.1 Playback Engine

| Feature | Description | Priority |
|---------|-------------|----------|
| Play | Start playback of loaded track | P0 |
| Pause | Pause current playback | P0 |
| Resume | Resume paused playback | P0 |
| Stop | Stop playback, reset position | P0 |
| Seek | Jump to specific position in track (ms precision) | P1 |
| Next | Skip to next track in playlist | P0 |
| Previous | Skip to previous track in playlist | P0 |
| Volume | Adjustable volume (0-100%) | P0 |
| State events | Notify listeners on state change | P0 |

### 2.2 Playlist Management

| Feature | Description | Priority |
|---------|-------------|----------|
| Sequential | Play tracks in order | P0 |
| Loop One | Repeat current track | P0 |
| Loop All | Repeat entire playlist | P0 |
| Shuffle | Random order (Fisher-Yates) | P0 |
| Queue | Manual queue management | P2 |

### 2.3 Media Display

#### 2.3.1 Always Visible
- Player controls and progress bar
- Current track info (title, artist, album)

#### 2.3.2 Alternate Views (Independent Toggles)

| View | Description | Toggle Key | Priority |
|------|-------------|------------|----------|
| Lyrics | Synchronized lyrics display | Y | P1 |
| Cover Art | Album art visualization | C | P1 |
| Visualizer | Audio spectrum analyzer | V | P1 |

### 2.4 Audio Spectrum Visualizer

| Feature | Description | Priority |
|---------|-------------|----------|
| Bars Vertical | Classic equalizer bars (CAVA/Winamp style) | P0 |
| Bars Horizontal | Modern horizontal bars | P0 |
| Waveform | Real-time waveform display | P0 |
| Radial | Circular/radial visualization | P0 |
| Particles | Beat-reactive particle effects | P0 |
| Cycle style | Ctrl+V cycles through 5 styles | P0 |
| Configurable | Bars count, smoothing, sensitivity | P1 |

### 2.5 Help System

| Feature | Description | Priority |
|---------|-------------|----------|
| TUI Modal | F1 opens ModalScreen with shortcuts | P0 |
| GUI Menu | Help menu with dialog | P0 |
| GUI F1 | F1 opens help dialog | P0 |
| Comprehensive | All controls and keybindings listed | P0 |

### 2.6 Layout Configuration

| Feature | Description | Priority |
|---------|-------------|----------|
| Side-by-side | Alternate view on right panel | P0 |
| Stacked | Alternate view below controls | P0 |
| Configurable | Settings + keyboard cycling | P0 |
| Cycle layout | Shift+L cycles layout mode | P0 |

### 2.7 Metadata & Display

| Feature | Description | Priority |
|---------|-------------|----------|
| Album art | Extract from ID3 tags or folder cover.jpg/png | P1 |
| Placeholder | Default image when no art available | P1 |
| Lyrics (local) | Parse .lrc files from same directory | P1 |
| Lyrics (API) | Fetch from LRCLIB as fallback | P1 |
| Lyrics sync | Synchronized lyrics display | P2 |

### 2.8 Library Management

| Feature | Description | Priority |
|---------|-------------|----------|
| Scan folder | Recursively scan for audio files | P0 |
| Import collection | Add folder as named collection | P0 |
| Refresh | Detect added/removed/modified files | P1 |
| Filter | By artist, album, folder, collection | P0 |
| Search | Full-text search across metadata | P1 |
| Index | SQLite database for fast queries | P0 |

### 2.9 Download

| Feature | Description | Priority |
|---------|-------------|----------|
| yt-dlp | Download audio from URLs | P1 |
| Format | Opus (configurable: mp3, flac) | P1 |
| Metadata | Embed title, artist, album | P1 |
| Thumbnail | Embed album art | P1 |
| Progress | Download progress callback | P2 |

### 2.10 API Server

| Feature | Description | Priority |
|---------|-------------|----------|
| Stream | HTTP streaming with Range requests | P0 |
| Cover | Serve album art as image | P0 |
| Lyrics | Serve lyrics as JSON | P0 |
| Library | List and filter songs | P0 |
| Search | Search endpoint | P1 |
| Download | Trigger download from URL | P2 |
| CORS | Allow web/Android clients | P0 |

### 2.11 Notifications

| Feature | Description | Priority |
|---------|-------------|----------|
| Track change | Notify on new track | P1 |
| State change | Notify on play/pause/stop | P2 |
| Platform | Linux (notify-send), macOS (osascript), Windows (win10toast) | P1 |

## 3. Non-Functional Requirements

### 3.1 Architecture

- **Pattern**: Ports & Adapters (Hexagonal Architecture)
- **Dependency Injection**: Container-based wiring at entry point
- **Coupling**: Modules depend only on Protocol interfaces
- **Testability**: Each component testable in isolation

### 3.2 Cross-Platform

- Linux (primary)
- Windows
- macOS

### 3.3 Performance

- Audio seek latency: < 100ms
- Library scan: ~1000 songs/second
- API response: < 50ms (excluding streaming)
- Visualizer FPS: 60fps target
- FFT processing: < 16ms per frame
- Memory usage: < 200MB normal operation

### 3.4 Configuration

- Portable: `./data/config.json`
- Global: `~/.config/pyusicplayer/config.json` (XDG)
- Priority: portable > global > defaults

### 3.5 Internationalization

- Languages: English (en_US), Spanish (es_ES)
- Framework: gettext + Babel
- Files: `.po` (source), `.mo` (compiled)

## 4. Technical Specifications

### 4.1 Audio Backend Protocol

```python
class AudioBackend(Protocol):
    """Interface for audio playback backends."""
    
    def load(self, file_path: str) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    def seek(self, position_ms: int) -> None: ...
    
    @property
    def position(self) -> int: ...
    
    @property
    def duration(self) -> int: ...
    
    @property
    def state(self) -> PlayerState: ...
    
    def on_state_change(self, callback: Callable) -> None: ...
    def on_track_end(self, callback: Callable) -> None: ...
```

### 4.2 Metadata Reader Protocol

```python
class MetadataReader(Protocol):
    """Interface for reading audio metadata."""
    
    def read(self, file_path: str) -> SongMetadata: ...
    def get_cover(self, file_path: str) -> Optional[bytes]: ...
    def has_cover(self, file_path: str) -> bool: ...
```

### 4.3 Lyrics Provider Protocol

```python
class LyricsProvider(Protocol):
    """Interface for fetching lyrics."""
    
    def get_lyrics(self, artist: str, title: str) -> Optional[Lyrics]: ...
    def has_lyrics(self, artist: str, title: str) -> bool: ...
```

### 4.4 Library Indexer Protocol

```python
class LibraryIndexer(Protocol):
    """Interface for library indexing."""
    
    def scan_folder(self, path: str, recursive: bool = True) -> ScanResult: ...
    def search(self, query: str, filters: SearchFilters) -> list[Song]: ...
    def get_all(self, sort_by: str = "artist") -> list[Song]: ...
    def refresh(self, collection_id: str) -> ScanResult: ...
```

### 4.5 Downloader Protocol

```python
class Downloader(Protocol):
    """Interface for downloading audio."""
    
    def download(self, url: str, output_dir: str) -> DownloadResult: ...
    def get_info(self, url: str) -> VideoInfo: ...
```

### 4.6 Notifier Protocol

```python
class Notifier(Protocol):
    """Interface for desktop notifications."""
    
    def notify(self, title: str, message: str, icon: str = None) -> None: ...
```

### 4.7 Config Provider Protocol

```python
class ConfigProvider(Protocol):
    """Interface for configuration."""
    
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def save(self) -> None: ...
    def load(self) -> None: ...
    def reset(self) -> None: ...
```

### 4.8 Visualizer Protocol

```python
class Visualizer(Protocol):
    """Interface for audio spectrum visualizers."""
    
    def start(self, sample_rate: int = 44100) -> None: ...
    def stop(self) -> None: ...
    def update(self, audio_data: np.ndarray) -> None: ...
    def set_style(self, style: VisualizerStyle) -> None: ...
    def resize(self, width: int, height: int) -> None: ...
    
    @property
    def is_running(self) -> bool: ...
    
    @property
    def current_style(self) -> VisualizerStyle: ...
```

### 4.9 Visualizer Style Enum

```python
class VisualizerStyle(Enum):
    """Available visualization styles."""
    BARS_VERTICAL = auto()    # Classic equalizer (CAVA/Winamp)
    BARS_HORIZONTAL = auto()  # Horizontal bars
    WAVEFORM = auto()         # Waveform display
    RADIAL = auto()           # Circular/radial
    PARTICLES = auto()        # Beat-reactive particles

# Order for cycling with keyboard
VISUALIZER_STYLES_ORDER = [
    VisualizerStyle.BARS_VERTICAL,
    VisualizerStyle.BARS_HORIZONTAL,
    VisualizerStyle.WAVEFORM,
    VisualizerStyle.RADIAL,
    VisualizerStyle.PARTICLES,
]
```

### 4.10 Visualizer Base Class

```python
class BaseVisualizer(ABC):
    """Base class with FFT processing for all visualizers."""
    
    def __init__(self):
        self._is_running = False
        self._sample_rate = 44100
        self._fft_size = 1024
        self._width = 800
        self._height = 400
        self._fft_buffer = np.zeros(self._fft_size)
        self._frequency_data = np.zeros(self._fft_size // 2)
    
    def start(self, sample_rate: int = 44100) -> None:
        self._sample_rate = sample_rate
        self._is_running = True
    
    def stop(self) -> None:
        self._is_running = False
    
    def update(self, audio_data: np.ndarray) -> None:
        if not self._is_running:
            return
        
        # Apply Hann window to reduce spectral leakage
        window = np.hanning(len(audio_data))
        windowed = audio_data * window
        
        # FFT
        fft_data = np.fft.rfft(windowed)
        magnitudes = np.abs(fft_data)
        
        # Exponential smoothing
        alpha = 0.3
        self._frequency_data = (
            alpha * magnitudes[:len(self._frequency_data)] + 
            (1 - alpha) * self._frequency_data
        )
        
        # Call style-specific render
        self._render(self._frequency_data)
    
    @abstractmethod
    def _render(self, frequency_data: np.ndarray) -> None:
        """Render according to style. Each adapter implements this."""
        pass
    
    def resize(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
```

## 5. Keyboard Shortcuts

### 5.1 Playback

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `S` | Stop |
| `N` | Next track |
| `P` | Previous track |
| `←` | Seek backward |
| `→` | Seek forward |
| `↑` | Volume up |
| `↓` | Volume down |
| `M` | Mute |

### 5.2 Playback Modes

| Key | Action |
|-----|--------|
| `1` | Sequential |
| `L` | Loop one |
| `Shift+L` | Loop all |
| `R` | Shuffle |

### 5.3 Alternate Views (Independent Toggles)

| Key | Action |
|-----|--------|
| `Y` | Toggle Lyrics on/off |
| `C` | Toggle Cover on/off |
| `V` | Toggle Visualizer on/off |

### 5.4 Visualizer

| Key | Action |
|-----|--------|
| `Ctrl+V` | Cycle visualizer style (5 styles) |

### 5.5 Layout

| Key | Action |
|-----|--------|
| `Shift+L` | Cycle layout (side_by_side / stacked) |

### 5.6 Utilities

| Key | Action |
|-----|--------|
| `F1` or `?` | Help |
| `/` | Search library |
| `Q` | Quit |

## 6. API Specification

### 6.1 Base URL

```
http://localhost:{port}/api
```

Port is auto-discovered (default 8000, or random if busy).

### 6.2 Endpoints

#### GET /api/stream/{song_id}

Stream audio file with Range request support.

**Headers:**
- `Range: bytes=0-` (optional, for seeking)

**Response:**
- `200 OK` - Full audio
- `206 Partial Content` - Range response

**Content-Type:** `audio/opus`

#### GET /api/cover/{song_id}

Get album art image.

**Response:**
- `200 OK` - Image data
- `404 Not Found` - No cover available

**Content-Type:** `image/jpeg` or `image/png`

#### GET /api/lyrics/{song_id}

Get synchronized lyrics.

**Response:**
```json
{
  "lyrics": [
    {"time": 0, "text": "First line"},
    {"time": 5000, "text": "Second line"}
  ],
  "language": "en"
}
```

#### GET /api/library

List songs with optional filters.

**Query Parameters:**
- `artist` - Filter by artist
- `album` - Filter by album
- `collection` - Filter by collection ID
- `sort` - Sort field (artist, album, title, date_added)
- `limit` - Max results (default 100)
- `offset` - Pagination offset

**Response:**
```json
{
  "songs": [...],
  "total": 1234,
  "limit": 100,
  "offset": 0
}
```

#### GET /api/search

Search songs.

**Query Parameters:**
- `q` - Search query
- `limit` - Max results

**Response:**
```json
{
  "songs": [...],
  "total": 42
}
```

#### POST /api/download

Download audio from URL.

**Request Body:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "format": "opus"
}
```

**Response:**
```json
{
  "status": "downloading",
  "task_id": "abc123"
}
```

## 7. Database Schema

### 7.1 Collections

```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    last_scan TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_collections_path ON collections(path);
```

### 7.2 Artists

```sql
CREATE TABLE artists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE INDEX idx_artists_name ON artists(name);
```

### 7.3 Albums

```sql
CREATE TABLE albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    year INTEGER
);

CREATE INDEX idx_albums_artist ON albums(artist_id);
CREATE INDEX idx_albums_title ON albums(title);
```

### 7.4 Songs

```sql
CREATE TABLE songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    album_id INTEGER REFERENCES albums(id),
    collection_id INTEGER REFERENCES collections(id),
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT,
    duration_ms INTEGER,
    format TEXT,
    bitrate INTEGER,
    has_lyrics BOOLEAN DEFAULT FALSE,
    has_cover BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_songs_artist ON songs(artist_id);
CREATE INDEX idx_songs_album ON songs(album_id);
CREATE INDEX idx_songs_collection ON songs(collection_id);
CREATE INDEX idx_songs_path ON songs(file_path);
```

## 8. Configuration Schema

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
  },
  "library": {
    "collections": [],
    "auto_refresh": true
  },
  "download": {
    "format": "opus",
    "output_dir": "./downloads",
    "embed_thumbnail": true,
    "embed_metadata": true
  },
  "notifications": {
    "enabled": true,
    "on_track_change": true,
    "on_state_change": false
  },
  "appearance": {
    "theme": "dark",
    "language": "en_US"
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8000,
    "auto_start": false
  }
}
```

## 9. Dependencies

### 9.1 Core

```
pygame>=2.5.0          # Audio backend (primary)
mutagen>=1.47.0        # Metadata reading
textual>=0.40.0        # TUI framework
customtkinter>=5.2.0   # GUI framework
fastapi>=0.100.0       # API server
uvicorn>=0.20.0        # ASGI server
requests>=2.31.0       # HTTP client (LRCLIB)
yt-dlp>=2024.0.0       # Audio download
numpy>=1.24.0          # FFT and numerical processing
babel>=2.14.0          # i18n
```

### 9.2 Optional

```
python-vlc>=3.0.0      # Alternative audio backend
tinytag>=1.10.0        # Alternative metadata reader
```

### 9.3 Dev

```
pytest>=7.0.0
pytest-cov>=4.0.0
mypy>=1.0.0
ruff>=0.1.0
```

## 10. Testing Strategy

- **Unit Tests**: Each adapter independently
- **Integration Tests**: Service + port combinations
- **Contract Tests**: Verify Protocol implementations
- **E2E Tests**: Full user workflows
- **Visualizer Tests**: FFT correctness, rendering performance

## 11. Deployment

### 11.1 Local

```bash
# TUI mode
python main.py --tui

# GUI mode
python main.py --gui

# Server mode (headless)
python main.py --server --port 8000

# Combined (GUI + API)
python main.py --gui --api
```

### 11.2 Packaging

- PyInstaller for standalone executables
- Flatpak/Snap for Linux
- DMG for macOS
- Installer for Windows

## 12. Future Considerations

- Spotify/Last.fm integration
- Equalizer
- Crossfade between tracks
- Podcast support
- Multi-device sync
- Web UI (React/Vue)
- Android/iOS native clients
- Custom visualizer themes
- Audio effects (reverb, echo)
