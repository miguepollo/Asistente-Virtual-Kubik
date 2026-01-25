# Planning - Asistente Virtual Orange Pi 5 Ultra

## 📋 Resumen Ejecutivo

Asistente virtual de voz offline-first para Orange Pi 5 Ultra con IA local, wake word detection, integración APIs externas y webserver de configuración.

**Versión**: 1.0  
**Duración estimada**: 24-30 días  
**Complejidad**: Media-Alta  
**Nivel requerido**: Ninguno (automatizado por IA)

---

## 🎯 Especificaciones Técnicas Detalladas

### Hardware Completo
- **Placa**: Orange Pi 5 Ultra
  - **SoC**: Rockchip RK3588 (8 cores: 4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz)
  - **NPU**: 6 TOPS (triple NPU de 0.8T + 1.0T + 1.8T)
  - **RAM**: 16GB LPDDR4X
  - **Almacenamiento**: NVMe SSD
  - **GPU**: Mali-G610 MP4
- **OS**: Armbian (Debian-based)
- **Audio Input**: Micrófono integrado de la placa
  - Codec: ES8388
  - Canales: Mono (para STT)
  - Sample Rate: 16kHz
  - Bit Depth: 16-bit
- **Audio Output**: Jack 3.5mm
  - Compatible: Altavoces pasivos, auriculares
  - Amplificación: vía ALSA/PulseAudio
- **Sin componentes adicionales**: LEDs, botones, pantallas (fase inicial)

### Stack Tecnológico Completo

#### Core AI Components
| Componente | Tecnología | Versión | Propósito | Características |
|------------|------------|---------|-----------|-----------------|
| **LLM** | rkllama | Latest | Conversación | NPU-accelerated, GGUF support |
| **STT** | Vosk | 0.3.45 | Speech-to-Text | Offline, español, ligero |
| **TTS** | Piper | 1.2.0 | Text-to-Speech | Natural, bajo latencia |
| **Wake Word** | Porcupine | 2.2.0 | Hotword Detection | Custom wake words |
| **VAD** | WebRTC VAD | 2.0.10 | Voice Activity | Silence detection |

#### Backend Stack
| Componente | Tecnología | Versión | Propósito |
|------------|------------|---------|-----------|
| **Runtime** | Python | 3.10+ | Lenguaje principal |
| **Web Framework** | Flask | 3.0.0 | API REST + UI |
| **Audio** | PyAudio | 0.2.13 | Audio I/O |
| **HTTP Client** | Requests | 2.31.0 | API calls |
| **Encryption** | Cryptography | 41.0.7 | API key security |
| **Service** | systemd | Native | Daemon management |
| **Networking** | NetworkManager | Native | WiFi/AP control |

#### Integraciones Externas
| Servicio | Fase | Propósito | Autenticación |
|----------|------|-----------|---------------|
| **OpenWeatherMap** | 1 | Clima y previsión | API Key |
| **NTP** | 1 | Sincronización horaria | Público |
| **Spotify** | 2 | Control playback | OAuth 2.0 |
| **Google Calendar** | 3 | Eventos/recordatorios | OAuth 2.0 |
| **IFTTT** | 3 | Automatización | Webhooks |
| **Home Assistant** | 3 | Domótica | MQTT/REST |

---

## 🏗️ Arquitectura del Sistema Extendida

