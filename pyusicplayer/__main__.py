"""PyusicPlayer entry point.

Only --tui is implemented in this cycle. --gui/--server are reserved for
later phases and exit with a clear message instead of silently no-op-ing
or crashing on a missing import.
"""

from __future__ import annotations

import argparse
import sys

from .di.container import create_container


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pyusicplayer",
        description="PyusicPlayer - modular music player",
    )
    parser.add_argument("--tui", action="store_true", help="Run in TUI mode (default)")
    parser.add_argument("--gui", action="store_true", help="Run in GUI mode (not yet implemented)")
    parser.add_argument("--server", action="store_true", help="Run API server (not yet implemented)")
    parser.add_argument(
        "--music-dir",
        default="./music",
        help="Folder to scan for audio files (default: ./music)",
    )
    args = parser.parse_args()

    if args.gui:
        print("GUI mode is not implemented yet in this build.", file=sys.stderr)
        sys.exit(1)
    if args.server:
        print("Server mode is not implemented yet in this build.", file=sys.stderr)
        sys.exit(1)

    container = create_container()
    from .interfaces.tui import run_tui

    run_tui(container, music_folder=args.music_dir)


if __name__ == "__main__":
    main()
