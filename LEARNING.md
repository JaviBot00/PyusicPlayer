# PyusicPlayer - Guía de Aprendizaje

Esta guía documenta las decisiones técnicas, alternativas consideradas y conceptos aprendidos durante el desarrollo de PyusicPlayer. Pensada para aprender Python y arquitectura de software.

---

## 1. Arquitectura Modular (Ports & Adapters)

### ¿Qué es?

El patrón **Ports & Adapters** (también llamado Arquitectura Hexagonal) separa la lógica de negocio de los detalles de implementación. La idea clave:

- **Ports** (Interfaces): Definen QUÉ puede hacer el sistema, no CÓMO
- **Adapters** (Implementaciones): Implementan los ports con tecnologías concretas
- **Services** (Lógica): Usan los ports sin saber qué adapter hay detrás

### Ejemplo en código

```python
# core/ports/audio.py - DEFINICIÓN DEL CONTRATO
from typing import Protocol

class AudioBackend(Protocol):
    """Interface que TODO backend de audio debe cumplir."""
    
    def load(self, file_path: str) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def stop(self) -> None: ...

# adapters/audio/pygame_backend.py - IMPLEMENTACIÓN CONCRETA
class PygameAudioBackend:
    """Implementación usando pygame."""
    
    def __init__(self):
        mixer.init()
    
    def load(self, file_path: str) -> None:
        mixer.music.load(file_path)
    
    def play(self) -> None:
        mixer.music.play()
    
    # ... resto de métodos

# core/services/player_service.py - LÓGICA PURA
class PlayerService:
    """Lógica del player. NO sabe qué backend usa."""
    
    def __init__(self, audio: AudioBackend):  # Inyectado
        self._audio = audio
    
    def play_song(self, path: str) -> None:
        self._audio.load(path)
        self._audio.play()
```

### ¿Por qué funciona?

Si mañana quieres cambiar pygame por VLC:

1. Creas `adapters/audio/vlc_backend.py`
2. Modificas `di/container.py` para usar VLC
3. **NO tocas** `player_service.py`

El servicio no sabe qué usa por dentro. Solo conoce el contrato.

### Pros y Contras

| Pros | Contras |
|------|---------|
| Componentes intercambiables | Más archivos que un monolito |
| Testing fácil (mock de ports) | Curva de aprendizaje inicial |
| Mantenimiento simplificado | Puede ser overkill para proyectos simples |
| Escalabilidad | Requiere disciplina |

---

## 2. Protocol Classes (Python typing)

### ¿Qué son?

`Protocol` permite definir interfaces estructuradas (duck typing tipado). Una clase satisface un Protocol si tiene los métodos correctos, sin necesidad de heredar explícitamente.

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self, x: int, y: int) -> None: ...

# Esta clase cumple Drawable aunque NO hereda de él
class Circle:
    def draw(self, x: int, y: int) -> None:
        print(f"Drawing circle at {x}, {y}")

# Esto funciona
def render(shape: Drawable):
    shape.draw(0, 0)

render(Circle())  # ✅ Válido
```

### Protocol vs ABC

| Protocol (Structural) | ABC (Nominal) |
|-----------------------|---------------|
| No necesita herencia explícita | La clase DEBE heredar |
| Funciona con clases de terceros | Solo con clases propias |
| Se puede definir después de implementar | Requiere modificar implementaciones |
| Más flexible | Más explícito |

### Ejemplo real en PyusicPlayer

```python
# Definimos el Protocol
class MetadataReader(Protocol):
    def read(self, file_path: str) -> SongMetadata: ...
    def get_cover(self, file_path: str) -> Optional[bytes]: ...

# mutagen cumple el Protocol aunque no lo sabe
class MutagenReader:
    def __init__(self):
        from mutagen.easyid3 import EasyID3  # Dependencia externa
    
    def read(self, file_path: str) -> SongMetadata:
        audio = EasyID3(file_path)
        return SongMetadata(
            title=audio.get('title', [''])[0],
            artist=audio.get('artist', [''])[0],
        )
    
    def get_cover(self, file_path: str) -> Optional[bytes]:
        # Implementación...
        pass

