# PyusicPlayer

Un reproductor de música interactivo escrito en Python, con interfaz TUI (Terminal) y GUI (Gráfica), más un servidor API para clientes Web y Android.

> **Estado real del proyecto:** de todo lo descrito en este documento, solo
> la reproducción por TUI está implementada y probada hoy. GUI, API, base
> de datos de biblioteca, letras, visualizador, notificaciones, descargas,
> i18n y persistencia de configuración son diseño objetivo, no código
> existente. El detalle exacto de qué está hecho vive en
> [AGENT.md](AGENT.md#implementation-status), que se mantiene actualizado
> a propósito para no repetir el problema que tenía esta documentación
> antes (afirmar cosas como completadas que en realidad eran solo un
> esqueleto sin conectar).

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

_(Lista de características objetivo completa. Ver arriba qué está realmente implementado.)_

## Instalación

### Requisitos

- Python 3.10+
- ffmpeg (necesario también para generar los fixtures de audio de los tests)

### Dependencias

```bash
pip install -r requirements.txt

# Solo si vas a correr los tests o a contribuir código:
pip install -r requirements-dev.txt
```

## Uso

### Modo TUI (Terminal) — funcional hoy

```bash
python -m pyusicplayer --tui
python -m pyusicplayer --music-dir /ruta/a/tu/musica --tui
```

### Modo GUI / Servidor API — no implementados todavía

```bash
python -m pyusicplayer --gui     # termina con mensaje "not implemented"
python -m pyusicplayer --server  # termina con mensaje "not implemented"
```

## Tests

```bash
pip install -r requirements-dev.txt

pytest                  # suite completa
pytest -m "not audio"   # ciclo rápido: sin pygame/mutagen reales
pytest tests/core/      # solo una capa
```

Los tests de audio real (`@pytest.mark.audio`) generan sus propios ficheros
de prueba con `ffmpeg` al arrancar la sesión de tests (`tests/conftest.py`);
si no tienes `ffmpeg` instalado, esos tests se saltan con un aviso claro en
vez de fallar. Ver la sección "Testing" de [AGENT.md](AGENT.md#testing) para
el detalle de qué cubre cada capa y por qué (incluye dos bugs reales que
solo se encontraron escribiendo tests, no probando a mano).

## Atajos de Teclado

### Reproducción (implementado)

| Tecla | Acción |
|-------|--------|
| `Space` | Play/Pausa |
| `S` | Parar |
| `N` | Siguiente canción |
| `P` | Canción anterior |
| `←/→` | Retroceder/Avanzar (±5s) |
| `↑/↓` | Volumen arriba/abajo |

### Modos de Reproducción (implementado)

| Tecla | Acción |
|-------|--------|
| `1` | Secuencial |
| `L` | Bucle individual |
| `Shift+L` | Bucle completo |
| `R` | Aleatorio |

### Pendiente (diseño futuro, sin implementar)

| Tecla | Acción |
|-------|--------|
| `M` | Silenciar |
| `Y` / `C` / `V` | Letras / Portada / Visualizador |
| `Ctrl+V` | Cambiar estilo de visualización |
| `F1` o `?` | Ayuda |
| `/` | Buscar en biblioteca |

## Estructura del Proyecto

```
PyusicPlayer/
├── pyusicplayer/
│   ├── __main__.py             # Punto de entrada (--tui funcional; --gui/--server avisan que faltan)
│   ├── core/                   # Lógica de negocio (sin dependencias externas)
│   │   ├── models.py           # Track, Playlist (shuffle Fisher-Yates)
│   │   ├── services.py         # PlayerService
│   │   └── ports/              # Protocol interfaces (solo Audio/Metadata tienen adapter real)
│   ├── adapters/
│   │   ├── audio/pygame_adapter.py       # Implementado y probado
│   │   ├── metadata/mutagen_adapter.py   # Implementado y probado
│   │   ├── lyrics/ notifications/ config/ library/ downloader/ visualizer/  # stubs vacíos, fases futuras
│   ├── interfaces/
│   │   ├── tui/app.py          # Implementado y probado (Textual)
│   │   └── gui/                # stub vacío, fase futura
│   └── di/container.py         # Wiring real de los dos adapters implementados
│
├── tests/                      # pytest: core/ (rápidos, sin I/O) + adapters/di/interfaces/ (audio real vía ffmpeg)
├── pytest.ini
├── requirements.txt             # dependencias de ejecución
├── requirements-dev.txt         # pytest + pytest-asyncio
│
├── music/                       # Música de ejemplo
├── CONCEPT.md                   # Concepto original (visión completa)
├── AGENT.md                     # Contexto para agentes IA — estado real actualizado aquí
├── SPEC.md                      # Especificación técnica completa (visión, no todo implementado)
├── README.md / README_EN.md
├── INDEX.md
└── LEARNING.md
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
> La conexión se hace en el ENTRY POINT (`__main__.py`).

## Tecnologías

| Componente | Tecnología | Estado |
|------------|------------|--------|
| Audio | pygame | Implementado |
| Metadatos | mutagen | Implementado |
| TUI | Textual | Implementado |
| Tests | pytest + pytest-asyncio | Implementado |
| GUI | CustomTkinter | Planeado |
| API | FastAPI | Planeado |
| BD | SQLite | Planeado |
| Descargas | yt-dlp | Planeado |
| Visualizer | numpy (FFT) | Planeado |
| i18n | gettext + Babel | Planeado |

## Formatos de Audio Soportados

- **Reproducción**: MP3, OGG, WAV, FLAC, M4A, WMA — todos vía pygame
- **Metadatos completos** (título/artista/álbum/pista): MP3, FLAC, OGG, Opus, M4A
- **Solo duración** (sin tags): WAV, WMA — ver el docstring de
  `adapters/metadata/mutagen_adapter.py` para el motivo

## Configuración

**No implementado todavía.** El volumen, modo de reproducción, shuffle y
última playlist se reinician a sus valores por defecto en cada ejecución.
Está planeado junto al adapter de biblioteca SQLite (ver AGENT.md).

## API Endpoints — no implementado, diseño futuro

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
| [AGENT.md](AGENT.md) | Contexto para agentes IA — estado real de implementación |
| [SPEC.md](SPEC.md) | Especificación técnica detallada (visión completa) |
| [README.md](README.md) | Esta documentación (ES) |
| [README_EN.md](README_EN.md) | Documentación (EN) |
| [INDEX.md](INDEX.md) | Índice de documentación |
| [LEARNING.md](LEARNING.md) | Guía de aprendizaje (ES) |

## Licencia

[MIT License](LICENSE)

## Autor

[HotGuy]