### Diagrama de Arquitectura Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Orange Pi 5 Ultra (Armbian)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      AUDIO PIPELINE LAYER                            │  │
│  │  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐       │  │
│  │  │  Hardware    │─────▶│ ALSA Driver  │─────▶│  PyAudio     │       │  │
│  │  │  Mic (ES8388)│      │              │      │  Wrapper     │       │  │
│  │  └──────────────┘      └──────────────┘      └──────┬───────┘       │  │
│  │                                                      │                │  │
│  │                        ┌─────────────────────────────┘                │  │
│  │                        ▼                                              │  │
│  │              ┌──────────────────┐                                     │  │
│  │              │  Audio Buffer    │                                     │  │
│  │              │  (Circular)      │                                     │  │
│  │              │  16kHz, Mono     │                                     │  │
│  │              └────────┬─────────┘                                     │  │
│  └───────────────────────┼──────────────────────────────────────────────┘  │
│                          │                                                 │
│  ┌───────────────────────┼──────────────────────────────────────────────┐  │
│  │             WAKE WORD DETECTION LAYER                │                │  │
│  │                       ▼                              │                │  │
│  │         ┌──────────────────────────┐                 │                │  │
│  │         │   Porcupine Engine       │                 │                │  │
│  │         │   - Custom "Asistente"   │                 │                │  │
│  │         │   - Low CPU (<5%)        │                 │                │  │
│  │         │   - Sensitivity: 0.5     │                 │                │  │
│  │         └──────────┬───────────────┘                 │                │  │
│  │                    │ Wake Word                       │                │  │
│  │                    │ Detected?                       │                │  │
│  │                    ▼                                 │                │  │
│  │         ┌──────────────────────────┐                 │                │  │
│  │         │  Trigger Audio Capture   │                 │                │  │
│  │         └──────────┬───────────────┘                 │                │  │
│  └────────────────────┼──────────────────────────────────────────────────┘  │
│                       │                                                     │
│  ┌────────────────────┼──────────────────────────────────────────────────┐  │
│  │          SPEECH RECOGNITION LAYER                    │                │  │
│  │                    ▼                                 │                │  │
│  │      ┌──────────────────────────────┐                │                │  │
│  │      │   VAD (Voice Activity)       │                │                │  │
│  │      │   - WebRTC VAD               │                │                │  │
│  │      │   - Silence timeout: 2s      │                │                │  │
│  │      │   - Aggressiveness: 3        │                │                │  │
│  │      └──────────┬───────────────────┘                │                │  │
│  │                 │ Speech Detected                    │                │  │
│  │                 ▼                                    │                │  │
│  │      ┌──────────────────────────────┐                │                │  │
│  │      │   Vosk STT Engine            │                │                │  │
│  │      │   - Model: es-small-0.42     │                │                │  │
│  │      │   - Offline processing       │                │                │  │
│  │      │   - Latency: <500ms          │                │                │  │
│  │      └──────────┬───────────────────┘                │                │  │
│  │                 │ Transcribed Text                   │                │  │
│  └─────────────────┼──────────────────────────────────────────────────────┘  │
│                    │                                                        │
│  ┌─────────────────┼──────────────────────────────────────────────────────┐ │
│  │        NATURAL LANGUAGE UNDERSTANDING LAYER          │                │ │
│  │                 ▼                                    │                │ │
│  │   ┌──────────────────────────────────┐               │                │ │
│  │   │   Intent Classifier              │               │                │ │
│  │   │   - Pattern matching             │               │                │ │
│  │   │   - Keyword detection            │               │                │ │
│  │   │   - Context awareness            │               │                │ │
│  │   └──────────┬───────────────────────┘               │                │ │
│  │              │                                       │                │ │
│  │    ┌─────────┴─────────┬──────────────┬─────────────┤                │ │
│  │    ▼                   ▼              ▼             ▼                │ │
│  │ ┌────────┐      ┌────────────┐  ┌─────────┐  ┌──────────┐          │ │
│  │ │System  │      │   API      │  │  LLM    │  │ Unknown  │          │ │
│  │ │Commands│      │  Handlers  │  │  Query  │  │  Intent  │          │ │
│  │ └───┬────┘      └─────┬──────┘  └────┬────┘  └─────┬────┘          │ │
│  └─────┼──────────────────┼──────────────┼─────────────┼───────────────┘ │
│        │                  │              │             │                  │
│  ┌─────┼──────────────────┼──────────────┼─────────────┼───────────────┐ │
│  │     │    EXECUTION LAYER              │             │               │ │
│  │     │                  │              │             │               │ │
│  │     ▼                  ▼              ▼             ▼               │ │
│  │ ┌────────────┐  ┌──────────────┐  ┌─────────────────────┐          │ │
│  │ │ Time       │  │ OWM API      │  │   rkllama LLM       │          │ │
│  │ │ Volume     │  │ - Weather    │  │   - NPU Accel       │          │ │
│  │ │ System     │  │ - Forecast   │  │   - Model: 1-3B/7B  │          │ │
│  │ │ Info       │  │ NTP          │  │   - Context: 60s    │          │ │
│  │ └─────┬──────┘  └──────┬───────┘  └──────────┬──────────┘          │ │
│  │       │                │                     │                      │ │
│  │       └────────────────┴─────────────────────┘                      │ │
│  │                        │                                            │ │
│  │                        ▼                                            │ │
│  │              ┌──────────────────────┐                               │ │
│  │              │  Response Generator  │                               │ │
│  │              │  - Format text       │                               │ │
│  │              │  - Add context       │                               │ │
│  │              │  - Error handling    │                               │ │
│  │              └──────────┬───────────┘                               │ │
│  └──────────────────────────┼──────────────────────────────────────────┘ │
│                             │                                            │
│  ┌──────────────────────────┼──────────────────────────────────────────┐ │
│  │         TEXT-TO-SPEECH LAYER                         │              │ │
│  │                          ▼                           │              │ │
│  │              ┌──────────────────────┐                │              │ │
│  │              │   Piper TTS Engine   │                │              │ │
│  │              │   - Voice: davefx    │                │              │ │
│  │              │   - Lang: es_ES      │                │              │ │
│  │              │   - Quality: medium  │                │              │ │
│  │              │   - Latency: <300ms  │                │              │ │
│  │              └──────────┬───────────┘                │              │ │
│  │                         │ WAV file                   │              │ │
│  │                         ▼                            │              │ │
│  │              ┌──────────────────────┐                │              │ │
│  │              │  Audio Playback      │                │              │ │
│  │              │  - ALSA/PulseAudio   │                │              │ │
│  │              │  - Volume control    │                │              │ │
│  │              │  - Jack 3.5mm out    │                │              │ │
│  │              └──────────────────────┘                │              │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    CONTEXT & MEMORY LAYER                           │ │
│  │  ┌──────────────────────┐      ┌──────────────────────┐             │ │
│  │  │ Context Manager      │      │ Conversation History │             │ │
│  │  │ - Active: 60s        │      │ - Last 5 convs       │             │ │
│  │  │ - Auto-clear timeout │      │ - Persistent JSON    │             │ │
│  │  └──────────────────────┘      └──────────────────────┘             │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │              WEB SERVER & CONFIGURATION LAYER                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  Flask Web Application (Port 5000)                           │   │ │
│  │  │                                                               │   │ │
│  │  │  Routes:                                                      │   │ │
│  │  │  - GET  /           → Dashboard                              │   │ │
│  │  │  - GET  /config     → Configuration page                     │   │ │
│  │  │  - POST /api/config → Save settings                          │   │ │
│  │  │  - GET  /api/models → List available models                  │   │ │
│  │  │  - POST /api/models/download → Download model                │   │ │
│  │  │  - GET  /api/wifi   → WiFi networks                          │   │ │
│  │  │  - POST /api/wifi   → Connect to network                     │   │ │
│  │  │  - GET  /api/logs   → View logs                              │   │ │
│  │  │  - GET  /api/stats  → System statistics                      │   │ │
│  │  │  - POST /api/test   → Test voice pipeline                    │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  WiFi AP Manager                                             │   │ │
│  │  │  - SSID: Asistente-Config (open)                             │   │ │
│  │  │  - IP: 192.168.12.1                                          │   │ │
│  │  │  - DHCP: 192.168.12.100-200                                  │   │ │
│  │  │  - Auto-start on boot                                        │   │ │
│  │  │  - Graceful shutdown when connected to WiFi                  │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    SYSTEM SERVICES LAYER                            │ │
│  │  ┌──────────────────────┐      ┌──────────────────────┐             │ │
│  │  │ systemd Service      │      │ Logging System       │             │ │
│  │  │ - Auto-start         │      │ - Rotating logs      │             │ │
│  │  │ - Auto-restart       │      │ - Debug/Info modes   │             │ │
│  │  │ - Dependency mgmt    │      │ - 10MB max per file  │             │ │
│  │  └──────────────────────┘      └──────────────────────┘             │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘

         ▲                                    ▲
         │                                    │
    ┌────┴─────┐                         ┌───┴────┐
    │ Internet │                         │  User  │
    │ (APIs)   │                         │  Voice │
    └──────────┘                         └────────┘
```

### Flujo de Datos Detallado

```
1. IDLE STATE
   │
   ├─▶ [Continuously] Buffer audio chunks → Porcupine
   │
   └─▶ Wake word "Asistente" detected?
       │
       │ NO → Continue buffering
       │
       │ YES
       ▼
2. LISTENING STATE
   │
   ├─▶ [Feedback] (opcional: beep o LED)
   │
   ├─▶ Capture audio stream
   │
   ├─▶ VAD monitors speech activity
   │   │
   │   ├─▶ Speech detected → Continue recording
   │   │
   │   └─▶ Silence > 2s → Stop recording
   │
   └─▶ Audio buffer complete
       │
       ▼
3. TRANSCRIPTION STATE
   │
   ├─▶ Send audio to Vosk STT
   │
   ├─▶ Get transcribed text
   │
   └─▶ Text empty?
       │
       │ YES → Respond "No te he entendido" → IDLE
       │
       │ NO
       ▼