# El servicio NO importa MutagenReader
class LibraryService:
    def __init__(self, metadata: MetadataReader):  # Solo importa el Protocol
        self._metadata = metadata
```

---

## 3. Dependency Injection

### ¿Qué es?

Inyección de dependencias: en lugar de que un objeto cree sus dependencias, estas se las "inyectan" (se las pasan como parámetros).

```python
# ❌ MAL: Acoplamiento directo
class PlayerService:
    def __init__(self):
        self.audio = PygameAudioBackend()  # Dependencia rígida

# ✅ BIEN: Inyección de dependencias
class PlayerService:
    def __init__(self, audio: AudioBackend):  # Dependencia flexible
        self.audio = audio
```

### Container (Wiring)

El container conecta ports con adapters en el punto de entrada:

```python
# di/container.py
from core.ports.audio import AudioBackend
from adapters.audio.pygame_backend import PygameAudioBackend

class Container:
    """Conecta interfaces con implementaciones."""
    
    def __init__(self, audio_backend: str = "pygame"):
        if audio_backend == "pygame":
            self.audio: AudioBackend = PygameAudioBackend()
        elif audio_backend == "vlc":
            from adapters.audio.vlc_backend import VLCAudioBackend
            self.audio: AudioBackend = VLCAudioBackend()

# main.py - PUNTO DE ENTRADA
container = Container(audio_backend="pygame")
player = PlayerService(audio=container.audio)
```

### Dónde se aplica

| Componente | Port | Adapters |
|------------|------|----------|
| Audio | AudioBackend | pygame, vlc, null |
| Metadata | MetadataReader | mutagen, tinytag |
| Lyrics | LyricsProvider | lrclib, local, null |
| Config | ConfigProvider | json, memory |
| Library | LibraryIndexer | sqlite, memory |
| Notifier | Notifier | linux, macos, windows |
| Visualizer | Visualizer | bars_vertical, bars_horizontal, waveform, radial, particles |

---

## 4. Strategy Pattern

### ¿Qué es?

El patrón Strategy permite cambiar algoritmos en tiempo de ejecución sin modificar el código que los usa.

```python
# Estrategias de reproducción
class PlayStrategy(Protocol):
    def next(self, current_index: int, total: int) -> int: ...

class SequentialStrategy:
    def next(self, current_index: int, total: int) -> int:
        return (current_index + 1) % total

class ShuffleStrategy:
    def next(self, current_index: int, total: int) -> int:
        return random.randint(0, total - 1)

class LoopOneStrategy:
    def next(self, current_index: int, total: int) -> int:
        return current_index  # Siempre la misma

# Uso
class PlaylistManager:
    def __init__(self, strategy: PlayStrategy):
        self._strategy = strategy
    
    def next_track(self):
        self._current = self._strategy.next(self._current, len(self._tracks))
    
    def set_strategy(self, strategy: PlayStrategy):
        self._strategy = strategy
```

### Beneficios

- Sin `if/else` gigantes
- Fácil de testear cada estrategia
- Se puede cambiar en tiempo de ejecución
- Nuevo comportamiento = nueva clase, no modificar código existente

---

## 5. Observer Pattern

### ¿Qué es?

El Observer permite notificar a múltiples objetos cuando ocurre un evento, sin acoplamiento directo.

```python
from typing import Callable, List

class EventBus:
    """Centro de eventos simple."""
    
    def __init__(self):
        self._listeners: dict[str, List[Callable]] = {}
    
    def on(self, event: str, callback: Callable):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def emit(self, event: str, data=None):
        for callback in self._listeners.get(event, []):
            callback(data)

# Uso
event_bus = EventBus()

# UI se suscribe
def on_track_changed(song):
    print(f"Ahora suena: {song.title}")

event_bus.on("track_changed", on_track_changed)

# Notificaciones se suscriben
def on_track_notify(song):
    notify(title="Ahora sonando", message=song.title)

