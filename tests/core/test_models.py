"""Tests for core.models: Track and Playlist. Pure logic, no I/O required."""

from __future__ import annotations

from pyusicplayer.core.models import Playlist, PlaylistMode, Track


class TestTrack:
    def test_title_defaults_to_filename_stem(self):
        track = Track(file_path="/music/some_song.mp3")
        assert track.title == "some_song"

    def test_explicit_title_is_kept(self):
        track = Track(file_path="/music/some_song.mp3", title="Real Title")
        assert track.title == "Real Title"

    def test_display_name_combines_artist_and_title(self):
        track = Track(file_path="/x.mp3", title="Song", artist="Artist")
        assert track.display_name == "Artist - Song"

    def test_display_name_falls_back_to_stem_without_metadata(self):
        track = Track(file_path="/music/no_tags.mp3")
        assert track.display_name == "no_tags"

    def test_format_duration_unknown(self):
        track = Track(file_path="/x.mp3")
        assert track.format_duration == "--:--"

    def test_format_duration_formats_minutes_seconds(self):
        track = Track(file_path="/x.mp3", duration=125.0)
        assert track.format_duration == "02:05"


class TestPlaylistSequential:
    def _playlist(self, n=3) -> Playlist:
        p = Playlist()
        for i in range(n):
            p.add_track(Track(file_path=f"/t{i}.mp3"))
        return p

    def test_next_index_sequential_advances(self):
        p = self._playlist(3)
        p.current_index = 0
        assert p.next_index() == 1

    def test_next_index_sequential_end_of_playlist_stops(self):
        p = self._playlist(3)
        p.current_index = 2
        assert p.next_index() == -1  # PlaylistMode.NONE: no wraparound

    def test_next_index_loop_all_wraps_to_zero(self):
        p = self._playlist(3)
        p.mode = PlaylistMode.ALL
        p.current_index = 2
        assert p.next_index() == 0

    def test_next_index_loop_one_repeats_current(self):
        p = self._playlist(3)
        p.mode = PlaylistMode.ONE
        p.current_index = 1
        assert p.next_index() == 1

    def test_previous_index_sequential_clamps_to_zero(self):
        p = self._playlist(3)
        p.current_index = 0
        assert p.previous_index() == 0

    def test_previous_index_loop_all_wraps_to_last(self):
        p = self._playlist(3)
        p.mode = PlaylistMode.ALL
        p.current_index = 0
        assert p.previous_index() == 2

    def test_advance_commits_the_move(self):
        p = self._playlist(3)
        p.current_index = 0
        idx = p.advance()
        assert idx == 1
        assert p.current_index == 1

    def test_next_index_empty_playlist_returns_minus_one(self):
        p = Playlist()
        assert p.next_index() == -1


class TestPlaylistShuffle:
    def _playlist(self, n=5) -> Playlist:
        p = Playlist()
        for i in range(n):
            p.add_track(Track(file_path=f"/t{i}.mp3"))
        p.shuffle = True
        return p

    def test_shuffle_visits_every_track_exactly_once_before_repeating(self):
        """Fisher-Yates bag: over one full cycle (n-1 advances from a fixed
        start), every other index must appear exactly once, no repeats."""
        p = self._playlist(5)
        p.current_index = 0
        seen = []
        for _ in range(4):  # 4 remaining tracks besides the starting one
            idx = p.advance()
            seen.append(idx)
        assert sorted(seen) == [1, 2, 3, 4]
        assert len(set(seen)) == 4  # no repeats within the cycle

    def test_shuffle_refills_bag_after_exhaustion(self):
        """Refill-and-continue only happens in loop-all mode - shuffle alone
        doesn't imply looping (see TestPlaylistShuffleRespectsMode)."""
        p = self._playlist(3)
        p.mode = PlaylistMode.ALL
        p.current_index = 0
        first_cycle = {p.advance() for _ in range(2)}
        assert first_cycle == {1, 2}
        # Bag exhausted; next advance() must refill and keep working.
        next_idx = p.advance()
        assert 0 <= next_idx < 3

    def test_shuffle_single_track_playlist_does_not_crash(self):
        p = Playlist()
        p.add_track(Track(file_path="/only.mp3"))
        p.shuffle = True
        p.current_index = 0
        assert p.next_index() == 0


class TestPlaylistShuffleRespectsMode:
    """Bug found in production: shuffle was treated as implying infinite
    looping regardless of `mode`. shuffle only decides ORDER; `mode` alone
    decides whether the playlist stops, loops one, or loops all at the end.
    """

    def _playlist(self, n=2) -> Playlist:
        p = Playlist()
        for i in range(n):
            p.add_track(Track(file_path=f"/t{i}.mp3"))
        p.shuffle = True
        return p

    def test_sequential_mode_with_shuffle_stops_after_visiting_all_tracks(self):
        """2 tracks, shuffle on, mode=NONE (sequential/no-repeat): after
        the bag is exhausted (1 advance for a 2-track playlist), next_index()
        must return -1, NOT loop back to the other track."""
        p = self._playlist(2)
        p.mode = PlaylistMode.NONE
        p.current_index = 0

        first = p.advance()
        assert first == 1  # the only other track, correctly played once

        second = p.next_index()
        assert second == -1  # must stop here - this was the bug

    def test_loop_all_mode_with_shuffle_reshuffles_and_continues(self):
        """Same setup but mode=ALL: after exhausting the bag, it SHOULD
        refill and keep going (this part already worked before the fix)."""
        p = self._playlist(2)
        p.mode = PlaylistMode.ALL
        p.current_index = 0

        first = p.advance()
        assert first == 1

        second = p.next_index()
        assert second in (0, 1)  # refilled bag, playback continues

    def test_loop_one_mode_with_shuffle_repeats_current_track(self):
        """mode=ONE takes priority over shuffle entirely - always the
        current track, regardless of shuffle being on."""
        p = self._playlist(3)
        p.mode = PlaylistMode.ONE
        p.current_index = 1
        assert p.next_index() == 1


class TestPlaylistMutation:
    def test_remove_track_adjusts_current_index_past_end(self):
        p = Playlist()
        for i in range(3):
            p.add_track(Track(file_path=f"/t{i}.mp3"))
        p.current_index = 2
        p.remove_track(2)
        assert p.current_index == 1

    def test_clear_resets_state(self):
        p = Playlist()
        p.add_track(Track(file_path="/t0.mp3"))
        p.current_index = 0
        p.clear()
        assert p.is_empty
        assert p.current_index == -1

    def test_current_track_none_when_empty(self):
        p = Playlist()
        assert p.current_track is None