4. INTENT PROCESSING STATE
   │
   ├─▶ Classify intent (pattern matching)
   │   │
   │   ├─▶ System command? (time, volume, etc)
   │   │   └─▶ Execute → Get response → SYNTHESIS
   │   │
   │   ├─▶ API query? (weather, forecast)
   │   │   ├─▶ Check internet connectivity
   │   │   │   │
   │   │   │   ├─▶ Online → Call API → Get response → SYNTHESIS
   │   │   │   │
   │   │   │   └─▶ Offline → "Servicios no disponibles" → SYNTHESIS
   │   │   │
   │   │
   │   └─▶ General query?
   │       └─▶ Send to LLM → Get response → SYNTHESIS
   │
   └─▶ Update conversation context
       │
       ▼
5. SYNTHESIS STATE
   │
   ├─▶ Send text to Piper TTS
   │
   ├─▶ Generate WAV file
   │
   ├─▶ Play audio via ALSA
   │
   └─▶ Playback complete
       │
       ▼
6. CONTEXT MANAGEMENT
   │
   ├─▶ Save conversation to history
   │
   ├─▶ Start 60s context timeout timer
   │
   └─▶ Return to IDLE STATE
       │
       └─▶ If new wake word within 60s → Maintain context
           │
           └─▶ If timeout → Clear context
```

---

## 📁 Estructura de Directorios Completa

```
/home/orangepi/asistente/
│
├── config/                          # Configuración
│   ├── config.json                  # Config principal
│   ├── api_keys.json                # API keys (encriptado)
│   ├── network.json                 # WiFi credentials
│   ├── models.json                  # Model metadata
│   └── backup/                      # Backups automáticos
│       ├── config.json.2024-01-25
│       └── api_keys.json.2024-01-25
│
├── models/                          # Modelos AI
│   ├── llm/
│   │   ├── phi-2-1.3b-q4.gguf      # Modelo pequeño (pruebas)
│   │   ├── mistral-7b-q4.gguf      # Modelo producción
│   │   ├── llama3-8b-q5.gguf       # Modelo alternativo
│   │   └── metadata.json           # Info modelos
│   │
│   ├── stt/
│   │   ├── vosk-model-small-es-0.42/
│   │   │   ├── am/
│   │   │   ├── conf/
│   │   │   ├── graph/
│   │   │   └── ivector/
│   │   └── vosk-model-es-0.42/     # Modelo grande (opcional)
│   │
│   ├── tts/
│   │   ├── es_ES-davefx-medium.onnx
│   │   ├── es_ES-davefx-medium.onnx.json
│   │   ├── en_US-lessac-medium.onnx    # Inglés (fase 2)
│   │   └── en_US-lessac-medium.onnx.json
│   │
│   └── wakeword/
│       ├── asistente_es.ppn        # Wake word español
│       ├── assistant_en.ppn        # Wake word inglés
│       └── params.json             # Parámetros sensibilidad
│
├── src/                             # Código fuente
│   ├── __init__.py
│   ├── main.py                      # Entry point principal
│   │
│   ├── audio/                       # Gestión de audio
│   │   ├── __init__.py
│   │   ├── capture.py               # Captura micrófono
│   │   ├── playback.py              # Reproducción altavoz
│   │   ├── vad.py                   # Voice Activity Detection
│   │   ├── processor.py             # Audio preprocessing
│   │   └── devices.py               # Device enumeration
│   │
│   ├── engines/                     # Motores AI
│   │   ├── __init__.py
│   │   ├── wakeword.py              # Porcupine wrapper
│   │   ├── stt.py                   # Vosk wrapper
│   │   ├── tts.py                   # Piper wrapper
│   │   ├── llm.py                   # rkllama wrapper
│   │   └── benchmarks.py            # Performance testing
│   │
│   ├── intents/                     # Procesamiento intents
│   │   ├── __init__.py
│   │   ├── processor.py             # Intent classifier
│   │   ├── commands.py              # System commands
│   │   ├── apis.py                  # API handlers
│   │   ├── patterns.py              # Pattern matchers
│   │   └── plugins/                 # Extensible plugins
│   │       ├── __init__.py
│   │       ├── weather.py
│   │       ├── calendar.py
│   │       └── spotify.py
│   │
│   ├── context/                     # Gestión contexto
│   │   ├── __init__.py
│   │   ├── manager.py               # Context window manager
│   │   ├── history.py               # Conversation history
│   │   └── state.py                 # State machine
│   │
│   ├── webserver/                   # Flask web app
│   │   ├── __init__.py
│   │   ├── app.py                   # Flask application
│   │   │
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Config endpoints
│   │   │   ├── models.py            # Model management
│   │   │   ├── wifi.py              # WiFi management
│   │   │   ├── logs.py              # Log viewer
│   │   │   ├── stats.py             # Statistics
│   │   │   └── test.py              # Testing endpoints
│   │   │
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── index.html           # Dashboard
│   │   │   ├── config.html          # Configuration
│   │   │   ├── models.html          # Model downloader
│   │   │   ├── wifi.html            # WiFi setup
│   │   │   ├── logs.html            # Log viewer
│   │   │   ├── stats.html           # Statistics
│   │   │   └── test.html            # Test interface
│   │   │
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   ├── main.css
│   │   │   │   └── bootstrap.min.css
│   │   │   ├── js/
│   │   │   │   ├── main.js
│   │   │   │   ├── config.js
│   │   │   │   └── models.js
│   │   │   └── img/
│   │   │       ├── logo.png
│   │   │       └── favicon.ico
│   │   │
│   │   └── api/                     # API utilities
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── validators.py
│   │       └── responses.py
│   │
│   └── utils/                       # Utilidades
│       ├── __init__.py
│       ├── logger.py                # Logging setup
│       ├── network.py               # WiFi AP manager
│       ├── crypto.py                # Encryption/decryption
│       ├── config_loader.py         # Config management
│       ├── model_manager.py         # Model downloader
│       ├── system_info.py           # System metrics
│       └── validators.py            # Input validation
│
├── logs/                            # Logs
│   ├── assistant.log                # Main log
│   ├── debug.log                    # Debug log
│   ├── web.log                      # Web server log
│   ├── errors.log                   # Errors only
│   └── archive/                     # Rotated logs
│       ├── assistant.log.1
│       └── assistant.log.2
│
├── scripts/                         # Scripts utilidad
│   ├── install.sh                   # Instalación completa
│   ├── download_models.sh           # Descarga modelos
│   ├── setup_audio.sh               # Configurar audio
│   ├── setup_ap.sh                  # Configurar AP
│   ├── test_pipeline.sh             # Test completo
│   ├── benchmark.sh                 # Performance test
│   ├── backup.sh                    # Backup config
│   └── restore.sh                   # Restore config
│
├── tests/                           # Tests unitarios
│   ├── __init__.py
│   ├── test_audio.py
│   ├── test_stt.py
│   ├── test_tts.py
│   ├── test_llm.py
│   ├── test_intents.py
│   ├── test_webserver.py
│   └── test_integration.py
│
├── systemd/                         # Systemd services
│   ├── asistente.service            # Main service
│   ├── asistente-web.service        # Web server service
│   └── asistente-ap.service         # WiFi AP service
│
├── docs/                            # Documentación
│   ├── API.md                       # API reference
│   ├── ARCHITECTURE.md              # Arquitectura
│   ├── TROUBLESHOOTING.md           # Solución problemas
│   ├── CONTRIBUTING.md              # Guía contribución
│   └── CHANGELOG.md                 # Historial cambios
│
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Dev dependencies
├── setup.py                         # Package setup
├── .env.example                     # Environment template
├── .gitignore
├── LICENSE
└── README.md                        # Documentación principal
```

---

## 🚀 Fases de Desarrollo Extendidas

### **FASE 0: Setup Inicial y Preparación del Entorno** (Días 1-2)

**Objetivo**: Preparar completamente el Orange Pi 5 Ultra con todas las dependencias y herramientas necesarias.

#### Subtareas Detalladas

##### 0.1: Actualización y Configuración del Sistema

```bash
# Actualizar sistema completo
sudo apt update && sudo apt upgrade -y
sudo apt dist-upgrade -y