event_bus.on("track_changed", on_track_notify)

# Player emite eventos
event_bus.emit("track_changed", current_song)
```

### En PyusicPlayer

```python
class PlayerService:
    def __init__(self, audio: AudioBackend, event_bus: EventBus):
        self._audio = audio
        self._events = event_bus
        
        # Suscribirse a eventos del backend
        self._audio.on_track_end(self._on_track_end)
    
    def _on_track_end(self):
        # Emitir evento para UI, notificaciones, etc.
        self._events.emit("track_ended", self.current_song)
        self._next_track()
```

---

## 6. Async Programming (asyncio)

### ¿Qué es?

Permite ejecutar código concurrente sin threads. Ideal para I/O-bound tasks (red, archivos).

```python
import asyncio
import aiohttp

# Función asíncrona
async def fetch_lyrics(artist: str, title: str) -> str:
    async with aiohttp.ClientSession() as session:
        url = f"https://lrclib.net/api/get?artist_name={artist}&track_name={title}"
        async with session.get(url) as response:
            data = await response.json()
            return data.get("plainLyrics", "")

# Ejecutar
async def main():
    lyrics = await fetch_lyrics("The Beatles", "Yesterday")
    print(lyrics)

asyncio.run(main())
```

### Cuándo usar async

| Escenario | ¿Async? |
|-----------|---------|
| Llamadas HTTP (APIs) | ✅ Sí |
| Lectura de archivos | ⚠️ Opcional |
| Cálculos CPU | ❌ No (usar multiprocessing) |
| UI (tkinter) | ⚠️ Con cuidado (thread separado) |
| FFT en tiempo real | ⚠️ Usar numpy (no es I/O) |

### FastAPI es async nativo

```python
from fastapi import FastAPI
import aiohttp

app = FastAPI()

@app.get("/api/lyrics/{song_id}")
async def get_lyrics(song_id: str):
    # FastAPI maneja async automáticamente
    async with aiohttp.ClientSession() as session:
        async with session.get("https://lrclib.net/...") as resp:
            return await resp.json()
```

---

## 7. Streaming de Audio (HTTP Range Requests)

### ¿Qué es?

Para hacer seek en audio streaming, el cliente envía `Range` headers y el servidor responde con `206 Partial Content`.

```
Cliente: "Dame bytes 1000-2000"
Servidor: "Aquí tienes bytes 1000-2000 de 50000 totales" (206)
```

### Implementación en FastAPI

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import os

app = FastAPI()

def send_bytes_range_requests(file_obj, start: int, end: int, chunk_size: int = 10_000):
    """Envía archivo en chunks usando Range requests (RFC 7233)."""
    with file_obj as f:
        f.seek(start)
        while (pos := f.tell()) <= end:
            read_size = min(chunk_size, end + 1 - pos)
            yield f.read(read_size)

@app.get("/api/stream/{song_id}")
async def stream_audio(song_id: str, request: Request):
    file_path = get_song_path(song_id)
    file_size = os.stat(file_path).st_size
    
    range_header = request.headers.get("range")
    headers = {
        "content-type": "audio/opus",
        "accept-ranges": "bytes",
        "content-length": str(file_size),
    }
    
    start = 0
    end = file_size - 1
    status_code = 200
    
    if range_header:
        # Parsear "bytes=1000-"
        range_parts = range_header.replace("bytes=", "").split("-")
        start = int(range_parts[0])
        end = int(range_parts[1]) if range_parts[1] else file_size - 1
        
        headers["content-range"] = f"bytes {start}-{end}/{file_size}"
        headers["content-length"] = str(end - start + 1)
        status_code = 206
    
    return StreamingResponse(
        send_bytes_range_requests(open(file_path, "rb"), start, end),
        headers=headers,
        status_code=status_code,
    )
```

---

## 8. SQLite para Indexación

### ¿Por qué SQLite?

- **Portable**: Todo en un fichero `.db`
- **Sin servidor**: No necesita proceso separado
- **Rápido**: Suficiente para miles de canciones
- **SQL estándar**: Fácil de consultar

