"""Dependency Injection container."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

from ..core.ports import AudioPort, MetadataPort
from ..core.ports.config import ConfigPort

T = TypeVar("T")

# Portable data directory — all persistent files live here.
DATA_DIR = Path(__file__).parent.parent.parent / "data"


class Container:
    """Minimal DI container: singletons, factories, or bare type registrations."""

    def __init__(self) -> None:
        self._singletons: dict[type, object] = {}
        self._factories: dict[type, Callable[[], object]] = {}
        self._types: dict[type, type] = {}

    def register_singleton(self, interface: type[T], instance: T) -> None:
        self._singletons[interface] = instance

    def register_factory(self, interface: type[T], factory: Callable[[], T]) -> None:
        self._factories[interface] = factory

    def register_type(self, interface: type[T], implementation: type[T]) -> None:
        self._types[interface] = implementation

    def resolve(self, interface: type[T]) -> T:
        if interface in self._singletons:
            return self._singletons[interface]  # type: ignore[return-value]
        if interface in self._factories:
            instance = self._factories[interface]()
            self._singletons[interface] = instance  # factories are memoized too
            return instance  # type: ignore[return-value]
        if interface in self._types:
            instance = self._types[interface]()
            self._singletons[interface] = instance
            return instance  # type: ignore[return-value]
        raise ValueError(f"No registration found for {interface.__name__}")

    def has(self, interface: type) -> bool:
        return interface in self._singletons or interface in self._factories or interface in self._types


def create_container() -> Container:
    """Build the container with real adapter wiring. This is the ONLY place
    in the codebase allowed to import concrete adapters."""
    from ..adapters.audio.pygame_adapter import PygameAudioAdapter
    from ..adapters.metadata.mutagen_adapter import MutagenMetadataAdapter
    from ..adapters.config.json_adapter import JsonConfigAdapter

    container = Container()
    container.register_singleton(AudioPort, PygameAudioAdapter())
    container.register_singleton(MetadataPort, MutagenMetadataAdapter())
    container.register_singleton(
        ConfigPort,
        JsonConfigAdapter(config_path=DATA_DIR / "config.json"),
    )
    from ..core.services import PlayerService
    container.register_factory(
        PlayerService,
        lambda: PlayerService(
            audio=container.resolve(AudioPort),
            metadata=container.resolve(MetadataPort),
        ),
    )
    return container