# Instalar herramientas básicas
sudo apt install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    unzip \
    vim \
    htop \
    tmux \
    screen

# Instalar Python y desarrollo
sudo apt install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3-venv \
    python3-setuptools \
    python3-wheel

# Verificar versión Python
python3 --version  # Debe ser 3.10+
```

##### 0.2: Dependencias de Audio

```bash
# ALSA (Advanced Linux Sound Architecture)
sudo apt install -y \
    alsa-utils \
    alsa-tools \
    libasound2 \
    libasound2-dev \
    libasound2-plugins

# PulseAudio
sudo apt install -y \
    pulseaudio \
    pulseaudio-utils \
    pavucontrol

# PortAudio (para PyAudio)
sudo apt install -y \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0

# Configurar tarjeta de audio ES8388
sudo nano /etc/asound.conf
```

**Contenido /etc/asound.conf**:
```conf
pcm.!default {
    type asym
    playback.pcm "playback"
    capture.pcm "capture"
}

pcm.playback {
    type plug
    slave.pcm "hw:0,0"
}

pcm.capture {
    type plug
    slave.pcm "hw:0,0"
}

ctl.!default {
    type hw
    card 0
}
```

##### 0.3: Verificación de Audio

```bash
# Listar dispositivos de audio
arecord -l
# Esperado:
# card 0: rockchipes8388c [rockchip-es8388], device 0: ...

aplay -l
# Esperado:
# card 0: rockchipes8388c [rockchip-es8388], device 0: ...

# Test grabación (5 segundos)
arecord -D hw:0,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav

# Test reproducción
aplay test.wav

# Ajustar volumen
alsamixer
# F6 para seleccionar tarjeta
# F4 para captura
# Flechas para ajustar
```

##### 0.4: Instalación rkllm SDK

```bash
# Clonar repositorio oficial
cd ~
git clone https://github.com/airockchip/rknn-llm
cd rknn-llm

# Instalar dependencias
sudo apt install -y \
    libopencv-dev \
    python3-opencv

# Compilar para RK3588
cd rknn-llm/runtime/Linux/
mkdir build && cd build
cmake ..
make -j8

# Instalar
sudo make install
sudo ldconfig

# Verificar instalación
python3 -c "import rkllm; print(rkllm.__version__)"
```

##### 0.5: Estructura de Directorios

```bash
# Crear estructura completa
mkdir -p ~/asistente/{config,models/{llm,stt,tts,wakeword},src/{audio,engines,intents,context,webserver/{routes,templates,static/{css,js,img}},utils},logs/{archive},scripts,tests,systemd,docs}

# Verificar estructura
tree -L 3 ~/asistente

# Crear entorno virtual Python
cd ~/asistente
python3 -m venv venv

# Activar entorno
source venv/bin/activate

# Actualizar pip
pip install --upgrade pip setuptools wheel
```

##### 0.6: Instalación Dependencias Python Base

```bash
# Crear requirements.txt
cat > requirements.txt << 'EOF'
# Core
pyaudio==0.2.13
numpy==1.24.3
scipy==1.10.1

# AI Engines
pvporcupine==2.2.0
vosk==0.3.45
# piper-tts se instala como binario

# Web
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0

# Utils
python-dotenv==1.0.0
pyyaml==6.0.1
cryptography==41.0.7
webrtcvad==2.0.10
pydub==0.25.1

# Networking
netifaces==0.11.0
python-wifi==0.6.1

# Logging
colorlog==6.7.0

# Testing (opcional)
pytest==7.4.0
pytest-cov==4.1.0
EOF

# Instalar todas las dependencias
pip install -r requirements.txt
```

##### 0.7: Configuración NetworkManager para WiFi AP

```bash
# Instalar NetworkManager
sudo apt install -y \
    network-manager \
    dnsmasq \
    hostapd

# Deshabilitar servicios conflictivos
sudo systemctl stop wpa_supplicant
sudo systemctl disable wpa_supplicant
sudo systemctl mask wpa_supplicant

# Habilitar NetworkManager
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager

# Verificar
nmcli device status
```

##### 0.8: Configuración Git (opcional)

```bash
# Si quieres versionar tu código
cd ~/asistente
git init
git config user.name "Tu Nombre"
git config user.email "tu@email.com"

# Crear .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
*.so

# Config files con credenciales
config/api_keys.json
config/network.json
.env

# Logs
logs/
*.log

# Modelos (muy grandes)
models/

# OS
.DS_Store
Thumbs.db
EOF

git add .gitignore
git commit -m "Initial commit"
```

**Criterios de Éxito Fase 0**:
- ✅ Python 3.10+ instalado y funcional
- ✅ Audio input/output verificado con arecord/aplay
- ✅ rkllm importable desde Python
- ✅ Entorno virtual creado
- ✅ Todas las dependencias instaladas sin errores
- ✅ NetworkManager funcionando
- ✅ Estructura de directorios completa

---

### **FASE 1: Audio Pipeline Básico** (Días 3-4)

**Objetivo**: Implementar captura y reproducción de audio con buffers eficientes y baja latencia.

#### Subtareas Detalladas

##### 1.1: Implementar Audio Capture Module

**Archivo**: `src/audio/capture.py`

```python
"""
Audio Capture Module
Gestiona la captura de audio desde el micrófono con buffer circular.
"""

