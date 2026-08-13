"""SettingsScreen - modal for changing AppConfig.cover_render_mode at
runtime. Dismisses with the chosen mode string, or None if cancelled.

Persistence and re-rendering the current track's cover happen in the
caller (PyusicPlayerApp._on_settings_closed), not here - this screen only
picks a value, it doesn't know about ConfigPort or the cover widget.
"""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from ....core.ports.cover_renderer import CoverRenderMode

# Order matters for keyboard-driven tests (index = ListView position).
MODE_OPTIONS: list[tuple[str, str]] = [
    (CoverRenderMode.TRUECOLOR, "Truecolor (half-block, needs 24-bit color terminal)"),
    (CoverRenderMode.ASCII, "ASCII (monochrome, works everywhere)"),
    (CoverRenderMode.PLACEHOLDER, "Placeholder (text only, no image decode)"),
]


class _ModeItem(ListItem):
    def __init__(self, mode: str, label: str) -> None:
        super().__init__(Label(label))
        self.mode = mode


class SettingsScreen(ModalScreen[Optional[str]]):
    CSS = """
    SettingsScreen {
        align: center middle;
    }
    #settings-box {
        width: 60;
        height: auto;
        border: round $accent;
        padding: 1 2;
        background: $panel;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, current_mode: str) -> None:
        super().__init__()
        self._current_mode = current_mode

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-box"):
            yield Static("Cover art render mode (Enter to select, Esc to cancel)")
            yield ListView(*[_ModeItem(mode, label) for mode, label in MODE_OPTIONS])

    def on_mount(self) -> None:
        list_view = self.query_one(ListView)
        for index, (mode, _label) in enumerate(MODE_OPTIONS):
            if mode == self._current_mode:
                list_view.index = index
                break
        list_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, _ModeItem):
            self.dismiss(item.mode)

    def action_cancel(self) -> None:
        self.dismiss(None)
