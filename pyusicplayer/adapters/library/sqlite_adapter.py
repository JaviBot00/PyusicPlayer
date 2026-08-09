"""SQLite adapter for LibraryPort.

Implemented so far: lifecycle (initialize/close), Artist/Album/Song/Collection
CRUD, import_directory. get_stats is still a Protocol `...` stub, pending its
own test-first slice.

Schema note (deliberate deviation from the old AGENT.md draft): song-to-
collection membership is many-to-many via `collection_songs`, not a
`songs.collection_id` column. This matches what LibraryPort.add_to_collection/
remove_from_collection/get_collection_songs actually requires — a song must
be able to live in more than one collection (e.g. a playlist AND a smart
list) at once.

datetime fields (Song.last_modified / last_scanned) are stored as ISO 8601
strings — SQLite has no native datetime type.

import_directory requires a MetadataPort (constructor-injected) to extract
tags. Re-scans are idempotent: unchanged files (by filesystem mtime vs the
stored last_modified) are skipped, changed files are updated in place, and
only genuinely new files count toward the returned total. Files that fail to
parse (unsupported format, or a supported extension with unreadable/corrupt
content) are skipped with a logging.WARNING record naming the file, and the
scan continues — one bad file must not abort an import of hundreds.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from pyusicplayer.core.ports.library import Album, Artist, Collection, Song
from pyusicplayer.core.ports.metadata import MetadataPort

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS artists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_name TEXT,
    image_path TEXT
);

CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    year INTEGER,
    cover_path TEXT,
    disk_count INTEGER NOT NULL DEFAULT 1,
    UNIQUE (title, artist_id)
);

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    title TEXT,
    artist_id INTEGER REFERENCES artists(id),
    album_id INTEGER REFERENCES albums(id),
    track_number INTEGER,
    disc_number INTEGER,
    duration REAL,
    format TEXT,
    size INTEGER,
    last_modified TEXT,
    last_scanned TEXT
);

CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    is_smart INTEGER NOT NULL DEFAULT 0,
    query TEXT
);

CREATE TABLE IF NOT EXISTS collection_songs (
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    song_id INTEGER NOT NULL REFERENCES songs(id),
    PRIMARY KEY (collection_id, song_id)
);
"""