### Esquema normalizado

```sql
-- Evitar duplicación de strings
CREATE TABLE artists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE albums (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id)
);

CREATE TABLE songs (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    album_id INTEGER REFERENCES albums(id),
    file_path TEXT NOT NULL UNIQUE
);

-- Índices para búsquedas rápidas
CREATE INDEX idx_songs_artist ON songs(artist_id);
CREATE INDEX idx_songs_album ON songs(album_id);
```

### Python + SQLite

```python
import sqlite3
from dataclasses import dataclass

@dataclass
class Song:
    id: int
    title: str
    artist: str
    album: str

class SQLiteLibrary:
    def __init__(self, db_path: str):
        self._db = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self):
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT,
                file_path TEXT UNIQUE
            );
        """)
    
    def search(self, query: str) -> list[Song]:
        cursor = self._db.execute(
            "SELECT * FROM songs WHERE title LIKE ? OR artist LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
        return [Song(*row) for row in cursor.fetchall()]
```

---

## 9. Configuración Portable vs Global

### XDG Base Directory

Estándar Linux para ubicaciones de configuración:

```
~/.config/              # Configuración del usuario
~/.local/share/         # Datos del usuario
~/.cache/               # Caché del usuario
```

### Implementación dual

```python
import json
import os
from pathlib import Path

class JsonConfig:
    """Configuración portable + global."""
    
    def __init__(self):
        # Portable (junto al proyecto)
        self._portable_path = Path("./data/config.json")
        
        # Global (XDG)
        self._global_path = Path.home() / ".config" / "pyusicplayer" / "config.json"
        
        self._data = {}
        self.load()
    
    def load(self):
        # Prioridad: portable > global > defaults
        self._data = self._get_defaults()
        
        if self._global_path.exists():
            with open(self._global_path) as f:
                self._data.update(json.load(f))
        
        if self._portable_path.exists():
            with open(self._portable_path) as f:
                self._data.update(json.load(f))
    
    def save(self):
        # Guardar en portable por defecto
        self._portable_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._portable_path, "w") as f:
            json.dump(self._data, f, indent=2)
    
    def _get_defaults(self) -> dict:
        return {
            "volume": 80,
            "loop_mode": "none",
            "shuffle": False,
            "language": "en_US"
        }
```

---

## 10. Internacionalización (i18n)

### Flujo de trabajo

1. Marcar strings con `_()`
2. Extraer a fichero `.pot` (template)
3. Traducir a `.po` (por idioma)
4. Compilar a `.mo` (binario)
5. Cargar en runtime

### Ejemplo

```python
# i18n/loader.py
import gettext

def setup_i18n(lang: str):
    translation = gettext.translation(
        domain='messages',
        localedir='locales',
        languages=[lang],
        fallback=True
    )
    translation.install()
    return translation.gettext

# En cualquier archivo
from i18n.loader import setup_i18n
_ = setup_i18n("es_ES")

print(_("Playing"))  # "Reproduciendo"
```

### Fichero PO

```po
# locales/es_ES.po
msgid "Playing"
msgstr "Reproduciendo"

msgid "Paused"
msgstr "Pausado"

msgid "Stopped"
msgstr "Detenido"
```

---

## 11. FFT y Visualización de Spectrum

### ¿Qué es FFT?

**FFT** (Fast Fourier Transform) convierte una señal del **dominio del tiempo** (amplitud vs tiempo) al **dominio de la frecuencia** (magnitud vs frecuencia).

```
Señal temporal:    ~~~∿~~~∿~~~  (amplitud cambia con el tiempo)
                   ↓ FFT
Espectro:          |||||||||||  (barras de frecuencias)
                   bajo → alto
```

### Implementación con numpy

