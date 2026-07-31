# PyusicPlayer

Un reproductor de música interactivo escrito en Python, con interfaz TUI (Terminal) y GUI (Gráfica), más un servidor API para clientes Web y Android.

## Características

- **Reproducción**: Play, pausa, reanudar, parar, seek
- **Modos de reproducción**: Secuencial, bucle individual, bucle completo, aleatorio
- **Vistas alternas** (independientes, on/off con teclado):
  - **Letras de canciones**: Sincronizadas con LRCLIB o archivos .lrc locales
  - **Carátula del álbum**: Extraída de metadatos ID3 o archivo cover.jpg/png
  - **Visualizador de spectrum**: Analizador de frecuencias en tiempo real con 5 estilos
- **5 estilos de visualización**:
  - Barras verticales (clásico equalizer estilo CAVA/Winamp)
  - Barras horizontales
  - Forma de onda (waveform)
  - Radial (circular)
  - Partículas reactivas al beat
- **Sistema de ayuda**: F1 muestra atajos de teclado y controles
- **Layout configurable**: Lado a lado o apilado, configurable con settings y atajos
- **Gestión de biblioteca**: Indexación en SQLite con filtros por artista, álbum, carpeta
- **Descargas**: Descargar audio de YouTube/SoundCloud con yt-dlp
- **Multi-interfaz**: TUI (terminal), GUI (escritorio), API (web/móvil)
- **Portable**: Configuración y base de datos en la carpeta del proyecto
- **Multiplataforma**: Linux, Windows, macOS

## Instalación

### Requisitos

- Python 3.10+
- ffmpeg (para descargas y conversión de audio)

### Dependencias

```bash
pip install -r requirements.txt
```

### Archivos de audio necesarios

```bash
# Opcional: VLC como backend alternativo
pip install python-vlc
```

## Uso

### Modo TUI (Terminal)

```bash
python main.py --tui
```

### Modo GUI (Escritorio)

```bash
python main.py --gui
```

### Modo Servidor (API)

```bash
python main.py --server --port 8000
```

### Combinado (GUI + API)

```bash
python main.py --gui --api
```

## Atajos de Teclado

### Reproducción

| Tecla | Acción |
|-------|--------|
| `Space` | Play/Pausa |
| `S` | Parar |
| `N` | Siguiente canción |
| `P` | Canción anterior |
| `←/→` | Retroceder/Avanzar |
| `↑/↓` | Volumen arriba/abajo |
| `M` | Silenciar |

### Modos de Reproducción

| Tecla | Acción |
|-------|--------|
| `1` | Secuencial |
| `L` | Bucle individual |
| `Shift+L` | Bucle completo |
| `R` | Aleatorio |

### Vistas Alternas (On/Off independiente)

| Tecla | Acción |
|-------|--------|
| `Y` | Mostrar/ocultar Letras |
| `C` | Mostrar/ocultar Portada |
| `V` | Mostrar/ocultar Visualizador |

### Visualizador

| Tecla | Acción |
|-------|--------|
| `Ctrl+V` | Cambiar estilo de visualización (5 estilos) |

### Layout

| Tecla | Acción |
|-------|--------|
| `Shift+L` | Cambiar layout (lado a lado / apilado) |

### Utilidades

| Tecla | Acción |
|-------|--------|
| `F1` o `?` | Ayuda |
| `/` | Buscar en biblioteca |
| `Q` | Salir |

## Estructura del Proyecto