import pyaudio
import numpy as np
import threading
import queue
from collections import deque
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class AudioCapture:
    """Captura audio del micrófono con buffer circular."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 512,
        device_index: Optional[int] = None,
        buffer_duration: float = 5.0  # segundos
    ):
        """
        Args:
            sample_rate: Frecuencia de muestreo (Hz)
            channels: Número de canales (1=mono, 2=estéreo)
            chunk_size: Tamaño del chunk de audio
            device_index: Índice del dispositivo (None=default)
            buffer_duration: Duración del buffer circular (segundos)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        
        # Buffer circular
        buffer_size = int(sample_rate * buffer_duration)
        self.buffer = deque(maxlen=buffer_size)
        self.buffer_lock = threading.Lock()
        
        # PyAudio setup
        self.p = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_running = False
        
        # Thread de captura
        self.capture_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.callbacks: list[Callable] = []
        
        logger.info(
            f"AudioCapture initialized: {sample_rate}Hz, "
            f"{channels}ch, chunk={chunk_size}"
        )
    
    def start(self) -> None:
        """Inicia la captura de audio."""
        if self.is_running:
            logger.warning("Audio capture already running")
            return
        
        try:
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.is_running = True
            self.stream.start_stream()
            logger.info("Audio capture started")
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            raise
    
    def stop(self) -> None:
        """Detiene la captura de audio."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        logger.info("Audio capture stopped")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback interno de PyAudio."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # Convertir a numpy array
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        
        # Añadir al buffer circular
        with self.buffer_lock:
            self.buffer.extend(audio_data)
        
        # Llamar callbacks registrados
        for callback in self.callbacks:
            try:
                callback(audio_data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        return (None, pyaudio.paContinue)
    
    def register_callback(self, callback: Callable) -> None:
        """Registra un callback para procesar audio en tiempo real."""
        self.callbacks.append(callback)
    
    def get_buffer(self, duration: Optional[float] = None) -> np.ndarray:
        """
        Obtiene audio del buffer.
        
        Args:
            duration: Duración en segundos (None=todo el buffer)
        
        Returns:
            Array de audio
        """
        with self.buffer_lock:
            if duration is None:
                return np.array(self.buffer, dtype=np.int16)
            else:
                samples = int(self.sample_rate * duration)
                samples = min(samples, len(self.buffer))
                return np.array(list(self.buffer)[-samples:], dtype=np.int16)
    
    def clear_buffer(self) -> None:
        """Limpia el buffer circular."""
        with self.buffer_lock:
            self.buffer.clear()
    
    def get_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Obtiene un chunk de audio (bloqueante).
        
        Args:
            timeout: Tiempo máximo de espera
        
        Returns:
            Chunk de audio o None si timeout
        """
        # Para uso síncrono, capturar directamente
        if not self.is_running:
            self.start()
        
        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            return np.frombuffer(data, dtype=np.int16)
        except Exception as e:
            logger.error(f"Error reading audio chunk: {e}")
            return None
    
    def list_devices(self) -> list[dict]:
        """Lista todos los dispositivos de audio disponibles."""
        devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # Solo dispositivos de entrada
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })
        return devices
    
    def __del__(self):
        """Cleanup al destruir el objeto."""
        self.stop()
        self.p.terminate()


# Test del módulo
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Listar dispositivos
    capture = AudioCapture()
    print("\nDispositivos de audio disponibles:")
    for device in capture.list_devices():
        print(f"  [{device['index']}] {device['name']} "
              f"({device['channels']}ch @ {device['sample_rate']}Hz)")
    
    # Test captura
    print("\nIniciando captura de 5 segundos...")
    capture.start()
    
    import time
    time.sleep(5)
    
    # Obtener buffer
    audio_data = capture.get_buffer(duration=5.0)
    print(f"Capturados {len(audio_data)} samples "
          f"({len(audio_data)/capture.sample_rate:.2f}s)")
    
    capture.stop()
```

##### 1.2: Implementar Audio Playback Module

**Archivo**: `src/audio/playback.py`

```python
"""
Audio Playback Module
Gestiona la reproducción de audio por el altavoz.
"""

