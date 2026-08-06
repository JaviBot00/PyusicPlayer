"""Tests for the DI container: this is what used to be broken (create_container()
returned an empty container that resolved nothing). These tests exist
specifically so that regression can never silently return."""

from __future__ import annotations

import pytest

from pyusicplayer.core.ports import AudioPort, MetadataPort
from pyusicplayer.core.services import PlayerService
from pyusicplayer.di.container import Container, create_container


class TestCreateContainerWiring:
    def test_resolves_audio_port(self, container: Container):
        audio = container.resolve(AudioPort)
        assert audio is not None

    def test_resolves_metadata_port(self, container: Container):
        metadata = container.resolve(MetadataPort)
        assert metadata is not None

    def test_resolves_player_service_with_real_dependencies_injected(self, container: Container):
        service = container.resolve(PlayerService)
        assert isinstance(service, PlayerService)

    def test_singletons_are_the_same_instance_across_resolves(self, container: Container):
        first = container.resolve(AudioPort)
        second = container.resolve(AudioPort)
        assert first is second

    def test_player_service_is_memoized_too(self, container: Container):
        first = container.resolve(PlayerService)
        second = container.resolve(PlayerService)
        assert first is second


class TestContainerBasics:
    def test_resolving_unregistered_type_raises(self):
        c = Container()
        with pytest.raises(ValueError):
            c.resolve(str)

    def test_register_singleton_and_resolve(self):
        c = Container()
        c.register_singleton(str, "hello")
        assert c.resolve(str) == "hello"

    def test_has_reports_registered_types(self):
        c = Container()
        assert not c.has(str)
        c.register_singleton(str, "x")
        assert c.has(str)

    def test_two_calls_to_create_container_are_independent(self):
        c1 = create_container()
        c2 = create_container()
        assert c1.resolve(AudioPort) is not c2.resolve(AudioPort)