```python
import numpy as np

def compute_fft(audio_data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
    """Calcular FFT de datos de audio."""
    
    # 1. Aplicar ventana de Hann (reducir spectral leakage)
    window = np.hanning(len(audio_data))
    windowed = audio_data * window
    
    # 2. Calcular FFT
    fft_data = np.fft.rfft(windowed)
    
    # 3. Obtener magnitudes (valores reales positivos)
    magnitudes = np.abs(fft_data)
    
    # 4. Normalizar
    magnitudes = magnitudes / len(audio_data)
    
    return magnitudes

# Ejemplo de uso
sample_rate = 44100
duration = 0.1  # 100ms de audio
samples = int(sample_rate * duration)

# Generar audio de ejemplo (tono de 440Hz = La)
t = np.linspace(0, duration, samples)
audio = np.sin(2 * np.pi * 440 * t)

# Calcular FFT
spectrum = compute_fft(audio, sample_rate)

# Obtener frecuencias correspondientes
freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)
```

### Por qué numpy y no scipy/scikit?

| Opción | Pros | Contras |
|--------|------|---------|
| **numpy** | Rápido, incluido en muchas deps | API básica |
| **scipy** | Más features signal processing | Dependencia extra |
| **scikit-mir** | Específico para audio | Muy específico |

**Decisión**: numpy es suficiente para visualización básica y está en el ecosistema científico de Python.

### Pipeline de Visualización

```
Audio Input → Buffer → Windowing → FFT → Magnitudes → Smoothing → Render
    ↓           ↓          ↓         ↓         ↓            ↓         ↓
 pygame    np.array   hann()    rfft()    abs()      exponential   draw()
 mixer                                       moving avg
```

### Código del Visualizer Base

```python
import numpy as np
from abc import ABC, abstractmethod
from core.domain.visualizer_style import VisualizerStyle

class BaseVisualizer(ABC):
    """Clase base con procesamiento FFT para todos los visualizadores."""
    
    def __init__(self):
        self._is_running = False
        self._sample_rate = 44100
        self._fft_size = 1024
        self._width = 800
        self._height = 400
        self._frequency_data = np.zeros(self._fft_size // 2)
    
    def start(self, sample_rate: int = 44100) -> None:
        self._sample_rate = sample_rate
        self._is_running = True
    
    def stop(self) -> None:
        self._is_running = False
    
    def update(self, audio_data: np.ndarray) -> None:
        if not self._is_running:
            return
        
        # Aplicar ventana de Hann
        window = np.hanning(len(audio_data))
        windowed = audio_data * window
        
        # FFT
        fft_data = np.fft.rfft(windowed)
        magnitudes = np.abs(fft_data)
        
        # Suavizado exponencial (para estabilidad visual)
        alpha = 0.3
        self._frequency_data = (
            alpha * magnitudes[:len(self._frequency_data)] + 
            (1 - alpha) * self._frequency_data
        )
        
        # Llamar al renderizador específico
        self._render(self._frequency_data)
    
    @abstractmethod
    def _render(self, frequency_data: np.ndarray) -> None:
        """Renderizar según el estilo. Cada adaptador implementa esto."""
        pass
```

### Los 5 Estilos de Visualización

#### 1. Barras Verticales (CAVA/Winamp)

```python
class BarsVerticalVisualizer(BaseVisualizer):
    """Estilo clásico: barras verticales de equalizer."""
    
    def __init__(self):
        super().__init__()
        self._num_bars = 32
        self._bar_peaks = np.zeros(self._num_bars)
    
    def _render(self, frequency_data: np.ndarray) -> None:
        # Agrupar frecuencias en barras (escala logarítmica)
        bar_heights = self._frequencies_to_bars(frequency_data)
        
        # Peak hold con decay
        self._bar_peaks = np.maximum(bar_heights, self._bar_peaks * 0.95)
        
        # Dibujar cada barra
        bar_width = self._width // self._num_bars
        for i, (height, peak) in enumerate(zip(bar_heights, self._bar_peaks)):
            x = i * bar_width
            bar_h = int(height * self._height)
            color = self._get_color(i, self._num_bars)  # Rainbow gradient
            self._draw_bar(x, bar_h, bar_width, color)
```

#### 2. Barras Horizontales

