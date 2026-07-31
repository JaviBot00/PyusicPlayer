# PyusicPlayer - Concept

Create an interactive music player in Python that can be run in TUI and GUI.

---

## Player Features

### Core Controls
- Play, Pause, Resume, Stop
- Seek (advance/rewind within a song)
- Next/Previous track

### Playback Modes
- Sequential (play in order)
- Loop one (repeat current track)
- Loop all (repeat entire playlist)
- Shuffle (random order)

### Media Display (Always Visible)
- Player controls and progress bar
- Current track info (title, artist, album)

### Alternate Views (Independent Toggles)
- **Lyrics**: Synchronized lyrics (or message if not available)
- **Cover Art**: Album art visualization (or placeholder if not available)
- **Audio Spectrum Analyzer**: Real-time frequency visualization

### Audio Spectrum Visualizer
- 5 visualization styles (all available from start):
  - **Bars Vertical**: Classic equalizer bars (CAVA/Winamp style)
  - **Bars Horizontal**: Modern horizontal bars
  - **Waveform**: Real-time waveform display
  - **Radial**: Circular/radial visualization
  - **Particles**: Beat-reactive particle effects
- Cycle through styles with keyboard shortcut
- Configurable via settings (bars count, smoothing, sensitivity)

### Help System
- TUI: F1 opens ModalScreen with all shortcuts
- GUI: Help menu + F1 opens dialog with shortcuts
- Comprehensive list of controls and keybindings

### Configuration
- Customizable settings
- Restore to defaults
- Portable (local) + global (XDG) storage
- Layout configuration (side-by-side or stacked)

### Download Support
- Download audio from YouTube/SoundCloud/etc via yt-dlp
- Format: Opus (optimal quality/size)
- Embed metadata and thumbnail

### Library Management
- Index and organize music in SQLite database
- Filter by artist, album, folder
- Import multiple folders recursively
- Separate collections management
- Refresh detection for changes

---

## Interfaces

### TUI (Terminal User Interface)
- Framework: Textual
- Keyboard and mouse control
- Rich terminal visuals
- ModalScreen for help (F1)
- Configurable layout (side-by-side / stacked)

### GUI (Graphical User Interface)
- Framework: CustomTkinter
- Modern look
- Executable as background process
- Help menu + F1 dialog
- Configurable layout

### API Server
- Framework: FastAPI
- Streaming audio with Range requests
- Endpoints for web/Android clients
- Auto-generated OpenAPI docs

---

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

---

## Requirements

### Architecture
- Ports & Adapters (Hexagonal Architecture)
- Modular design for swappability
- Dependency injection via container
- Never import concrete implementations in business logic

### Cross-Platform
- Linux (primary)
- Windows
- macOS

### Interactions
- Mouse control (GUI)
- Keyboard control (TUI)
- Pop-up notifications when window not focused

### Distribution
- GUI as executable/background process
- No terminal window required
- Portable configuration

---

## Technology Stack

| Component | Technology | Alternative |
|-----------|------------|-------------|
| Audio backend | pygame | python-vlc |
| Metadata | mutagen + EasyID3 | tinytag |
| TUI | Textual | prompt_toolkit |
| GUI | CustomTkinter | PySide6 |
| API | FastAPI | Litestar |
| Database | SQLite | - |
| Downloads | yt-dlp | - |
| Visualizer | numpy (FFT) | scipy |
| i18n | gettext + Babel | - |
| Notifications | Native (notify-send/osascript) | plyer |

---

## Important

- **Prioritize perfect architecture over something playable**
- Any component should be swappable without breaking others
- All decisions documented in AGENT.md, SPEC.md, LEARNING.md
