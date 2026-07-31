"""Config port - Protocol for configuration management."""

from typing import Protocol, Optional, Any
from pathlib import Path
from enum import Enum


class LayoutMode(Enum):
    """Player layout modes."""
    SIDE_BY_SIDE = "side_by_side"
    STACKED = "stacked"


class VisualizerStyle(Enum):
    """Visualizer display styles."""
    BARS_VERTICAL = "bars_vertical"
    BARS_HORIZONTAL = "bars_horizontal"
    WAVEFORM = "waveform"
    RADIAL = "radial"
    PARTICLES = "particles"


@dataclass
class AlternateViewsConfig:
    """Configuration for alternate views."""
    
    lyrics_enabled: bool = True
    cover_enabled: bool = True
    visualizer_enabled: bool = True


@dataclass 
class VisualizerConfig:
    """Configuration for visualizer."""
    
    style: VisualizerStyle = VisualizerStyle.BARS_VERTICAL
    color: str = "#00ff00"
    sensitivity: float = 1.0
    smoothing: float = 0.5


@dataclass
class AppConfig:
    """Application configuration."""
    
    # Playback
    volume: float = 0.7
    repeat_mode: str = "none"  # none, one, all
    shuffle: bool = False
    
    # UI
    layout: LayoutMode = LayoutMode.SIDE_BY_SIDE
    alternate_views: AlternateViewsConfig = AlternateViewsConfig()
    visualizer: VisualizerConfig = VisualizerConfig()
    
    # Library
    music_dirs: list = None
    auto_scan: bool = True
    
    # Download
    download_dir: str = "./downloads"
    download_quality: str = "opus"
    
    # Server
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    auto_discover_port: bool = True
    
    # Language
    language: str = "es"
    
    def __post_init__(self):
        if self.music_dirs is None:
            self.music_dirs = []


class ConfigPort(Protocol):
    """Protocol for configuration adapters.
    
    Implementations must handle loading, saving, and accessing
    configuration from portable and global locations.
    """

    def load(self) -> AppConfig:
        """Load configuration from disk.
        
        Returns:
            AppConfig with merged portable + global settings.
        """
        ...

    def save(self, config: AppConfig) -> None:
        """Save configuration to portable location.
        
        Args:
            config: Configuration to save.
        """
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g., "visualizer.style").
            default: Default value if key not found.
        
        Returns:
            Configuration value or default.
        """
        ...

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g., "visualizer.style").
            value: Value to set.
        """
        ...

    def get_config_path(self) -> Path:
        """Get the path to the portable config file.
        
        Returns:
            Path to config.json.
        """
        ...

    def get_data_dir(self) -> Path:
        """Get the portable data directory path.
        
        Returns:
            Path to data/ directory.
        """
        ...
