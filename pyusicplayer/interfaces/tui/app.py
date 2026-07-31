"""Minimal Textual TUI: playlist + transport controls + progress bar.

Scope for this first implementation cycle (P0 only):
  play/pause/stop/next/prev, seek, volume, playlist from a folder scan.
Deliberately NOT implemented yet (agreed as out-of-scope for this cycle):
  lyrics/cover/visualizer alternate views, layout toggle, help modal,
  library DB, downloader, notifications, i18n, GUI, API server.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, ListItem, ListView, Label, ProgressBar, Static

from ...core.models import PlaylistMode
from ...core.ports import PlaybackState
from ...core.services import PlayerService
from ...di.container import Container

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".wma"}


def scan_music_folder(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    return sorted(
        str(p) for p in folder.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


class TrackListItem(ListItem):
    def __init__(self, index: int, label: str) -> None:
        super().__init__(Label(label))
        self.track_index = index


class PyusicPlayerApp(App):
    """Terminal music player."""

    CSS = """
    #now-playing {
        height: 3;
        content-align: center middle;
        text-style: bold;
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
        Binding("shift+l", "mode_loop_all", "Loop all"),
        Binding("r", "toggle_shuffle", "Shuffle"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, container: Container, music_folder: Path) -> None:
        super().__init__()
        self._music_folder = music_folder
        self.player: PlayerService = container.resolve(PlayerService)
        self._added = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Nothing loaded", id="now-playing")
        with Vertical(id="progress-row"):
            yield ProgressBar(total=100, show_eta=False, id="progress")
            yield Static("--:-- / --:--", id="time-label")
        yield ListView(id="playlist-view")
        yield Footer()

    def on_mount(self) -> None:
        self.player.initialize()
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
        self.set_interval(0.2, self._tick)

    def on_unmount(self) -> None:
        self.player.shutdown()

    def _on_track_change(self, track) -> None:
        self.query_one("#now-playing", Static).update(track.display_name)

    def _on_state_change(self, state: PlaybackState) -> None:
        pass  # progress bar / labels are refreshed by the periodic _tick instead

    def _tick(self) -> None:
        self.player.poll()
        duration = self.player.get_duration()
        position = self.player.get_position()
        progress = self.query_one("#progress", ProgressBar)
        if duration > 0:
            progress.update(total=100, progress=min(100, (position / duration) * 100))
        time_label = self.query_one("#time-label", Static)
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

    def action_mode_loop_one(self) -> None:
        self.player.playlist.mode = PlaylistMode.ONE

    def action_mode_loop_all(self) -> None:
        self.player.playlist.mode = PlaylistMode.ALL

    def action_toggle_shuffle(self) -> None:
        self.player.playlist.shuffle = not self.player.playlist.shuffle


def _fmt(seconds: float) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def run_tui(container: Container, music_folder: str = "./music") -> None:
    app = PyusicPlayerApp(container, Path(music_folder))
    app.run()