```python
class BarsHorizontalVisualizer(BaseVisualizer):
    """Barras horizontales (alternativa moderna)."""
    
    def _render(self, frequency_data: np.ndarray) -> None:
        bar_heights = self._frequencies_to_bars(frequency_data)
        bar_height = self._height // self._num_bars
        
        for i, height in enumerate(bar_heights):
            y = i * bar_height
            bar_w = int(height * self._width)
            color = self._get_color(i, self._num_bars)
            self._draw_hbar(y, bar_w, bar_height, color)
```

#### 3. Waveform (Onda)

```python
class WaveformVisualizer(BaseVisualizer):
    """Forma de onda en tiempo real."""
    
    def _render(self, frequency_data: np.ndarray) -> None:
        # Para waveform, usar datos temporales en vez de frecuencia
        points = []
        step = self._width / len(self._waveform_buffer)
        
        for i, amplitude in enumerate(self._waveform_buffer):
            x = int(i * step)
            y = int((1 - amplitude) * self._height / 2)
            points.append((x, y))
        
        self._draw_waveform(points, color=(0, 255, 128))
```

#### 4. Radial (Circular)

```python
import math

class RadialVisualizer(BaseVisualizer):
    """Visualización circular/radial."""
    
    def _render(self, frequency_data: np.ndarray) -> None:
        center_x = self._width // 2
        center_y = self._height // 2
        max_radius = min(center_x, center_y) * 0.8
        
        num_bars = len(frequency_data)
        angle_step = 2 * math.pi / num_bars
        
        for i, magnitude in enumerate(frequency_data):
            angle = i * angle_step
            bar_length = magnitude * max_radius
            
            inner_radius = max_radius * 0.3
            x1 = center_x + inner_radius * math.cos(angle)
            y1 = center_y + inner_radius * math.sin(angle)
            
            outer_radius = inner_radius + bar_length
            x2 = center_x + outer_radius * math.cos(angle)
            y2 = center_y + outer_radius * math.sin(angle)
            
            color = self._get_color(i, num_bars)
            self._draw_line(x1, y1, x2, y2, color)
```

#### 5. Partículas

```python
import random

class ParticlesVisualizer(BaseVisualizer):
    """Partículas reactivas al beat."""
    
    def __init__(self):
        super().__init__()
        self._particles = []
        self._beat_threshold = 0.7
    
    def _render(self, frequency_data: np.ndarray) -> None:
        # Detectar beat (bass frequencies)
        bass_energy = np.mean(frequency_data[:10])
        
        # Generar nuevas partículas en el beat
        if bass_energy > self._beat_threshold:
            self._spawn_particles(int(bass_energy * 20))
        
        # Actualizar y dibujar partículas
        self._update_particles()
        self._draw_particles()
    
    def _spawn_particles(self, count: int):
        for _ in range(count):
            self._particles.append({
                'x': self._width // 2,
                'y': self._height // 2,
                'vx': random.uniform(-5, 5),
                'vy': random.uniform(-5, 5),
                'life': 1.0,
                'color': self._random_color()
            })
```

### Conexión con el Player

```python
class PlayerService:
    def __init__(self, audio: AudioBackend, visualizer: Visualizer):
        self._audio = audio
        self._visualizer = visualizer
        
        # Suscribirse a actualizaciones de audio
        self._audio.on_audio_data(self._on_audio_data)
    
    def _on_audio_data(self, audio_data: np.ndarray):
        """Callback con datos de audio en tiempo real."""
        self._visualizer.update(audio_data)
```

### Rendimiento

| Métrica | Objetivo |
|---------|----------|
| FPS | 60fps |
| Latencia FFT | < 16ms |
| Uso memoria | < 50MB extra |

**Optimizaciones:**
- Usar `np.fft.rfft` (real FFT, más rápido)
- Buffer circular para reutilizar memoria
- Suavizado exponencial (no recalcular cada frame)
- Peak hold con decay (evitar flickering)

---

## 12. Sistema de Ayuda

