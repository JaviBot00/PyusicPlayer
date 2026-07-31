# PyusicPlayer - Documentation Index

## Documentación Creada

| Fichero | Contenido | Idioma |
|---------|-----------|--------|
| **CONCEPT.md** | Concepto actualizado con todas las features del chat | EN |
| **AGENT.md** | Arquitectura completa, tech stack, estructura, API, DB schema | EN |
| **SPEC.md** | Especificación técnica detallada (requisitos, protocolos, endpoints) | EN |
| **README.md** | Documentación de usuario (instalación, uso, estructura) | ES |
| **README_EN.md** | User documentation (installation, usage, structure) | EN |
| **LEARNING.md** | Guía completa de aprendizaje (patrones, alternativas, código) | ES |
| **requirements.txt** | Dependencias del proyecto | - |

---

## Contenido de cada fichero

### CONCEPT.md
Concepto original del proyecto actualizado con todas las features discutidas:
- Player features (controls, modes, display, config)
- Download support (yt-dlp, opus format)
- Library management (SQLite, filters, collections)
- Interfaces (TUI, GUI, API)
- Requirements (architecture, cross-platform, interactions)
- Technology stack table

### AGENT.md
Contexto completo para agentes IA y desarrollo:
- Project overview
- Core features
- Architecture principles (Ports & Adapters)
- Dependency flow diagram
- Design patterns used
- Technology stack with rationale
- Project structure (full tree)
- API endpoints
- Database schema (SQL)
- Configuration schema (JSON)
- Dependencies list
- Key decisions table
- Implementation status

### SPEC.md
Especificación técnica detallada:
- Functional requirements (P0/P1/P2)
- Non-functional requirements
- Protocol definitions (Python code)
- API specification (endpoints, request/response)
- Database schema (SQL with indexes)
- Configuration schema (JSON)
- Dependencies (core, optional, dev)
- Testing strategy
- Deployment options
- Future considerations

### README.md
Documentación de usuario en español:
- Características
- Instalación (requisitos, dependencias)
- Uso (TUI, GUI, Server, combinado)
- Estructura del proyecto
- Arquitectura (puertos y adaptadores)
- Tecnologías
- Formatos de audio soportados
- Configuración (portable vs global)
- API endpoints
- Licencia

### README_EN.md
User documentation in English:
- Features
- Installation (requirements, dependencies)
- Usage (TUI, GUI, Server, combined)
- Project structure
- Architecture (Ports & Adapters)
- Technologies
- Supported audio formats
- Configuration (portable vs global)
- API endpoints
- License

### LEARNING.md
Guía de aprendizaje completa en español:
- Arquitectura modular (Ports & Adapters)
- Protocol Classes (typing)
- Dependency Injection
- Strategy Pattern
- Observer Pattern
- Async Programming (asyncio)
- Streaming de Audio (HTTP Range Requests)
- SQLite para Indexación
- Configuración Portable vs Global
- Internacionalización (i18n)
- Comparativa de Alternativas (pros/contras)
- Lecciones Aprendidas
- Recursos de Aprendizaje
- Glosario

### requirements.txt
Dependencias del proyecto organizadas por categoría:
- Core: pygame, mutagen
- TUI: textual
- GUI: customtkinter
- API: fastapi, uvicorn
- Audio: numpy
- Lyrics: httpx
- Download: yt-dlp
- i18n: babel

---

## Ficheros del Proyecto

```
PyusicPlayer/
├── main.py                    # Legacy entry point (to be replaced)
├── pyusicplayer/              # Código fuente
│   ├── __init__.py
│   ├── __main__.py            # Entry point (--tui, --gui, --server)
│   ├── core/                  # Business logic
│   │   ├── models.py          # Track, Playlist, PlaylistMode
│   │   ├── services.py        # PlayerService, LibraryService
│   │   └── ports/             # Protocol interfaces
│   │       ├── audio.py
│   │       ├── metadata.py
│   │       ├── lyrics.py
│   │       ├── notifications.py
│   │       ├── config.py
│   │       ├── library.py
│   │       ├── downloader.py
│   │       └── visualizer.py
│   ├── adapters/              # Concrete implementations
│   │   ├── audio/
│   │   │   └── pygame_adapter.py
│   │   └── metadata/
│   │       └── mutagen_adapter.py
│   ├── interfaces/            # UI layer
│   │   ├── tui/
│   │   └── gui/
│   ├── di/                    # Dependency Injection
│   │   └── container.py
│   └── i18n/                  # Internationalization
├── data/                      # Portable data (gitignored)
├── music/                     # Música de ejemplo
├── requirements.txt           # Dependencias
├── CONCEPT.md                 # Concepto original
├── AGENT.md                   # Contexto del agente
├── SPEC.md                    # Especificación técnica
├── README.md                  # Documentación (ES)
├── README_EN.md               # Documentation (EN)
├── LEARNING.md                # Guía de aprendizaje (ES)
├── INDEX.md                   # Este fichero
└── icon.png                   # Icono del proyecto
```