class SqliteLibraryAdapter:
    """SQLite implementation of LibraryPort (partial — see module docstring)."""

    def __init__(
        self, db_path: Union[str, Path], metadata_port: MetadataPort
    ) -> None:
        self._db_path = Path(db_path)
        self._metadata_port = metadata_port
        self._conn: Optional[sqlite3.Connection] = None

    # -- lifecycle ----------------------------------------------------

    def initialize(self) -> None:
        if self._conn is not None:
            self._conn.close()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- artists --------------------------------------------------------

    def get_artist(self, artist_id: int) -> Optional[Artist]:
        row = self._conn.execute(
            "SELECT id, name, sort_name, image_path FROM artists WHERE id = ?",
            (artist_id,),
        ).fetchone()
        return self._row_to_artist(row) if row else None

    def get_or_create_artist(self, name: str) -> Artist:
        row = self._conn.execute(
            "SELECT id, name, sort_name, image_path FROM artists WHERE name = ?",
            (name,),
        ).fetchone()
        if row:
            return self._row_to_artist(row)

        cursor = self._conn.execute(
            "INSERT INTO artists (name) VALUES (?)", (name,)
        )
        self._conn.commit()
        return Artist(id=cursor.lastrowid, name=name)

    def search_artists(self, query: str) -> List[Artist]:
        # COLLATE NOCASE only folds ASCII A-Z (SQLite has no built-in
        # Unicode-aware case folding without loading the ICU extension), so
        # accented letters that change case (Ä -> ä) would be missed by a
        # pure SQL LIKE ... COLLATE NOCASE. Filter in Python with casefold()
        # instead, which is Unicode-correct. Acceptable at this project's
        # scale (personal music library, not a streaming-service catalog).
        needle = query.casefold()
        rows = self._conn.execute(
            "SELECT id, name, sort_name, image_path FROM artists"
        ).fetchall()
        return [
            self._row_to_artist(row)
            for row in rows
            if needle in row["name"].casefold()
        ]

    @staticmethod
    def _row_to_artist(row: sqlite3.Row) -> Artist:
        return Artist(
            id=row["id"],
            name=row["name"],
            sort_name=row["sort_name"],
            image_path=row["image_path"],
        )

    # -- albums -----------------------------------------------------------

    _ALBUM_SELECT = (
        "SELECT albums.id, albums.title, albums.artist_id, "
        "artists.name AS artist_name, albums.year, albums.cover_path, "
        "albums.disk_count "
        "FROM albums LEFT JOIN artists ON albums.artist_id = artists.id"
    )

    def get_album(self, album_id: int) -> Optional[Album]:
        row = self._conn.execute(
            f"{self._ALBUM_SELECT} WHERE albums.id = ?", (album_id,)
        ).fetchone()
        return self._row_to_album(row) if row else None

    def get_or_create_album(
        self, title: str, artist_id: Optional[int] = None
    ) -> Album:
        # NULL never equals NULL in SQL, so "artist_id = ?" would silently
        # miss existing rows when artist_id is None - use IS for that branch.
        if artist_id is None:
            row = self._conn.execute(
                f"{self._ALBUM_SELECT} "
                "WHERE albums.title = ? AND albums.artist_id IS NULL",
                (title,),
            ).fetchone()
        else:
            row = self._conn.execute(
                f"{self._ALBUM_SELECT} "
                "WHERE albums.title = ? AND albums.artist_id = ?",
                (title, artist_id),
            ).fetchone()
        if row:
            return self._row_to_album(row)

        cursor = self._conn.execute(
            "INSERT INTO albums (title, artist_id) VALUES (?, ?)",
            (title, artist_id),
        )
        self._conn.commit()
        return self.get_album(cursor.lastrowid)

    def search_albums(self, query: str) -> List[Album]:
        needle = query.casefold()
        rows = self._conn.execute(self._ALBUM_SELECT).fetchall()
        return [
            self._row_to_album(row)
            for row in rows
            if needle in row["title"].casefold()
        ]

    @staticmethod
    def _row_to_album(row: sqlite3.Row) -> Album:
        return Album(
            id=row["id"],
            title=row["title"],
            artist_id=row["artist_id"],
            artist_name=row["artist_name"],
            year=row["year"],
            cover_path=row["cover_path"],
            disk_count=row["disk_count"],
        )

    # -- songs --------------------------------------------------------------

    _SONG_SELECT = (
        "SELECT songs.id, songs.file_path, songs.title, songs.artist_id, "
        "artists.name AS artist_name, songs.album_id, "
        "albums.title AS album_title, songs.track_number, songs.disc_number, "
        "songs.duration, songs.format, songs.size, songs.last_modified, "
        "songs.last_scanned "
        "FROM songs "
        "LEFT JOIN artists ON songs.artist_id = artists.id "
        "LEFT JOIN albums ON songs.album_id = albums.id"
    )

    def get_song(self, song_id: int) -> Optional[Song]:
        row = self._conn.execute(
            f"{self._SONG_SELECT} WHERE songs.id = ?", (song_id,)
        ).fetchone()
        return self._row_to_song(row) if row else None

    def add_song(self, song: Song) -> int:
        try:
            cursor = self._conn.execute(
                "INSERT INTO songs (file_path, title, artist_id, album_id, "
                "track_number, disc_number, duration, format, size, "
                "last_modified, last_scanned) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    song.file_path,
                    song.title,
                    song.artist_id,
                    song.album_id,
                    song.track_number,
                    song.disc_number,
                    song.duration,
                    song.format,
                    song.size,
                    self._to_iso(song.last_modified),
                    self._to_iso(song.last_scanned),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"song already exists: {song.file_path}") from exc
        self._conn.commit()
        return cursor.lastrowid

    def update_song(self, song: Song) -> bool:
        cursor = self._conn.execute(
            "UPDATE songs SET file_path = ?, title = ?, artist_id = ?, "
            "album_id = ?, track_number = ?, disc_number = ?, duration = ?, "
            "format = ?, size = ?, last_modified = ?, last_scanned = ? "
            "WHERE id = ?",
            (
                song.file_path,
                song.title,
                song.artist_id,
                song.album_id,
                song.track_number,
                song.disc_number,
                song.duration,
                song.format,
                song.size,
                self._to_iso(song.last_modified),
                self._to_iso(song.last_scanned),
                song.id,
            ),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_song(self, song_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def get_all_songs(self) -> List[Song]:
        rows = self._conn.execute(self._SONG_SELECT).fetchall()
        return [self._row_to_song(row) for row in rows]

    def search_songs(self, query: str) -> List[Song]:
        needle = query.casefold()
        rows = self._conn.execute(self._SONG_SELECT).fetchall()
        seen_ids = set()
        results = []
        for row in rows:
            haystacks = (row["title"], row["artist_name"], row["album_title"])
            if any(h and needle in h.casefold() for h in haystacks):
                if row["id"] not in seen_ids:
                    seen_ids.add(row["id"])
                    results.append(self._row_to_song(row))
        return results

    def get_songs_by_artist(self, artist_id: int) -> List[Song]:
        rows = self._conn.execute(
            f"{self._SONG_SELECT} WHERE songs.artist_id = ?", (artist_id,)
        ).fetchall()
        return [self._row_to_song(row) for row in rows]

    def get_songs_by_album(self, album_id: int) -> List[Song]:
        rows = self._conn.execute(
            f"{self._SONG_SELECT} WHERE songs.album_id = ?", (album_id,)
        ).fetchall()
        return [self._row_to_song(row) for row in rows]

    @staticmethod
    def _to_iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _from_iso(value: Optional[str]) -> Optional[datetime]:
        return datetime.fromisoformat(value) if value is not None else None

    @classmethod
    def _row_to_song(cls, row: sqlite3.Row) -> Song:
        return Song(
            id=row["id"],
            file_path=row["file_path"],
            title=row["title"],
            artist_id=row["artist_id"],
            artist_name=row["artist_name"],
            album_id=row["album_id"],
            album_title=row["album_title"],
            track_number=row["track_number"],
            disc_number=row["disc_number"],
            duration=row["duration"],
            format=row["format"],
            size=row["size"],
            last_modified=cls._from_iso(row["last_modified"]),
            last_scanned=cls._from_iso(row["last_scanned"]),
        )

    # -- collections ----------------------------------------------------

    def create_collection(self, name: str, is_smart: bool = False) -> Collection:
        cursor = self._conn.execute(
            "INSERT INTO collections (name, is_smart) VALUES (?, ?)",
            (name, int(is_smart)),
        )
        self._conn.commit()
        return Collection(id=cursor.lastrowid, name=name, is_smart=is_smart)

    def get_collection(self, collection_id: int) -> Optional[Collection]:
        row = self._conn.execute(
            "SELECT id, name, is_smart, query FROM collections WHERE id = ?",
            (collection_id,),
        ).fetchone()
        if not row:
            return None
        song_id_rows = self._conn.execute(
            "SELECT song_id FROM collection_songs WHERE collection_id = ? "
            "ORDER BY song_id",
            (collection_id,),
        ).fetchall()
        return Collection(
            id=row["id"],
            name=row["name"],
            is_smart=bool(row["is_smart"]),
            query=row["query"],
            song_ids=[r["song_id"] for r in song_id_rows],
        )

    def add_to_collection(self, collection_id: int, song_id: int) -> bool:
        try:
            self._conn.execute(
                "INSERT INTO collection_songs (collection_id, song_id) "
                "VALUES (?, ?)",
                (collection_id, song_id),
            )
        except sqlite3.IntegrityError:
            # Composite PRIMARY KEY (collection_id, song_id) violated - the
            # song is already in this collection. Protocol contract: False,
            # not an exception.
            return False
        self._conn.commit()
        return True

    def remove_from_collection(self, collection_id: int, song_id: int) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM collection_songs WHERE collection_id = ? AND song_id = ?",
            (collection_id, song_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_collection_songs(self, collection_id: int) -> List[Song]:
        rows = self._conn.execute(
            f"{self._SONG_SELECT} "
            "JOIN collection_songs ON collection_songs.song_id = songs.id "
            "WHERE collection_songs.collection_id = ?",
            (collection_id,),
        ).fetchall()
        return [self._row_to_song(row) for row in rows]

    # -- import_directory -------------------------------------------------

    def import_directory(self, dir_path: str, recursive: bool = True) -> int:
        root = Path(dir_path)
        pattern_iter = root.rglob("*") if recursive else root.glob("*")
        files = sorted(p for p in pattern_iter if p.is_file())

        imported_count = 0
        for file_path in files:
            path_str = str(file_path)
            if not self._metadata_port.supports_format(path_str):
                continue

            try:
                metadata = self._metadata_port.extract(path_str)
            except Exception:
                logger.warning(
                    "import_directory: skipping unreadable file %s", path_str,
                    exc_info=True,
                )
                continue

            disk_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            existing = self._get_song_by_path(path_str)

            if existing is not None:
                if existing.last_modified is not None and disk_mtime <= existing.last_modified:
                    continue  # unchanged - skip, not counted
                existing.last_modified = disk_mtime
                existing.last_scanned = datetime.now()
                self._apply_metadata(existing, metadata)
                self.update_song(existing)
                continue  # updated - not counted as "imported"

            artist_id = None
            if metadata.artist:
                artist_id = self.get_or_create_artist(metadata.artist).id

            album_id = None
            if metadata.album:
                album_id = self.get_or_create_album(
                    metadata.album, artist_id=artist_id
                ).id

            song = Song(
                file_path=path_str,
                title=metadata.title,
                artist_id=artist_id,
                album_id=album_id,
                track_number=metadata.track_number,
                disc_number=metadata.disc_number,
                duration=metadata.duration,
                format=file_path.suffix.lstrip(".").lower(),
                size=file_path.stat().st_size,
                last_modified=disk_mtime,
                last_scanned=datetime.now(),
            )
            self.add_song(song)
            imported_count += 1

        return imported_count

    def _get_song_by_path(self, file_path: str) -> Optional[Song]:
        row = self._conn.execute(
            f"{self._SONG_SELECT} WHERE songs.file_path = ?", (file_path,)
        ).fetchone()
        return self._row_to_song(row) if row else None

    @staticmethod
    def _apply_metadata(song: Song, metadata) -> None:
        song.title = metadata.title
        song.track_number = metadata.track_number
        song.disc_number = metadata.disc_number
        song.duration = metadata.duration

    # -- get_stats ----------------------------------------------------------

    def get_stats(self) -> dict:
        songs = self._conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        albums = self._conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0]
        artists = self._conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0]
        collections = self._conn.execute(
            "SELECT COUNT(*) FROM collections"
        ).fetchone()[0]
        # SUM() over an empty/all-NULL set returns SQL NULL, not 0 - coalesce
        # to 0.0 so the return type is always float, never None.
        total_duration = self._conn.execute(
            "SELECT COALESCE(SUM(duration), 0.0) FROM songs"
        ).fetchone()[0]
        return {
            "songs": songs,
            "albums": albums,
            "artists": artists,
            "collections": collections,
            "total_duration": total_duration,
        }