### TUI (Textual ModalScreen)

```python
from textual.screen import ModalScreen
from textual.widgets import Static, ScrollableContainer

class HelpScreen(ModalScreen[None]):
    """Modal con ayuda y atajos de teclado."""
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("up", "scroll_up"),
        ("down", "scroll_down"),
    ]
    
    def compose(self):
        with Vertical():
            yield Static("PyusicPlayer Help", classes="title")
            with ScrollableContainer():
                yield Static(self._build_help_content())
    
    def _build_help_content(self) -> str:
        return """
[bold]Playback Controls[/bold]
Space       Play/Pause
S           Stop
N           Next track
P           Previous track

[bold]Alternate Views[/bold]
Y           Toggle Lyrics
C           Toggle Cover
V           Toggle Visualizer
Ctrl+V      Cycle visualizer style
"""
```

### GUI (CustomTkinter)

```python
import customtkinter as ctk

class HelpDialog(ctk.CTkToplevel):
    """Diálogo de ayuda con atajos de teclado."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Help")
        self.geometry("500x600")
        self.transient(parent)
        self.grab_set()
        
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Añadir secciones de ayuda
        self._add_section(scroll, "Playback Controls", [
            ("Space", "Play/Pause"),
            ("S", "Stop"),
        ])
```

---

## 13. Comparativa de Alternativas

### Audio Backend

| Opción | Pros | Contras |
|--------|------|---------|
| **pygame** | Simple, incluido, mp3/ogg/wav | Seeking limitado, sin FLAC nativo |
| **python-vlc** | Soporta TODOS los formatos | Requiere VLC instalado |
| **python-mpv** | Excelente seek, API rica | Requiere mpv, complejo |
| **ffpyplayer** | Soporta todo vía FFmpeg | Overkill, pesado |

**Decisión**: pygame (primario) + VLC (alternativa documentada)

### TUI Framework

| Opción | Pros | Contras |
|--------|------|---------|
| **Textual** | Moderno, CSS, mouse, 36k stars | Curva aprendizaje media |
| **prompt_toolkit** | Maduro (IPython) | Sin widgets modernos |
| **Urwid** | Estable, ligero | UI anticuada |

**Decisión**: Textual

### GUI Framework

| Opción | Pros | Contras |
|--------|------|---------|
| **Tkinter** | Incluido, simple | UI anticuada |
| **CustomTkinter** | Moderno, fácil, MIT | Limitado para apps complejas |
| **PySide6** | Qt power, LGPL | Pesado (~50-100MB) |
| **Kivy** | Touch/mobile | No look nativo |

**Decisión**: CustomTkinter

### Metadata

| Opción | Pros | Contras |
|--------|------|---------|
| **mutagen** | Multi-formato, activo | API basada en keys nativas |
| **eyed3** | API amigable | Solo mp3, menos mantenimiento |
| **tinytag** | Ultra-ligero | Solo lectura |

**Decisión**: mutagen + EasyID3

### Lyrics

| Opción | Pros | Contras |
|--------|------|---------|
| **LRCLIB** | Gratis, open source | Base mediana |
| **Musixmatch** | Base grande | API key requerida |
| **Local .lrc** | Offline, control total | Usuario debe proveer |

**Decisión**: LRCLIB + local .lrc

### Framework API

| Opción | Pros | Contras |
|--------|------|---------|
| **FastAPI** | Async, OpenAPI, comunidad | No incluye auth |
| **Litestar** | ~2x más rápido | Comunidad pequeña |
| **Flask** | Simplicidad | WSGI (bloqueante) |
| **Quart** | Flask async | Comunidad pequeña |

**Decisión**: FastAPI

### Notificaciones

| Opción | Pros | Contras |
|--------|------|---------|
| **plyer** | Cross-platform | Actualizaciones lentas |
| **Nativas** | Zero dependencias | Código por OS |
| **notifier.py** | Multi-platform | Depende de libnotify |

**Decisión**: Nativas (notify-send / osascript / win10toast)

### Visualización de Audio