import pyaudio
import wave
import subprocess
import logging
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class AudioPlayback:
    """Reproduce audio por el altavoz con control de volumen."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device_index: Optional[int] = None
    ):
        """
        Args:
            sample_rate: Frecuencia de muestreo
            channels: Número de canales
            device_index: Índice del dispositivo de salida
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        
        self.p = pyaudio.PyAudio()
        self.current_stream: Optional[pyaudio.Stream] = None
        
        logger.info(f"AudioPlayback initialized: {sample_rate}Hz, {channels}ch")
    
    def play_wav(self, filepath: str, blocking: bool = True) -> None:
        """
        Reproduce un archivo WAV.
        
        Args:
            filepath: Ruta al archivo WAV
            blocking: Si True, espera a que termine la reproducción
        """
        try:
            # Abrir archivo WAV
            wf = wave.open(filepath, 'rb')
            
            # Crear stream
            stream = self.p.open(
                format=self.p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
                output_device_index=self.device_index
            )
            
            self.current_stream = stream
            
            # Reproducir
            chunk_size = 1024
            data = wf.readframes(chunk_size)
            
            while data:
                stream.write(data)
                data = wf.readframes(chunk_size)
            
            if blocking:
                stream.stop_stream()
                stream.close()
                self.current_stream = None
            
            wf.close()
            logger.debug(f"Played audio file: {filepath}")
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            raise
    
    def play_array(
        self,
        audio_data: np.ndarray,
        sample_rate: Optional[int] = None,
        blocking: bool = True
    ) -> None:
        """
        Reproduce audio desde un numpy array.
        
        Args:
            audio_data: Array de audio (int16)
            sample_rate: Frecuencia de muestreo (None=usar default)
            blocking: Si True, espera a que termine
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        try:
            stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=sample_rate,
                output=True,
                output_device_index=self.device_index
            )
            
            # Convertir a bytes
            audio_bytes = audio_data.astype(np.int16).tobytes()
            
            stream.write(audio_bytes)
            
            if blocking:
                stream.stop_stream()
                stream.close()
            
            logger.debug(f"Played audio array: {len(audio_data)} samples")
            
        except Exception as e:
            logger.error(f"Error playing array: {e}")
            raise
    
    def stop(self) -> None:
        """Detiene la reproducción actual."""
        if self.current_stream:
            self.current_stream.stop_stream()
            self.current_stream.close()
            self.current_stream = None
    
    def set_volume(self, level: int) -> None:
        """
        Ajusta el volumen del sistema.
        
        Args:
            level: Nivel de volumen (0-100)
        """
        level = max(0, min(100, level))  # Clamp 0-100
        
        try:
            # Usando amixer
            subprocess.run(
                ['amixer', 'sset', 'Master', f'{level}%'],
                check=True,
                capture_output=True
            )
            logger.info(f"Volume set to {level}%")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error setting volume: {e}")
    
    def get_volume(self) -> int:
        """
        Obtiene el volumen actual del sistema.
        
        Returns:
            Nivel de volumen (0-100)
        """
        try:
            result = subprocess.run(
                ['amixer', 'get', 'Master'],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Parsear output (formato: [XX%])
            import re
            match = re.search(r'\[(\d+)%\]', result.stdout)
            if match:
                return int(match.group(1))
            
            return 50  # Default
            
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return 50
    
    def volume_up(self, step: int = 10) -> None:
        """Sube el volumen."""
        current = self.get_volume()
        self.set_volume(current + step)
    
    def volume_down(self, step: int = 10) -> None:
        """Baja el volumen."""
        current = self.get_volume()
        self.set_volume(current - step)
    
    def list_devices(self) -> list[dict]:
        """Lista dispositivos de salida disponibles."""
        devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxOutputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })
        return devices
    
    def __del__(self):
        """Cleanup."""
        self.stop()
        self.p.terminate()


# Test del módulo
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    playback = AudioPlayback()
    
    # Listar dispositivos
    print("\nDispositivos de salida disponibles:")
    for device in playback.list_devices():
        print(f"  [{device['index']}] {device['name']}")
    
    # Test volumen
    print(f"\nVolumen actual: {playback.get_volume()}%")
    playback.set_volume(50)
    print(f"Volumen ajustado a: {playback.get_volume()}%")
    
    # Test reproducción (genera un tono de prueba)
    print("\nGenerando tono de prueba...")
    duration = 2.0
    frequency = 440.0  # La (A4)
    
    t = np.linspace(0, duration, int(16000 * duration))
    audio = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.3).astype(np.int16)
    
    print("Reproduciendo tono...")
    playback.play_array(audio)
    print("¡Hecho!")
```

##### 1.3: Implementar Voice Activity Detection (VAD)

**Archivo**: `src/audio/vad.py`

```python
"""
Voice Activity Detection Module
Detecta cuando hay voz activa y cuándo hay silencio.
"""

import webrtcvad
import numpy as np
import logging
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class VAD:
    """Voice Activity Detection usando WebRTC VAD."""
    
    # Duraciones de frame válidas para WebRTC VAD (ms)
    VALID_FRAME_DURATIONS = [10, 20, 30]
    
    def __init__(
        self,
        sample_rate: int = 16000,
        aggressiveness: int = 3,
        frame_duration_ms: int = 30,
        silence_duration: float = 2.0
    ):
        """
        Args:
            sample_rate: Frecuencia de muestreo (8000, 16000, 32000, 48000)
            aggressiveness: Nivel de agresividad (0-3, mayor=más estricto)
            frame_duration_ms: Duración del frame (10, 20, 30 ms)
            silence_duration: Duración de silencio para considerar fin (s)
        """
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Invalid sample rate: {sample_rate}")
        
        if frame_duration_ms not in self.VALID_FRAME_DURATIONS:
            raise ValueError(f"Invalid frame duration: {frame_duration_ms}")
        
        if not 0 <= aggressiveness <= 3:
            raise ValueError(f"Invalid aggressiveness: {aggressiveness}")
        
        self.sample_rate = sample_rate
        self.aggressiveness = aggressiveness
        self.frame_duration_ms = frame_duration_ms
        self.silence_duration = silence_duration
        
        # Calcular tamaño de frame en samples
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # WebRTC VAD instance
        self.vad = webrtcvad.Vad(aggressiveness)
        
        # Estado
        self.speech_frames = 0
        self.silence_frames = 0
        self.silence_threshold = int(
            (silence_duration * 1000) / frame_duration_ms
        )
        
        logger.info(
            f"VAD initialized: {sample_rate}Hz, aggressiveness={aggressiveness}, "
            f"frame={frame_duration_ms}ms, silence_threshold={self.silence_threshold} frames"
        )
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Detecta si el chunk de audio contiene voz.
        
        Args:
            audio_chunk: Array de audio (int16)
        
        Returns:
            True si detecta voz, False si es silencio
        """
        # Asegurar que el chunk tiene el tamaño correcto
        if len(audio_chunk) != self.frame_size:
            # Rellenar con ceros si es necesario
            if len(audio_chunk) < self.frame_size:
                audio_chunk = np.pad(
                    audio_chunk,
                    (0, self.frame_size - len(audio_chunk)),
                    'constant'
                )
            else:
                audio_chunk = audio_chunk[:self.frame_size]
        
        # Convertir a bytes
        audio_bytes = audio_chunk.astype(np.int16).tobytes()
        
        try:
            return self.vad.is_speech(audio_bytes, self.sample_rate)
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False
    
    def detect_speech_end(self, audio_chunk: np.ndarray) -> bool:
        """
        Detecta si ha terminado la voz (silencio prolongado).
        
        Args:
            audio_chunk: Array de audio
        
        Returns:
            True si detecta fin de voz
        """
        is_speech = self.is_speech(audio_chunk)
        
        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1
        
        # Fin de voz: hubo voz antes y ahora silencio prolongado
        if self.speech_frames > 0 and self.silence_frames >= self.silence_threshold:
            self.reset()
            return True
        
        return False
    
    def reset(self) -> None:
        """Resetea el estado del detector."""
        self.speech_frames = 0
        self.silence_frames = 0
    
    def process_stream(
        self,
        audio_stream: np.ndarray,
        return_chunks: bool = False
    ) -> tuple[bool, Optional[list[np.ndarray]]]:
        """
        Procesa un stream completo de audio.
        
        Args:
            audio_stream: Stream de audio completo
            return_chunks: Si True, retorna los chunks procesados
        
        Returns:
            (tiene_voz, chunks_opcionales)
        """
        has_speech = False
        chunks = [] if return_chunks else None
        
        # Dividir en frames
        num_frames = len(audio_stream) // self.frame_size
        
        for i in range(num_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio_stream[start:end]
            
            if self.is_speech(frame):
                has_speech = True
                if return_chunks:
                    chunks.append(frame)
        
        return has_speech, chunks


# Test del módulo
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test con audio de prueba
    vad = VAD(sample_rate=16000, aggressiveness=3)
    
    # Generar audio de prueba (silencio + tono + silencio)
    duration = 5.0
    sample_rate = 16000
    
    silence_duration = 1.0
    tone_duration = 2.0
    
    # Silencio inicial
    silence1 = np.zeros(int(sample_rate * silence_duration), dtype=np.int16)
    
    # Tono (simula voz)
    t = np.linspace(0, tone_duration, int(sample_rate * tone_duration))
    tone = (np.sin(2 * np.pi * 200 * t) * 10000).astype(np.int16)
    
    # Silencio final
    silence2 = np.zeros(int(sample_rate * silence_duration * 2), dtype=np.int16)
    
    # Concatenar
    audio = np.concatenate([silence1, tone, silence2])
    
    print(f"\nProcesando audio de {len(audio)/sample_rate:.2f}s...")
    has_speech, _ = vad.process_stream(audio)
    print(f"¿Contiene voz? {has_speech}")
    
    # Test detección de fin
    print("\nTest detección de fin de voz:")
    frame_size = vad.frame_size
    for i in range(0, len(audio), frame_size):
        chunk = audio[i:i+frame_size]
        if len(chunk) < frame_size:
            break
        
        is_speech = vad.is_speech(chunk)
        end_detected = vad.detect_speech_end(chunk)
        
        if is_speech or end_detected:
            time = i / sample_rate
            status = "SPEECH" if is_speech else "END"
            print(f"  {time:.2f}s: {status}")
```

##### 1.4: Test de Integración Audio Pipeline

**Archivo**: `tests/test_audio.py`

```python
"""
Tests del pipeline de audio completo.
"""

import sys
sys.path.append('/home/orangepi/asistente/src')

from audio.capture import AudioCapture
from audio.playback import AudioPlayback
from audio.vad import VAD
import numpy as np
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_latency():
    """Test de latencia end-to-end."""
    logger.info("=== Test de latencia ===")
    
    capture = AudioCapture()
    playback = AudioPlayback()
    
    # Grabar 1 segundo
    logger.info("Grabando 1 segundo...")
    start_time = time.time()
    
    capture.start()
    time.sleep(1.0)
    audio_data = capture.get_buffer(duration=1.0)
    capture.stop()
    
    capture_time = time.time() - start_time
    logger.info(f"Captura completada en {capture_time:.3f}s")
    
    # Reproducir
    logger.info("Reproduciendo...")
    start_time = time.time()
    playback.play_array(audio_data)
    playback_time = time.time() - start_time
    
    logger.info(f"Reproducción completada en {playback_time:.3f}s")
    logger.info(f"Latencia total: {capture_time + playback_time:.3f}s")


def test_vad_realtime():
    """Test VAD en tiempo real."""
    logger.info("\n=== Test VAD en tiempo real ===")
    logger.info("Habla durante 5 segundos...")
    
    capture = AudioCapture()
    vad = VAD(aggressiveness=2, silence_duration=2.0)
    
    speech_detected = False
    end_detected = False
    
    def vad_callback(audio_chunk):
        nonlocal speech_detected, end_detected
        
        # Procesar en frames VAD
        frame_size = vad.frame_size
        for i in range(0, len(audio_chunk), frame_size):
            frame = audio_chunk[i:i+frame_size]
            if len(frame) < frame_size:
                continue
            
            if vad.is_speech(frame):
                if not speech_detected:
                    logger.info("¡VOZ DETECTADA!")
                    speech_detected = True
            
            if vad.detect_speech_end(frame):
                if not end_detected:
                    logger.info("¡FIN DE VOZ DETECTADO!")
                    end_detected = True
    
    capture.register_callback(vad_callback)
    capture.start()
    
    time.sleep(5.0)
    
    capture.stop()
    
    logger.info(f"Voz detectada: {speech_detected}")
    logger.info(f"Fin detectado: {end_detected}")


def test_volume_control():
    """Test control de volumen."""
    logger.info("\n=== Test control de volumen ===")
    
    playback = AudioPlayback()
    
    # Volumen inicial
    initial_vol = playback.get_volume()
    logger.info(f"Volumen inicial: {initial_vol}%")
    
    # Generar tono
    duration = 1.0
    t = np.linspace(0, duration, int(16000 * duration))
    tone = (np.sin(2 * np.pi * 440 * t) * 32767 * 0.3).astype(np.int16)
    
    # Test subir volumen
    logger.info("Subiendo volumen...")
    playback.set_volume(30)
    logger.info(f"Reproduciendo a {playback.get_volume()}%")
    playback.play_array(tone)
    
    time.sleep(0.5)
    
    logger.info("Subiendo más...")
    playback.set_volume(70)
    logger.info(f"Reproduciendo a {playback.get_volume()}%")
    playback.play_array(tone)
    
    # Restaurar volumen
    playback.set_volume(initial_vol)
    logger.info(f"Volumen restaurado a {initial_vol}%")


if __name__ == '__main__':
    logger.info("Iniciando tests de audio...\n")
    
    try:
        test_latency()
        test_vad_realtime()
        test_volume_control()
        
        logger.info("\n✅ Todos los tests completados!")
        
    except Exception as e:
        logger.error(f"\n❌ Error en tests: {e}", exc_info=True)
```

**Criterios de Éxito Fase 1**:
- ✅ Captura de audio sin drops (buffer estable)
- ✅ Reproducción sin distorsión
- ✅ Latencia captura+reproducción < 200ms
- ✅ VAD detecta voz y silencio correctamente
- ✅ Control de volumen funcional
- ✅ Todos los tests pasan

**Script de verificación**:
```bash
#!/bin/bash
# scripts/test_audio_phase1.sh

echo "=== Verificación Fase 1: Audio Pipeline ==="

# Test 1: Dispositivos disponibles
echo -e "\n1. Verificando dispositivos de audio..."
python3 << 'EOF'
import sys
sys.path.append('/home/orangepi/asistente/src')
from audio.capture import AudioCapture
from audio.playback import AudioPlayback

capture = AudioCapture()
playback = AudioPlayback()

print("Dispositivos de entrada:")
for d in capture.list_devices():
    print(f"  {d}")

print("\nDispositivos de salida:")
for d in playback.list_devices():
    print(f"  {d}")
EOF

# Test 2: Captura y reproducción
echo -e "\n2. Test captura y reproducción..."
python3 /home/orangepi/asistente/tests/test_audio.py

echo -e "\n✅ Fase 1 verificada correctamente!"
```

---

### **FASE 2: Wake Word Detection** (Días 5-6)

**Objetivo**: Implementar detección de wake word "Asistente" con alta precisión y baja latencia.

#### Subtareas Detalladas

##### 2.1: Configurar Porcupine y Crear Wake Word Custom

```bash
# Instalar Porcupine
pip install pvporcupine

# Obtener access key de Picovoice Console
# 1. Ir a https://console.picovoice.ai
# 2. Crear cuenta gratis
# 3. Copiar Access Key

# Guardar key en config
python3 << 'EOF'
import json

config = {
    "porcupine": {
        "access_key": "TU_ACCESS_KEY_AQUI",
        "sensitivity": 0.5,
        "model_path": "/home/orangepi/asistente/models/wakeword/asistente_es.ppn"
    }
}

with open('/home/orangepi/asistente/config/config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Configuración guardada")
EOF
```

**Entrenar wake word custom**:

1. Ir a [Picovoice Console](https://console.picovoice.ai)
2. Wake Word → Train Custom Wake Word
3. Palabra: "Asistente"
4. Idioma: Español
5. Generar samples de voz (grabar tú mismo)
6. Entrenar modelo
7. Descargar `.ppn` file
8. Copiar a `models/wakeword/asistente_es.ppn`

##### 2.2: Implementar Wake Word Engine

**Archivo**: `src/engines/wakeword.py`

```python
"""
Wake Word Detection Engine
Detecta la palabra de activación "Asistente" usando Porcupine.
"""

import pvporcupine
import numpy as np
import logging
from typing import Optional, Callable
import time

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Detector de wake word usando Porcupine."""
    
    def __init__(
        self,
        access_key: str,
        keyword_path: str,
        sensitivity: float = 0.5,
        model_path: Optional[str] = None
    ):
        """
        Args:
            access_key: API key de Picovoice
            keyword_path: Ruta al archivo .ppn del wake word
            sensitivity: Sensibilidad (0.0-1.0, mayor=más sensible)
            model_path: Ruta al modelo custom (opcional)
        """
        self.access_key = access_key
        self.keyword_path = keyword_path
        self.sensitivity = sensitivity
        
        try:
            # Crear instancia de Porcupine
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[keyword_path],
                sensitivities=[sensitivity],
                model_path=model_path
            )
            
            # Metadata
            self.sample_rate = self.porcupine.sample_rate
            self.frame_length = self.porcupine.frame_length
            
            # Estadísticas
            self.detections = 0
            self.false_positives = 0
            self.start_time = time.time()
            
            logger.info(
                f"WakeWordDetector initialized: "
                f"sample_rate={self.sample_rate}Hz, "
                f"frame_length={self.frame_length}, "
                f"sensitivity={sensitivity}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            raise
    
    def process(self, audio_frame: np.ndarray) -> bool:
        """
        Procesa un frame de audio para detectar wake word.
        
        Args:
            audio_frame: Frame de audio (int16, longitud=frame_length)
        
        Returns:
            True si detecta wake word, False si no
        """
        if len(audio_frame) != self.frame_length:
            logger.warning(
                f"Invalid frame length: {len(audio_frame)} "
                f"(expected {self.frame_length})"
            )
            return False
        
        try:
            # Porcupine.process retorna índice del keyword detectado (-1 si nada)
            keyword_index = self.porcupine.process(audio_frame)
            
            if keyword_index >= 0:
                self.detections += 1
                logger.info(
                    f"Wake word detected! "
                    f"(total detections: {self.detections})"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Retorna estadísticas del detector."""
        uptime = time.time() - self.start_time
        return {
            'detections': self.detections,
            'false_positives': self.false_positives,
            'uptime_seconds': uptime,
            'detections_per_hour': (self.detections / uptime) * 3600 if uptime > 0 else 0
        }
    
    def reset_stats(self) -> None:
        """Resetea las estadísticas."""
        self.detections = 0
        self.false_positives = 0
        self.start_time = time.time()
    
    def __del__(self):
        """Cleanup al destruir."""
        if hasattr(self, 'porcupine'):
            self.porcupine.delete()


class WakeWordEngine:
    """
    Motor completo de wake word con integración AudioCapture.
    """
    
    def __init__(
        self,
        access_key: str,
        keyword_path: str,
        sensitivity: float = 0.5,
        on_detection: Optional[Callable] = None
    ):
        """
        Args:
            access_key: API key Picovoice
            keyword_path: Ruta al .ppn file
            sensitivity: Sensibilidad detección
            on_detection: Callback cuando se detecta wake word
        """
        self.detector = WakeWordDetector(
            access_key=access_key,
            keyword_path=keyword_path,
            sensitivity=sensitivity
        )
        
        self.on_detection = on_detection
        self.is_running = False
        
        logger.info("WakeWordEngine initialized")
    
    def start(self, audio_capture) -> None:
        """
        Inicia la detección de wake word.
        
        Args:
            audio_capture: Instancia de AudioCapture
        """
        if self.is_running:
            logger.warning("Wake word engine already running")
            return
        
        # Verificar sample rate compatible
        if audio_capture.sample_rate != self.detector.sample_rate:
            raise ValueError(
                f"Sample rate mismatch: capture={audio_capture.sample_rate}, "
                f"porcupine={self.detector.sample_rate}"
            )
        
        # Registrar callback
        audio_capture.register_callback(self._audio_callback)
        
        # Iniciar captura si no está activa
        if not audio_capture.is_running:
            audio_capture.start()
        
        self.is_running = True
        logger.info("Wake word detection started")
    
    def _audio_callback(self, audio_chunk: np.ndarray) -> None:
        """Callback interno para procesar audio."""
        # Procesar en frames de Porcupine
        frame_length = self.detector.frame_length
        
        for i in range(0, len(audio_chunk), frame_length):
            frame = audio_chunk[i:i+frame_length]
            
            if len(frame) < frame_length:
                continue
            
            if self.detector.process(frame):
                # Wake word detectado!
                if self.on_detection:
                    try:
                        self.on_detection()
                    except Exception as e:
                        logger.error(f"Error in detection callback: {e}")
    
    def stop(self) -> None:
        """Detiene la detección."""
        self.is_running = False
        logger.info("Wake word detection stopped")


# Test del módulo
if __name__ == '__main__':
    import sys
    sys.path.append('/home/orangepi/asistente/src')
    
    from audio.capture import AudioCapture
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    # Cargar config
    with open('/home/orangepi/asistente/config/config.json') as f:
        config = json.load(f)
    
    # Crear detector
    def on_wake_word():
        print("\n🎤 ¡WAKE WORD DETECTADO! 🎤\n")
    
    engine = WakeWordEngine(
        access_key=config['porcupine']['access_key'],
        keyword_path=config['porcupine']['model_path'],
        sensitivity=config['porcupine']['sensitivity'],
        on_detection=on_wake_word
    )
    
    # Iniciar captura
    capture = AudioCapture(sample_rate=engine.detector.sample_rate)
    
    print("Iniciando detección de wake word...")
    print("Di 'Asistente' para probar")
    print("Presiona Ctrl+C para salir\n")
    
    engine.start(capture)
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nDeteniendo...")
        engine.stop()
        capture.stop()
```

**Criterios de Éxito Fase 2**:
- ✅ Wake word "Asistente" se detecta con >90% precisión
- ✅ False positives < 1 por hora
- ✅ Latencia detección < 100ms
- ✅ CPU usage < 5% en idle
- ✅ Sin crashes en 30 minutos de operación continua

---

Continúo con el resto de fases extendidas... 