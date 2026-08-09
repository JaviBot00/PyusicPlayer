"""Tests for SqliteLibraryAdapter.

Covers: lifecycle, Artist/Album/Song/Collection CRUD, and import_directory.

All tests use tmp_path — no real filesystem side effects on ./data/.
"""

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from pyusicplayer.adapters.library.sqlite_adapter import SqliteLibraryAdapter
from pyusicplayer.adapters.metadata.mutagen_adapter import MutagenMetadataAdapter
from pyusicplayer.core.ports.library import Album, Artist, Collection, Song
from pyusicplayer.core.ports.metadata import AudioMetadata


class _FakeMetadataPort:
    """Stand-in MetadataPort for tests that don't exercise import_directory
    and shouldn't need real audio fixtures / ffmpeg just to construct an
    adapter."""

    def extract(self, file_path: str) -> AudioMetadata:
        raise AssertionError("_FakeMetadataPort.extract should not be called by non-import tests")

    def get_cover(self, file_path: str):
        return None

    def supports_format(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in {".mp3", ".flac", ".ogg", ".m4a", ".wav"}


def make_adapter(tmp_path: Path, metadata_port=None) -> SqliteLibraryAdapter:
    adapter = SqliteLibraryAdapter(
        db_path=tmp_path / "library.db",
        metadata_port=metadata_port or _FakeMetadataPort(),
    )
    adapter.initialize()
    return adapter


# ---------------------------------------------------------------------------
# initialize() / close()
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_initialize_creates_db_file(self, tmp_path):
        db_path = tmp_path / "library.db"
        adapter = SqliteLibraryAdapter(db_path=db_path, metadata_port=_FakeMetadataPort())
        adapter.initialize()
        assert db_path.exists()
        adapter.close()

    def test_initialize_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "nested" / "dir" / "library.db"
        adapter = SqliteLibraryAdapter(db_path=db_path, metadata_port=_FakeMetadataPort())
        adapter.initialize()
        assert db_path.exists()
        adapter.close()

    def test_initialize_is_idempotent(self, tmp_path):
        """Calling initialize() twice must not raise or wipe existing data."""
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Radiohead")
        adapter.initialize()
        assert adapter.get_artist(artist.id) is not None
        adapter.close()

    def test_creates_expected_tables(self, tmp_path):
        db_path = tmp_path / "library.db"
        adapter = SqliteLibraryAdapter(db_path=db_path, metadata_port=_FakeMetadataPort())
        adapter.initialize()
        adapter.close()

        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        assert {"artists", "albums", "songs", "collections", "collection_songs"} <= tables

    def test_close_allows_reopening(self, tmp_path):
        db_path = tmp_path / "library.db"
        adapter = SqliteLibraryAdapter(db_path=db_path, metadata_port=_FakeMetadataPort())
        adapter.initialize()
        adapter.get_or_create_artist("Boards of Canada")
        adapter.close()

        reopened = SqliteLibraryAdapter(db_path=db_path, metadata_port=_FakeMetadataPort())
        reopened.initialize()
        assert len(reopened.search_artists("Boards")) == 1
        reopened.close()

    def test_initialize_twice_closes_previous_connection(self, tmp_path):
        """Calling initialize() again must not leak the old sqlite3.Connection.

        Regression: the first call's Connection object was being discarded by
        simple reassignment (self._conn = sqlite3.connect(...)) without
        closing it first.
        """
        adapter = make_adapter(tmp_path)
        old_conn = adapter._conn
        adapter.initialize()
        with pytest.raises(sqlite3.ProgrammingError):
            old_conn.execute("SELECT 1")
        adapter.close()


# ---------------------------------------------------------------------------
# get_or_create_artist()
# ---------------------------------------------------------------------------

class TestGetOrCreateArtist:
    def test_creates_new_artist(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Aphex Twin")
        assert artist.id is not None
        assert artist.name == "Aphex Twin"
        adapter.close()

    def test_returns_existing_artist_on_duplicate_name(self, tmp_path):
        adapter = make_adapter(tmp_path)
        first = adapter.get_or_create_artist("Aphex Twin")
        second = adapter.get_or_create_artist("Aphex Twin")
        assert first.id == second.id
        adapter.close()

    def test_name_matching_is_exact_not_case_insensitive(self, tmp_path):
        """Documented behavior: 'Aphex Twin' and 'aphex twin' are different
        artists. Case-folding is a search concern (search_artists), not an
        identity concern — merging on case would silently corrupt libraries
        with genuinely distinct artists that differ only by case convention.
        """
        adapter = make_adapter(tmp_path)
        lower = adapter.get_or_create_artist("aphex twin")
        upper = adapter.get_or_create_artist("Aphex Twin")
        assert lower.id != upper.id
        adapter.close()


# ---------------------------------------------------------------------------
# get_artist()
# ---------------------------------------------------------------------------

class TestGetArtist:
    def test_returns_none_for_missing_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.get_artist(999) is None
        adapter.close()

    def test_returns_artist_by_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        created = adapter.get_or_create_artist("Burial")
        fetched = adapter.get_artist(created.id)
        assert fetched is not None
        assert fetched.name == "Burial"
        assert fetched.id == created.id
        adapter.close()


# ---------------------------------------------------------------------------
# search_artists()
# ---------------------------------------------------------------------------

class TestSearchArtists:
    def test_empty_library_returns_empty_list(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.search_artists("anything") == []
        adapter.close()

    def test_finds_partial_case_insensitive_match(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_artist("Massive Attack")
        results = adapter.search_artists("massive")
        assert len(results) == 1
        assert results[0].name == "Massive Attack"
        adapter.close()

    def test_no_match_returns_empty_list(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_artist("Massive Attack")
        assert adapter.search_artists("nonexistent") == []
        adapter.close()

    def test_returns_dataclass_instances(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_artist("Tycho")
        results = adapter.search_artists("Tycho")
        assert all(isinstance(a, Artist) for a in results)
        adapter.close()

    def test_finds_case_insensitive_match_with_accented_chars(self, tmp_path):
        """COLLATE NOCASE only folds ASCII A-Z; it misses accented case pairs
        where the ACCENTED letter itself changes case (Ä U+00C4 -> ä U+00E4).
        Regression for ES/EN library content.

        Note: 'Mägo'/'mägo' would NOT catch this bug - only the plain 'M'/'m'
        differs there, which is ASCII and already handled. The query below
        instead differs in the accented letter's case.
        """
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_artist("Ängel")
        results = adapter.search_artists("ängel")
        assert len(results) == 1
        assert results[0].name == "Ängel"
        adapter.close()


# ---------------------------------------------------------------------------
# get_or_create_album()
# ---------------------------------------------------------------------------

class TestGetOrCreateAlbum:
    def test_creates_new_album_without_artist(self, tmp_path):
        adapter = make_adapter(tmp_path)
        album = adapter.get_or_create_album("Unknown Pleasures")
        assert album.id is not None
        assert album.title == "Unknown Pleasures"
        assert album.artist_id is None
        adapter.close()

    def test_creates_new_album_with_artist(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Joy Division")
        album = adapter.get_or_create_album("Unknown Pleasures", artist_id=artist.id)
        assert album.artist_id == artist.id
        assert album.artist_name == "Joy Division"
        adapter.close()

    def test_returns_existing_album_on_duplicate_title_and_artist(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Joy Division")
        first = adapter.get_or_create_album("Unknown Pleasures", artist_id=artist.id)
        second = adapter.get_or_create_album("Unknown Pleasures", artist_id=artist.id)
        assert first.id == second.id
        adapter.close()

    def test_same_title_different_artist_are_different_albums(self, tmp_path):
        """'Greatest Hits' by artist A must not collide with 'Greatest Hits'
        by artist B - identity is (title, artist_id), not title alone."""
        adapter = make_adapter(tmp_path)
        artist_a = adapter.get_or_create_artist("Queen")
        artist_b = adapter.get_or_create_artist("ABBA")
        album_a = adapter.get_or_create_album("Greatest Hits", artist_id=artist_a.id)
        album_b = adapter.get_or_create_album("Greatest Hits", artist_id=artist_b.id)
        assert album_a.id != album_b.id
        adapter.close()

    def test_same_title_no_artist_vs_with_artist_are_different_albums(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Queen")
        no_artist = adapter.get_or_create_album("Greatest Hits")
        with_artist = adapter.get_or_create_album("Greatest Hits", artist_id=artist.id)
        assert no_artist.id != with_artist.id
        adapter.close()

    def test_default_disk_count_is_one(self, tmp_path):
        adapter = make_adapter(tmp_path)
        album = adapter.get_or_create_album("OK Computer")
        assert album.disk_count == 1
        adapter.close()


# ---------------------------------------------------------------------------
# get_album()
# ---------------------------------------------------------------------------

class TestGetAlbum:
    def test_returns_none_for_missing_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.get_album(999) is None
        adapter.close()

    def test_returns_album_by_id_with_artist_name_populated(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Radiohead")
        created = adapter.get_or_create_album("OK Computer", artist_id=artist.id)
        fetched = adapter.get_album(created.id)
        assert fetched is not None
        assert fetched.title == "OK Computer"
        assert fetched.artist_id == artist.id
        assert fetched.artist_name == "Radiohead"
        adapter.close()

    def test_returns_album_by_id_without_artist(self, tmp_path):
        adapter = make_adapter(tmp_path)
        created = adapter.get_or_create_album("Compilation")
        fetched = adapter.get_album(created.id)
        assert fetched is not None
        assert fetched.artist_id is None
        assert fetched.artist_name is None
        adapter.close()


# ---------------------------------------------------------------------------
# search_albums()
# ---------------------------------------------------------------------------

class TestSchemaConstraints:
    """DB-level defense-in-depth. get_or_create_* already prevent duplicates
    at the application layer, but nothing stopped a future code path (e.g.
    import_directory) from inserting duplicates directly - these constraints
    close that gap at the schema level.
    """

    def test_duplicate_artist_name_violates_unique_constraint(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter._conn.execute("INSERT INTO artists (name) VALUES ('Muse')")
        adapter._conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            adapter._conn.execute("INSERT INTO artists (name) VALUES ('Muse')")
        adapter.close()

    def test_duplicate_album_title_and_artist_violates_unique_constraint(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Muse")
        adapter._conn.execute(
            "INSERT INTO albums (title, artist_id) VALUES ('Absolution', ?)",
            (artist.id,),
        )
        adapter._conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            adapter._conn.execute(
                "INSERT INTO albums (title, artist_id) VALUES ('Absolution', ?)",
                (artist.id,),
            )
        adapter.close()

    def test_duplicate_album_title_with_null_artist_is_not_caught_by_db(self, tmp_path):
        """Documented SQLite behavior: NULL != NULL, so a composite UNIQUE
        constraint does not stop two rows with the same title and a NULL
        artist_id. Deduplication for that case is application-level only,
        inside get_or_create_album.
        """
        adapter = make_adapter(tmp_path)
        adapter._conn.execute("INSERT INTO albums (title, artist_id) VALUES ('Compilation', NULL)")
        adapter._conn.execute("INSERT INTO albums (title, artist_id) VALUES ('Compilation', NULL)")
        adapter._conn.commit()
        rows = adapter._conn.execute("SELECT COUNT(*) FROM albums WHERE title = 'Compilation'").fetchone()
        assert rows[0] == 2
        adapter.close()


class TestSearchAlbums:
    def test_empty_library_returns_empty_list(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.search_albums("anything") == []
        adapter.close()

    def test_finds_partial_case_insensitive_match(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_album("The Downward Spiral")
        results = adapter.search_albums("downward")
        assert len(results) == 1
        assert results[0].title == "The Downward Spiral"
        adapter.close()

    def test_finds_case_insensitive_match_with_accented_chars(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_album("Éxtasis")
        results = adapter.search_albums("éxtasis")
        assert len(results) == 1
        adapter.close()

    def test_no_match_returns_empty_list(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_album("The Downward Spiral")
        assert adapter.search_albums("nonexistent") == []
        adapter.close()

    def test_returns_dataclass_instances(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_album("Kid A")
        results = adapter.search_albums("Kid A")
        assert all(isinstance(a, Album) for a in results)
        adapter.close()


# ---------------------------------------------------------------------------
# add_song() / get_song()
# ---------------------------------------------------------------------------

class TestAddAndGetSong:
    def test_add_song_returns_new_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        assert isinstance(song_id, int)
        adapter.close()

    def test_get_song_returns_none_for_missing_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.get_song(999) is None
        adapter.close()

    def test_get_song_returns_all_scalar_fields(self, tmp_path):
        adapter = make_adapter(tmp_path)
        song_id = adapter.add_song(
            Song(
                file_path="/music/a.mp3",
                title="Everything In Its Right Place",
                track_number=1,
                disc_number=1,
                duration=249.5,
                format="mp3",
                size=6_000_000,
            )
        )
        song = adapter.get_song(song_id)
        assert song.file_path == "/music/a.mp3"
        assert song.title == "Everything In Its Right Place"
        assert song.track_number == 1
        assert song.disc_number == 1
        assert song.duration == 249.5
        assert song.format == "mp3"
        assert song.size == 6_000_000
        adapter.close()

    def test_get_song_populates_artist_and_album_names_via_join(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Radiohead")
        album = adapter.get_or_create_album("Kid A", artist_id=artist.id)
        song_id = adapter.add_song(
            Song(
                file_path="/music/a.mp3",
                title="Idioteque",
                artist_id=artist.id,
                album_id=album.id,
            )
        )
        song = adapter.get_song(song_id)
        assert song.artist_name == "Radiohead"
        assert song.album_title == "Kid A"
        adapter.close()

    def test_get_song_without_artist_or_album_has_none_names(self, tmp_path):
        adapter = make_adapter(tmp_path)
        song_id = adapter.add_song(Song(file_path="/music/orphan.mp3", title="Orphan"))
        song = adapter.get_song(song_id)
        assert song.artist_id is None
        assert song.artist_name is None
        assert song.album_id is None
        assert song.album_title is None
        adapter.close()

    def test_add_song_duplicate_file_path_raises_value_error(self, tmp_path):
        """file_path is UNIQUE at the schema level. add_song is insert-only
        (update_song is the separate, explicit path for changes) - on a
        duplicate path it must fail loudly with a ValueError, not leak a raw
        sqlite3.IntegrityError or silently upsert.
        """
        adapter = make_adapter(tmp_path)
        adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        with pytest.raises(ValueError, match="/music/a.mp3"):
            adapter.add_song(Song(file_path="/music/a.mp3", title="A duplicate"))
        adapter.close()

    def test_add_song_persists_datetime_fields_roundtrip(self, tmp_path):
        adapter = make_adapter(tmp_path)
        modified = datetime(2024, 3, 15, 10, 30, 0)
        scanned = datetime(2024, 3, 16, 9, 0, 0)
        song_id = adapter.add_song(
            Song(
                file_path="/music/a.mp3",
                title="A",
                last_modified=modified,
                last_scanned=scanned,
            )
        )
        song = adapter.get_song(song_id)
        assert song.last_modified == modified
        assert song.last_scanned == scanned
        adapter.close()

    def test_add_song_with_null_datetime_fields_returns_none(self, tmp_path):
        adapter = make_adapter(tmp_path)
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        song = adapter.get_song(song_id)
        assert song.last_modified is None
        assert song.last_scanned is None
        adapter.close()


# ---------------------------------------------------------------------------
# update_song()
# ---------------------------------------------------------------------------

class TestUpdateSong:
    def test_updates_existing_song_and_returns_true(self, tmp_path):
        adapter = make_adapter(tmp_path)
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="Old Title"))
        song = adapter.get_song(song_id)
        song.title = "New Title"
        result = adapter.update_song(song)
        assert result is True
        assert adapter.get_song(song_id).title == "New Title"
        adapter.close()

    def test_returns_false_for_missing_song(self, tmp_path):
        adapter = make_adapter(tmp_path)
        ghost = Song(id=999, file_path="/music/ghost.mp3", title="Ghost")
        assert adapter.update_song(ghost) is False
        adapter.close()


# ---------------------------------------------------------------------------
# delete_song()
# ---------------------------------------------------------------------------

class TestDeleteSong:
    def test_deletes_existing_song_and_returns_true(self, tmp_path):
        adapter = make_adapter(tmp_path)
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        assert adapter.delete_song(song_id) is True
        assert adapter.get_song(song_id) is None
        adapter.close()

    def test_returns_false_for_missing_song(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.delete_song(999) is False
        adapter.close()


# ---------------------------------------------------------------------------
# get_all_songs()
# ---------------------------------------------------------------------------

class TestGetAllSongs:
    def test_empty_library_returns_empty_list(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.get_all_songs() == []
        adapter.close()

    def test_returns_all_added_songs(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        adapter.add_song(Song(file_path="/music/b.mp3", title="B"))
        songs = adapter.get_all_songs()
        assert len(songs) == 2
        assert {s.title for s in songs} == {"A", "B"}
        adapter.close()


# ---------------------------------------------------------------------------
# search_songs()
# ---------------------------------------------------------------------------

class TestSearchSongs:
    def test_matches_by_title(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.add_song(Song(file_path="/music/a.mp3", title="Paranoid Android"))
        results = adapter.search_songs("paranoid")
        assert len(results) == 1
        adapter.close()

    def test_matches_by_artist_name(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Radiohead")
        adapter.add_song(Song(file_path="/music/a.mp3", title="X", artist_id=artist.id))
        results = adapter.search_songs("radiohead")
        assert len(results) == 1
        adapter.close()

    def test_matches_by_album_title(self, tmp_path):
        adapter = make_adapter(tmp_path)
        album = adapter.get_or_create_album("Kid A")
        adapter.add_song(Song(file_path="/music/a.mp3", title="X", album_id=album.id))
        results = adapter.search_songs("kid a")
        assert len(results) == 1
        adapter.close()

    def test_no_match_returns_empty_list(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.add_song(Song(file_path="/music/a.mp3", title="X"))
        assert adapter.search_songs("nonexistent") == []
        adapter.close()

    def test_does_not_duplicate_song_matching_multiple_fields(self, tmp_path):
        """A song titled 'Kid A' inside an album also titled 'Kid A' must
        appear once in results, not twice from a naive OR-joined query."""
        adapter = make_adapter(tmp_path)
        album = adapter.get_or_create_album("Kid A")
        adapter.add_song(Song(file_path="/music/a.mp3", title="Kid A", album_id=album.id))
        results = adapter.search_songs("kid a")
        assert len(results) == 1
        adapter.close()


# ---------------------------------------------------------------------------
# get_songs_by_artist() / get_songs_by_album()
# ---------------------------------------------------------------------------

class TestGetSongsByArtistAndAlbum:
    def test_get_songs_by_artist_returns_only_that_artists_songs(self, tmp_path):
        adapter = make_adapter(tmp_path)
        radiohead = adapter.get_or_create_artist("Radiohead")
        muse = adapter.get_or_create_artist("Muse")
        adapter.add_song(Song(file_path="/music/a.mp3", title="A", artist_id=radiohead.id))
        adapter.add_song(Song(file_path="/music/b.mp3", title="B", artist_id=muse.id))
        songs = adapter.get_songs_by_artist(radiohead.id)
        assert len(songs) == 1
        assert songs[0].title == "A"
        adapter.close()

    def test_get_songs_by_artist_empty_when_none_match(self, tmp_path):
        adapter = make_adapter(tmp_path)
        artist = adapter.get_or_create_artist("Radiohead")
        assert adapter.get_songs_by_artist(artist.id) == []
        adapter.close()

    def test_get_songs_by_album_returns_only_that_albums_songs(self, tmp_path):
        adapter = make_adapter(tmp_path)
        kid_a = adapter.get_or_create_album("Kid A")
        ok_computer = adapter.get_or_create_album("OK Computer")
        adapter.add_song(Song(file_path="/music/a.mp3", title="A", album_id=kid_a.id))
        adapter.add_song(Song(file_path="/music/b.mp3", title="B", album_id=ok_computer.id))
        songs = adapter.get_songs_by_album(kid_a.id)
        assert len(songs) == 1
        assert songs[0].title == "A"
        adapter.close()

    def test_get_songs_by_album_empty_when_none_match(self, tmp_path):
        adapter = make_adapter(tmp_path)
        album = adapter.get_or_create_album("Kid A")
        assert adapter.get_songs_by_album(album.id) == []
        adapter.close()


# ---------------------------------------------------------------------------
# create_collection() / get_collection()
# ---------------------------------------------------------------------------

class TestCreateAndGetCollection:
    def test_create_collection_returns_collection_with_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        assert collection.id is not None
        assert collection.name == "Favorites"
        adapter.close()

    def test_create_collection_defaults_to_not_smart(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        assert collection.is_smart is False
        adapter.close()

    def test_create_collection_defaults_to_empty_song_ids(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        assert collection.song_ids == []
        adapter.close()

    def test_create_smart_collection(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Recently Added", is_smart=True)
        assert collection.is_smart is True
        adapter.close()

    def test_get_collection_returns_none_for_missing_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        assert adapter.get_collection(999) is None
        adapter.close()

    def test_get_collection_returns_by_id(self, tmp_path):
        adapter = make_adapter(tmp_path)
        created = adapter.create_collection("Favorites")
        fetched = adapter.get_collection(created.id)
        assert fetched is not None
        assert fetched.name == "Favorites"
        adapter.close()

    def test_get_collection_populates_song_ids(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        adapter.add_to_collection(collection.id, song_id)
        fetched = adapter.get_collection(collection.id)
        assert fetched.song_ids == [song_id]
        adapter.close()


# ---------------------------------------------------------------------------
# add_to_collection() / remove_from_collection()
# ---------------------------------------------------------------------------

class TestCollectionMembership:
    def test_add_to_collection_returns_true_on_success(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        assert adapter.add_to_collection(collection.id, song_id) is True
        adapter.close()

    def test_add_to_collection_returns_false_if_already_present(self, tmp_path):
        """collection_songs has a composite PRIMARY KEY (collection_id,
        song_id); a duplicate INSERT raises IntegrityError, which this
        method must catch and translate to False per the protocol's
        documented contract - not propagate as an exception.
        """
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        adapter.add_to_collection(collection.id, song_id)
        assert adapter.add_to_collection(collection.id, song_id) is False
        adapter.close()

    def test_remove_from_collection_returns_true_on_success(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        adapter.add_to_collection(collection.id, song_id)
        assert adapter.remove_from_collection(collection.id, song_id) is True
        adapter.close()

    def test_remove_from_collection_returns_false_if_not_present(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        assert adapter.remove_from_collection(collection.id, song_id) is False
        adapter.close()

    def test_remove_from_collection_updates_get_collection_song_ids(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        adapter.add_to_collection(collection.id, song_id)
        adapter.remove_from_collection(collection.id, song_id)
        assert adapter.get_collection(collection.id).song_ids == []
        adapter.close()


# ---------------------------------------------------------------------------
# get_collection_songs()
# ---------------------------------------------------------------------------

class TestGetCollectionSongs:
    def test_returns_empty_list_for_empty_collection(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        assert adapter.get_collection_songs(collection.id) == []
        adapter.close()

    def test_returns_full_song_objects_not_just_ids(self, tmp_path):
        adapter = make_adapter(tmp_path)
        collection = adapter.create_collection("Favorites")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A Song"))
        adapter.add_to_collection(collection.id, song_id)
        songs = adapter.get_collection_songs(collection.id)
        assert len(songs) == 1
        assert isinstance(songs[0], Song)
        assert songs[0].title == "A Song"
        adapter.close()

    def test_excludes_songs_not_in_this_collection(self, tmp_path):
        adapter = make_adapter(tmp_path)
        favorites = adapter.create_collection("Favorites")
        workout = adapter.create_collection("Workout")
        song_a = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        song_b = adapter.add_song(Song(file_path="/music/b.mp3", title="B"))
        adapter.add_to_collection(favorites.id, song_a)
        adapter.add_to_collection(workout.id, song_b)
        songs = adapter.get_collection_songs(favorites.id)
        assert len(songs) == 1
        assert songs[0].title == "A"
        adapter.close()

    def test_same_song_can_belong_to_multiple_collections(self, tmp_path):
        """Confirms the many-to-many design decision from the schema review:
        a song must be addable to more than one collection at once."""
        adapter = make_adapter(tmp_path)
        favorites = adapter.create_collection("Favorites")
        workout = adapter.create_collection("Workout")
        song_id = adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        assert adapter.add_to_collection(favorites.id, song_id) is True
        assert adapter.add_to_collection(workout.id, song_id) is True
        assert len(adapter.get_collection_songs(favorites.id)) == 1
        assert len(adapter.get_collection_songs(workout.id)) == 1
        adapter.close()


# ---------------------------------------------------------------------------
# import_directory()
#
# Uses the REAL MutagenMetadataAdapter against synthetic audio_fixtures
# (ffmpeg-generated, session-scoped, see conftest.py). Skipped automatically
# if ffmpeg is unavailable.
# ---------------------------------------------------------------------------

def make_import_adapter(tmp_path: Path) -> SqliteLibraryAdapter:
    return make_adapter(tmp_path, metadata_port=MutagenMetadataAdapter())


class TestImportDirectory:
    def test_imports_all_supported_files_in_flat_directory(self, tmp_path, audio_fixtures):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        shutil.copy(audio_fixtures["mp3"], music_dir / "a.mp3")
        shutil.copy(audio_fixtures["ogg"], music_dir / "b.ogg")
        shutil.copy(audio_fixtures["flac"], music_dir / "c.flac")

        adapter = make_import_adapter(tmp_path)
        count = adapter.import_directory(str(music_dir))
        assert count == 3
        assert len(adapter.get_all_songs()) == 3
        adapter.close()

    def test_skips_unsupported_files(self, tmp_path, audio_fixtures):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        shutil.copy(audio_fixtures["mp3"], music_dir / "a.mp3")
        (music_dir / "readme.txt").write_text("not audio")

        adapter = make_import_adapter(tmp_path)
        count = adapter.import_directory(str(music_dir))
        assert count == 1
        songs = adapter.get_all_songs()
        assert len(songs) == 1
        assert songs[0].file_path.endswith("a.mp3")
        adapter.close()

    def test_recursive_true_scans_subdirectories(self, tmp_path, audio_fixtures):
        music_dir = tmp_path / "music"
        subdir = music_dir / "sub"
        subdir.mkdir(parents=True)
        shutil.copy(audio_fixtures["mp3"], music_dir / "top.mp3")
        shutil.copy(audio_fixtures["ogg"], subdir / "nested.ogg")

        adapter = make_import_adapter(tmp_path)
        count = adapter.import_directory(str(music_dir), recursive=True)
        assert count == 2
        adapter.close()

    def test_recursive_false_ignores_subdirectories(self, tmp_path, audio_fixtures):
        music_dir = tmp_path / "music"
        subdir = music_dir / "sub"
        subdir.mkdir(parents=True)
        shutil.copy(audio_fixtures["mp3"], music_dir / "top.mp3")
        shutil.copy(audio_fixtures["ogg"], subdir / "nested.ogg")

        adapter = make_import_adapter(tmp_path)
        count = adapter.import_directory(str(music_dir), recursive=False)
        assert count == 1
        songs = adapter.get_all_songs()
        assert songs[0].file_path.endswith("top.mp3")
        adapter.close()

    def test_creates_artist_and_album_from_metadata(self, tmp_path, audio_fixtures):
        """The flac fixture is tagged with title/artist/album/track by
        conftest.py's ffmpeg invocation - use it to confirm import_directory
        actually resolves artist/album via get_or_create_*, not just stores
        raw tag strings on the song row."""
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        shutil.copy(audio_fixtures["flac"], music_dir / "c.flac")

        adapter = make_import_adapter(tmp_path)
        adapter.import_directory(str(music_dir))
        songs = adapter.get_all_songs()
        assert songs[0].title == "Test Title"
        assert songs[0].artist_name == "Test Artist"
        assert songs[0].album_title == "Test Album"
        assert len(adapter.search_artists("Test Artist")) == 1
        assert len(adapter.search_albums("Test Album")) == 1
        adapter.close()

    def test_reimport_unchanged_file_is_skipped_and_not_recounted(self, tmp_path, audio_fixtures):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        shutil.copy(audio_fixtures["mp3"], music_dir / "a.mp3")

        adapter = make_import_adapter(tmp_path)
        first_count = adapter.import_directory(str(music_dir))
        second_count = adapter.import_directory(str(music_dir))
        assert first_count == 1
        assert second_count == 0
        assert len(adapter.get_all_songs()) == 1
        adapter.close()

    def test_reimport_changed_file_updates_without_recounting_or_duplicating(self, tmp_path, audio_fixtures):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        target = music_dir / "a.mp3"
        shutil.copy(audio_fixtures["mp3"], target)

        adapter = make_import_adapter(tmp_path)
        adapter.import_directory(str(music_dir))
        original_song = adapter.get_all_songs()[0]

        # Simulate the file changing on disk later.
        future = os.path.getmtime(target) + 3600
        os.utime(target, (future, future))

        second_count = adapter.import_directory(str(music_dir))
        songs = adapter.get_all_songs()
        assert second_count == 0
        assert len(songs) == 1
        assert songs[0].id == original_song.id
        assert songs[0].last_modified > original_song.last_modified
        adapter.close()

    def test_unreadable_file_is_skipped_and_scan_continues(self, tmp_path, audio_fixtures, caplog):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        shutil.copy(audio_fixtures["mp3"], music_dir / "good.mp3")
        (music_dir / "corrupt.mp3").write_bytes(b"not a real mp3 file, just garbage bytes")

        adapter = make_import_adapter(tmp_path)
        with caplog.at_level(logging.WARNING):
            count = adapter.import_directory(str(music_dir))

        assert count == 1
        songs = adapter.get_all_songs()
        assert len(songs) == 1
        assert songs[0].file_path.endswith("good.mp3")
        adapter.close()

    def test_logs_warning_with_path_for_skipped_file(self, tmp_path, audio_fixtures, caplog):
        """The failure must be identifiable after the fact - the log record
        has to name which file failed, not just that something failed."""
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        bad_file = music_dir / "corrupt.mp3"
        bad_file.write_bytes(b"garbage")

        adapter = make_import_adapter(tmp_path)
        with caplog.at_level(logging.WARNING):
            adapter.import_directory(str(music_dir))

        assert any(str(bad_file) in record.message for record in caplog.records)
        adapter.close()

    def test_empty_directory_returns_zero(self, tmp_path):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        adapter = make_import_adapter(tmp_path)
        assert adapter.import_directory(str(music_dir)) == 0
        adapter.close()


# ---------------------------------------------------------------------------
# get_stats()
#
# Fixed key set (confirmed, not to be extended without explicit request):
# songs, albums, artists, collections, total_duration.
# ---------------------------------------------------------------------------

class TestGetStats:
    def test_empty_library_returns_zeroed_stats(self, tmp_path):
        adapter = make_adapter(tmp_path)
        stats = adapter.get_stats()
        assert stats == {
            "songs": 0,
            "albums": 0,
            "artists": 0,
            "collections": 0,
            "total_duration": 0.0,
        }
        adapter.close()

    def test_counts_songs(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.add_song(Song(file_path="/music/a.mp3", title="A"))
        adapter.add_song(Song(file_path="/music/b.mp3", title="B"))
        assert adapter.get_stats()["songs"] == 2
        adapter.close()

    def test_counts_albums(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_album("Kid A")
        adapter.get_or_create_album("OK Computer")
        assert adapter.get_stats()["albums"] == 2
        adapter.close()

    def test_counts_artists(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.get_or_create_artist("Radiohead")
        assert adapter.get_stats()["artists"] == 1
        adapter.close()

    def test_counts_collections(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.create_collection("Favorites")
        adapter.create_collection("Workout")
        assert adapter.get_stats()["collections"] == 2
        adapter.close()

    def test_sums_song_durations(self, tmp_path):
        adapter = make_adapter(tmp_path)
        adapter.add_song(Song(file_path="/music/a.mp3", title="A", duration=180.5))
        adapter.add_song(Song(file_path="/music/b.mp3", title="B", duration=200.0))
        assert adapter.get_stats()["total_duration"] == 380.5
        adapter.close()

    def test_songs_with_null_duration_do_not_break_the_sum(self, tmp_path):
        """SQL SUM() silently ignores NULLs, which is correct here - a song
        with unknown duration shouldn't need a 0.0 placeholder just to be
        summable. Confirms that behavior explicitly rather than relying on
        it by accident."""
        adapter = make_adapter(tmp_path)
        adapter.add_song(Song(file_path="/music/a.mp3", title="A", duration=180.5))
        adapter.add_song(Song(file_path="/music/b.mp3", title="B"))  # no duration
        assert adapter.get_stats()["total_duration"] == 180.5
        adapter.close()