| Opción | Pros | Contras |
|--------|------|---------|
| **numpy FFT** | Rápido, incluido | API básica |
| **scipy** | Más features | Dependencia extra |
| **matplotlib** | Fácil de usar | No es real-time |
| **pygame** | Ya incluido | Limitado para gráficos |

**Decisión**: numpy FFT + pygame/render para dibujar

---

## 14. Lecciones Aprendidas

### 1. Arquitectura sobre features
> "Prioritize perfect architecture over something playable"

Un buen diseño permite crecer. Un código rápido pero desordenado frena a largo plazo.

### 2. Dependencias en el entry point
> "A module NEVER imports concrete implementations"

Al principio parece excesivo, pero facilita:
- Testing (mock fácil)
- Cambio de tecnologías
- Mantenimiento

### 3. Protocol > ABC para flexibilidad
> "Post-hoc abstraction"

Con Protocol puedes definir la interfaz DESPUÉS de implementar. Con ABC debes heredar explícitamente.

### 4. Async no es siempre mejor
> "Half-measures make things worse"

Si tu código hace I/O real (HTTP, archivos), async ayuda. Si es CPU-bound, puede empeorar las cosas.

### 5. SQLite es suficiente
> "Premature optimization is the root of all evil"

Para miles de canciones, SQLite es perfecto. No necesitas PostgreSQL para una biblioteca local.

### 6. Portable > Global para empezar
> "Convention over configuration"

Portable permite probar sin instalar nada global. Global es para producción.

### 7. FFT es CPU-bound, no I/O
> "Know your bottleneck"

La FFT es un cálculo CPU, no I/O. Usar numpy (C backend) es clave para 60fps.

### 8. Suavizado exponencial
> "Raw data is noisy"

Los datos FFT crudos son inestables visualmente. El suavizado exponencial (`alpha * new + (1-alpha) * old`) estabiliza la visualización.

---

## 15. Recursos de Aprendizaje

### Documentación oficial
- [Python typing](https://docs.python.org/3/library/typing.html)
- [Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [SQLite](https://docs.python.org/3/library/sqlite3.html)
- [gettext](https://docs.python.org/3/library/gettext.html)
- [numpy FFT](https://numpy.org/doc/stable/reference/routines.fft.html)

### Frameworks
- [Textual](https://textual.textualize.io/)
- [CustomTkinter](https://customtkinter.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [mutagen](https://mutagen.readthedocs.io/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

### Patrones de diseño
- [Refactoring Guru - Patterns](https://refactoring.guru/design-patterns)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)

### Audio y FFT
- [FFT Explained](https://www.jezzamon.com/fft/index.html)
- [Audio Signal Processing (Wikipedia)](https://en.wikipedia.org/wiki/Audio_signal_processing)
- [CAVA Source Code](https://github.com/karlstav/cava)

---

## 16. Glossary

| Término | Definición |
|---------|------------|
| **Protocol** | Interface estructural (duck typing tipado) |
| **Port** | Interface que define un contrato |
| **Adapter** | Implementación concreta de un port |
| **DI** | Dependency Injection (inyección de dependencias) |
| **TUI** | Terminal User Interface |
| **GUI** | Graphical User Interface |
| **ASGI** | Asynchronous Server Gateway Interface |
| **Range Request** | HTTP request para obtener partes de un archivo |
| **XDG** | X Desktop Group (estándar de ubicaciones) |
| **i18n** | Internationalization (internacionalización) |
| **l10n** | Localization (localización) |
| **PO** | Portable Object (fichero de traducción) |
| **MO** | Machine Object (fichero binario compilado) |
| **FFT** | Fast Fourier Transform (transformada rápida de Fourier) |
| **Spectrum** | Espectro de frecuencias |
| **dBFS** | Decibels Full Scale (escala de decibelios) |
| **Peak Hold** | Mantener el pico máximo visible |
| **Smoothing** | Suavizado de datos |
| **ModalScreen** | Pantalla modal en Textual |
| **CAVA** | Cross-platform Audio Visualizer |