```
PyusicPlayer/
├── main.py                    # Punto de entrada
├── pyusicplayer/
│   ├── core/                  # Lógica de negocio (sin dependencias externas)
│   │   ├── ports/             # Interfaces (Protocol classes)
│   │   ├── domain/            # Modelos de datos
│   │   └── services/          # Lógica de negocio
│   ├── adapters/              # Implementaciones concretas
│   │   ├── audio/             # Backends de audio (pygame, vlc)
│   │   ├── metadata/          # Lectores de metadatos (mutagen)
│   │   ├── lyrics/            # Proveedores de letras (LRCLIB, local)
│   │   ├── notifications/     # Notificaciones del sistema
│   │   ├── config/            # Configuración
│   │   ├── library/           # Indexación SQLite
│   │   ├── downloader/        # Descargas yt-dlp
│   │   └── visualizer/        # Visualizadores de spectrum (5 estilos)
│   ├── interfaces/            # Capa de UI
│   │   ├── tui/               # Interfaz de terminal (Textual)
│   │   │   ├── screens/       # ModalScreen de ayuda
│   │   │   └── widgets/       # Widgets de vistas alternas
│   │   ├── gui/               # Interfaz gráfica (CustomTkinter)
│   │   │   ├── widgets/       # Frames de vistas alternas
│   │   │   └── menus/         # Menú de ayuda
│   │   └── api/               # Servidor FastAPI
│   ├── i18n/                  # Internacionalización
│   └── di/                    # Inyección de dependencias
├── data/                      # Datos portables (gitignored)
│   ├── config.json
│   └── library.db
├── assets/
│   └── placeholder.png
├── CONCEPT.md                 # Concepto original
├── AGENT.md                   # Contexto del agente
├── SPEC.md                    # Especificación técnica
├── README.md                  # Esta documentación (ES)
├── README_EN.md               # Documentación (EN)
├── INDEX.md                   # Índice de documentación
├── LEARNING.md                # Guía de aprendizaje (ES)
└── LICENSE
```

## Arquitectura

El proyecto sigue el patrón **Ports & Adapters** (Arquitectura Hexagonal):

- **Ports**: Interfaces definidas como `Protocol` classes
- **Adapters**: Implementaciones concretas de cada interface
- **Services**: Lógica de negocio que solo depende de ports
- **Container**: Conecta ports con adapters en el punto de entrada

### Principio Clave

> Un módulo NUNCA importa implementaciones concretas.
> Solo importa PROTOCOLOS (interfaces).
> La conexión se hace en el ENTRY POINT (main.py).

## Tecnologías

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| Audio | pygame / VLC | Reproducción de audio |
| Metadatos | mutagen | Lectura de tags ID3 |
| TUI | Textual | Interfaz de terminal moderna |
| GUI | CustomTkinter | Interfaz gráfica de escritorio |
| API | FastAPI | Servidor de streaming |
| BD | SQLite | Indexación de biblioteca |
| Descargas | yt-dlp | Descarga de audio |
| Visualizer | numpy (FFT) | Procesamiento numérico |
| i18n | gettext + Babel | Internacionalización |

## Formatos de Audio Soportados

- **Principal**: Opus (para descargas)
- **Soportados**: MP3, OGG, WAV, FLAC, M4A, AAC
- Todos los formatos soportados por pygame/VLC

## Configuración

La configuración se almacena en dos ubicaciones:

1. **Portable**: `./data/config.json` (junto al proyecto)
2. **Global**: `~/.config/pyusicplayer/config.json` (estándar XDG)

La configuración portable tiene prioridad sobre la global.

### Opciones de Visualización

```json
{
  "alternate_views": {
    "lyrics_enabled": false,
    "cover_enabled": false,
    "visualizer_enabled": false,
    "visualizer_style": "BARS_VERTICAL"
  },
  "layout": {
    "mode": "side_by_side",
    "alternate_position": "right",
    "split_ratio": 60
  },
  "visualizer": {
    "num_bars": 32,
    "smoothing": 0.3,
    "sensitivity": 1.0,
    "peak_hold": true
  }
}
```

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/stream/{id}` | Streaming de audio con Range requests |
| GET | `/api/cover/{id}` | Carátula del álbum como imagen |
| GET | `/api/lyrics/{id}` | Letras sincronizadas como JSON |
| GET | `/api/library` | Lista de canciones con filtros |
| GET | `/api/search?q=` | Búsqueda de canciones |
| POST | `/api/download` | Descargar audio desde URL |

## Documentación

| Fichero | Contenido |
|---------|-----------|
| [CONCEPT.md](CONCEPT.md) | Concepto original del proyecto |
| [AGENT.md](AGENT.md) | Contexto para agentes IA |
| [SPEC.md](SPEC.md) | Especificación técnica detallada |
| [README.md](README.md) | Esta documentación (ES) |
| [README_EN.md](README_EN.md) | Documentación (EN) |
| [INDEX.md](INDEX.md) | Índice de documentación |
| [LEARNING.md](LEARNING.md) | Guía de aprendizaje (ES) |

## Licencia

[MIT License](LICENSE)

## Autor

[HotGuy]
