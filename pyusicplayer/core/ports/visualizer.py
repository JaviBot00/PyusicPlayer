"""Visualizer port - Protocol for audio spectrum visualization."""

from typing import Protocol, List
from dataclasses import dataclass
from enum import Enum


class VisualizerType(Enum):
    """Types of visualizer displays."""
    BARS_VERTICAL = "bars_vertical"
    BARS_HORIZONTAL = "bars_horizontal"
    WAVEFORM = "waveform"
    RADIAL = "radial"
    PARTICLES = "particles"


@dataclass
class VisualizerConfig:
    """Configuration for visualizer rendering."""
    
    visualizer_type: VisualizerType = VisualizerType.BARS_VERTICAL
    color: str = "#00ff00"
    background_color: str = "#000000"
    sensitivity: float = 1.0
    smoothing: float = 0.5
    bar_count: int = 32
    width: int = 800
    height: int = 200


@dataclass
class SpectrumData:
    """Processed spectrum data for visualization."""
    
    frequencies: List[float]  # Frequency values in Hz
    amplitudes: List[float]  # Amplitude values (0.0 to 1.0)
    raw_pcm: List[float]  # Raw PCM samples for waveform


class VisualizerPort(Protocol):
    """Protocol for visualizer adapters.
    
    Implementations must provide FFT processing and rendering
    for different visualizer styles.
    """

    def configure(self, config: VisualizerConfig) -> None:
        """Configure the visualizer.
        
        Args:
            config: Visualizer configuration.
        """
        ...

    def process_spectrum(self, pcm_data: List[float], sample_rate: int = 44100) -> SpectrumData:
        """Process raw PCM data into spectrum data using FFT.
        
        Args:
            pcm_data: Raw PCM samples.
            sample_rate: Audio sample rate in Hz.
        
        Returns:
            Processed SpectrumData with frequencies and amplitudes.
        """
        ...

    def render_bars_vertical(self, spectrum: SpectrumData) -> str:
        """Render vertical bars visualization as ANSI string.
        
        Args:
            spectrum: Processed spectrum data.
        
        Returns:
            ANSI escape sequence string for terminal rendering.
        """
        ...

    def render_bars_horizontal(self, spectrum: SpectrumData) -> str:
        """Render horizontal bars visualization as ANSI string.
        
        Args:
            spectrum: Processed spectrum data.
        
        Returns:
            ANSI escape sequence string for terminal rendering.
        """
        ...

    def render_waveform(self, spectrum: SpectrumData) -> str:
        """Render waveform visualization as ANSI string.
        
        Args:
            spectrum: Processed spectrum data.
        
        Returns:
            ANSI escape sequence string for terminal rendering.
        """
        ...

    def render_radial(self, spectrum: SpectrumData) -> str:
        """Render radial visualization as ANSI string.
        
        Args:
            spectrum: Processed spectrum data.
        
        Returns:
            ANSI escape sequence string for terminal rendering.
        """
        ...

    def render_particles(self, spectrum: SpectrumData) -> str:
        """Render particles visualization as ANSI string.
        
        Args:
            spectrum: Processed spectrum data.
        
        Returns:
            ANSI escape sequence string for terminal rendering.
        """
        ...

    def get_available_types(self) -> List[VisualizerType]:
        """Get list of available visualizer types.
        
        Returns:
            List of supported VisualizerType values.
        """
        ...

    def cycle_style(self) -> VisualizerType:
        """Cycle to the next visualizer style.
        
        Returns:
            The new current VisualizerType.
        """
        ...
