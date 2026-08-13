"""Minimal Textual TUI: playlist + transport controls + progress bar.

Scope for this first implementation cycle (P0 only):
  play/pause/stop/next/prev, seek, volume, playlist from a folder scan,
  now-playing highlight, playback-mode/shuffle indicator bar,
  config persistence (volume/mode/shuffle restored on startup, saved on exit).
Deliberately NOT implemented yet (agreed as out-of-scope for this cycle):
  lyrics/cover/visualizer alternate views, layout toggle, help modal,
  library DB, downloader, notifications, i18n, GUI, API server.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, ListItem, ListView, Label, ProgressBar, Static

from ...core.models import PlaylistMode
from ...core.ports import PlaybackState
from ...core.ports.config import AppConfig, ConfigPort
from ...core.ports.cover_renderer import CoverRenderMode
from ...core.services import PlayerService
from ...di.container import Container
from .screens.settings_screen import SettingsScreen

# Deliberate, documented exception to the "only di/container.py imports
# concrete adapters" rule (see AGENT.md "Key Decisions" - Cover render
# backend selection): create_cover_renderer() takes a runtime mode string
# that can change after a settings screen edits AppConfig, but
# Container.resolve() memoizes factory results into singletons, so routing
# this through DI would cache a stale renderer past the first mode change.
from ...adapters.cover_renderer.factory import create_cover_renderer

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".wma"}

_MODE_ICONS = [
    (PlaylistMode.NONE, "➡", "Seq"),
    (PlaylistMode.ONE, "🔂", "One"),
    (PlaylistMode.ALL, "🔁", "All"),
]
_SHUFFLE_ICON = "🔀"

_REPEAT_MODE_MAP: dict[str, PlaylistMode] = {
    "none": PlaylistMode.NONE,
    "one": PlaylistMode.ONE,
    "all": PlaylistMode.ALL,
}
_PLAYLIST_MODE_MAP: dict[PlaylistMode, str] = {v: k for k, v in _REPEAT_MODE_MAP.items()}

_COVER_WIDTH = 20
_COVER_HEIGHT = 8


def scan_music_folder(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    return sorted(
        str(p) for p in folder.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


class TrackListItem(ListItem):
    def __init__(self, index: int, base_label: str) -> None:
        super().__init__(Label(base_label))
        self.track_index = index
        self._base_label = base_label

    def set_playing(self, is_playing: bool) -> None:
        label = self.query_one(Label)
        if is_playing:
            label.update(f"▶ {self._base_label}")
            self.add_class("now-playing")
        else:
            label.update(f"  {self._base_label}")
            self.remove_class("now-playing")


class PyusicPlayerApp(App):
    """Terminal music player."""

    CSS = """
    #media-display {
        height: 8;
    }
    #cover-art {
        width: 22;
        height: 8;
        content-align: center middle;
    }
    #now-playing {
        height: 8;
        content-align: center middle;
        text-style: bold;
    }
    #mode-bar {
        height: 1;
        content-align: center middle;
    }
    #progress-row {
        height: 3;
        align: center middle;
    }
    ProgressBar {
        width: 60;
    }
    ListView {
        height: 1fr;
    }
    TrackListItem.now-playing {
        background: $accent;
    }
    TrackListItem.now-playing Label {
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("s", "stop", "Stop"),
        Binding("n", "next_track", "Next"),
        Binding("p", "previous_track", "Previous"),
        Binding("left", "seek_backward", "Seek -5s"),
        Binding("right", "seek_forward", "Seek +5s"),
        Binding("up", "volume_up", "Vol +"),
        Binding("down", "volume_down", "Vol -"),
        Binding("1", "mode_sequential", "Sequential"),
        Binding("l", "mode_loop_one", "Loop one"),
        Binding("L", "mode_loop_all", "Loop all"),
        Binding("r", "toggle_shuffle", "Shuffle"),
        Binding("comma", "open_settings", "Settings"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, container: Container, music_folder: Path) -> None:
        super().__init__()
        self._music_folder = music_folder
        self.player: PlayerService = container.resolve(PlayerService)
        self._config_adapter: ConfigPort = container.resolve(ConfigPort)
        self._added = 0
        self._playing_item: TrackListItem | None = None
        self._cover_render_mode: str = CoverRenderMode.PLACEHOLDER  # overwritten from config in on_mount

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="media-display"):
            yield Static("", id="cover-art")
            yield Static("Nothing loaded", id="now-playing")
        yield Static("", id="mode-bar")
        with Vertical(id="progress-row"):
            yield ProgressBar(total=100, show_eta=False, id="progress")
            yield Static("--:-- / --:--", id="time-label")
        yield ListView(id="playlist-view")
        yield Footer()

    def on_mount(self) -> None:
        self.player.initialize()

        # --- Restore persisted config ---
        config: AppConfig = self._config_adapter.load()
        self.player.volume = config.volume
        self.player.playlist.shuffle = config.shuffle
        self.player.playlist.mode = _REPEAT_MODE_MAP.get(config.repeat_mode, PlaylistMode.NONE)
        self._cover_render_mode = config.cover_render_mode
        self._render_cover(None)  # always visible: show placeholder before any track loads

        # --- Load playlist ---
        self._added = self.player.add_files(scan_music_folder(self._music_folder))
        list_view = self.query_one("#playlist-view", ListView)
        for i, track in enumerate(self.player.playlist.tracks):
            list_view.append(TrackListItem(i, f"{i + 1:>3}. {track.display_name} ({track.format_duration})"))

        now_playing = self.query_one("#now-playing", Static)
        if self._added == 0:
            now_playing.update(f"No audio files found in {self._music_folder}")
        else:
            now_playing.update(f"{self._added} tracks loaded — select one and press Enter")

        self.player.on_state_change(self._on_state_change)
        self.player.on_track_change(self._on_track_change)
        self._refresh_mode_bar()
        self.set_interval(0.2, self._tick)

    def on_unmount(self) -> None:
        # --- Persist current state ---
        config = AppConfig(
            volume=self.player.volume,
            shuffle=self.player.playlist.shuffle,
            repeat_mode=_PLAYLIST_MODE_MAP.get(self.player.playlist.mode, "none"),
            cover_render_mode=self._cover_render_mode,
        )
        self._config_adapter.save(config)
        self.player.shutdown()

    def _on_track_change(self, track) -> None:
        self.query_one("#now-playing", Static).update(track.display_name)
        self._render_cover(track)
        list_view = self.query_one("#playlist-view", ListView)
        if self._playing_item is not None:
            self._playing_item.set_playing(False)
        for item in list_view.children:
            if isinstance(item, TrackListItem) and item.track_index == self.player.playlist.current_index:
                item.set_playing(True)
                self._playing_item = item
                break

    def _render_cover(self, track) -> None:
        """Rebuilds the renderer on every call instead of caching one on
        self - CoverRendererPort adapters are cheap to construct (they just
        wrap decode/resize logic, no state), and rebuilding means a settings
        screen changing self._cover_render_mode takes effect on the very
        next track/refresh without needing a separate invalidation path."""
        cover_data = track.cover_data if track else None
        cover_mime = track.cover_mime if track else None
        renderer = create_cover_renderer(self._cover_render_mode)
        rendered = renderer.render(cover_data, cover_mime, _COVER_WIDTH, _COVER_HEIGHT)
        self.cover_render_text = rendered  # exposed for tests, same pattern as self.mode_bar_text
        self.query_one("#cover-art", Static).update(rendered)

    def _refresh_mode_bar(self) -> None:
        parts = []
        for mode, icon, label in _MODE_ICONS:
            active = self.player.playlist.mode == mode
            parts.append(f"[reverse] {icon} {label} [/]" if active else f" {icon} {label} ")
        shuffle_active = self.player.playlist.shuffle
        shuffle_part = f"[reverse] {_SHUFFLE_ICON} Shuffle [/]" if shuffle_active else f" {_SHUFFLE_ICON} Shuffle "
        self.mode_bar_text = "  ".join(parts) + "   │   " + shuffle_part
        self.query_one("#mode-bar", Static).update(self.mode_bar_text)

    def _on_state_change(self, state: PlaybackState) -> None:
        pass  # progress bar / labels are refreshed by the periodic _tick instead

    def _tick(self) -> None:
        self.player.poll()
        duration = self.player.get_duration()
        position = self.player.get_position()
        try:
            progress = self.query_one("#progress", ProgressBar)
            time_label = self.query_one("#time-label", Static)
        except NoMatches:
            # DOM not fully mounted yet (race between set_interval firing
            # and the widget tree completing) - skip this tick, next one
            # 200ms later will find the widgets.
            return
        if duration > 0:
            progress.update(total=100, progress=min(100, (position / duration) * 100))
        time_label.update(f"{_fmt(position)} / {_fmt(duration)}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, TrackListItem):
            self.player.play_index(item.track_index)

    def action_toggle_play(self) -> None:
        if not self.player.playlist.current_track:
            self.player.play_index(0)
        else:
            self.player.toggle_play_pause()

    def action_stop(self) -> None:
        self.player.stop()

    def action_next_track(self) -> None:
        self.player.next_track()

    def action_previous_track(self) -> None:
        self.player.previous_track()

    def action_seek_backward(self) -> None:
        self.player.seek(self.player.get_position() - 5)

    def action_seek_forward(self) -> None:
        self.player.seek(self.player.get_position() + 5)

    def action_volume_up(self) -> None:
        self.player.volume = self.player.volume + 0.05

    def action_volume_down(self) -> None:
        self.player.volume = self.player.volume - 0.05

    def action_mode_sequential(self) -> None:
        self.player.playlist.mode = PlaylistMode.NONE
        self._refresh_mode_bar()

    def action_mode_loop_one(self) -> None:
        self.player.playlist.mode = PlaylistMode.ONE
        self._refresh_mode_bar()

    def action_mode_loop_all(self) -> None:
        self.player.playlist.mode = PlaylistMode.ALL
        self._refresh_mode_bar()

    def action_toggle_shuffle(self) -> None:
        self.player.playlist.shuffle = not self.player.playlist.shuffle
        self._refresh_mode_bar()

    def action_open_settings(self) -> None:
        self.push_screen(SettingsScreen(self._cover_render_mode), self._on_settings_closed)

    def _on_settings_closed(self, mode) -> None:
        if mode is None:
            return  # cancelled - disk and in-memory mode both untouched
        self._cover_render_mode = mode
        config = self._config_adapter.load()
        config.cover_render_mode = mode
        self._config_adapter.save(config)
        self._render_cover(self.player.playlist.current_track)


def _fmt(seconds: float) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def run_tui(container: Container, music_folder: str = "./music") -> None:
    app = PyusicPlayerApp(container, Path(music_folder))
    app.run()
