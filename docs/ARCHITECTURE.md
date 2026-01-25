# Arquitectura del Sistema

## Vista General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Orange Pi 5 Ultra (Armbian)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      AUDIO PIPELINE LAYER                            │  │
│  │  Mic (ES8388) → ALSA → PyAudio → Buffer Circular → VAD               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                          │                                                  │
│  ┌───────────────────────┼──────────────────────────────────────────────┐  │
│  │             WAKE WORD DETECTION LAYER                                │  │
│  │                       Porcupine Engine                                │  │
│  └───────────────────────┼──────────────────────────────────────────────┘  │
│                          │                                                  │
│  ┌───────────────────────┼──────────────────────────────────────────────┐  │
│  │          SPEECH RECOGNITION LAYER (Vosk STT)                         │  │
│  │                      Spanish offline model                            │  │
│  └───────────────────────┼──────────────────────────────────────────────┘  │
│                          │                                                  │
│  ┌───────────────────────┼──────────────────────────────────────────────┐  │
│  │        NATURAL LANGUAGE UNDERSTANDING LAYER                          │  │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐           │  │
│  │   │ System  │  │   API   │  │   LLM   │  │   Context    │           │  │
│  │   │Commands │  │Handlers │  │ Query   │  │   Manager    │           │  │
│  │   └────┬────┘  └────┬────┘  └────┬────┘  └──────┬───────┘           │  │
│  └────────┼─────────────┼─────────────┼───────────────┼──────────────────┘  │
│           │             │             │               │                     │
│  ┌────────┴─────────────┴─────────────┴───────────────┴──────────────────┐  │
│  │                    RESPONSE GENERATOR                                 │  │
│  └──────────────────────────────┬─────────────────────────────────────────┘  │
│                                 │                                             │
│  ┌──────────────────────────────┴─────────────────────────────────────────┐  │
│  │         TEXT-TO-SPEECH LAYER (Piper TTS)                               │  │
│  └──────────────────────────────┬─────────────────────────────────────────┘  │
│                                 │                                             │
│  ┌──────────────────────────────┴─────────────────────────────────────────┐  │
│  │                    AUDIO PLAYBACK (ALSA)                               │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    WEB SERVER & CONFIGURATION                        │ │
│  │                    Flask (Port 5000)                                 │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

## Estados del Sistema

### 1. IDLE STATE
- Escuchando continuamente
- Procesando audio con Porcupine
- CPU: < 5%

### 2. LISTENING STATE
- Wake word detectado
- Capturando comando de voz
- VAD monitorea silencio

### 3. PROCESSING STATE
- STT transcribe audio
- Intent classifier analiza comando
- Se ejecuta acción correspondiente

### 4. SPEAKING STATE
- TTS genera respuesta
- Audio se reproduce por altavoz

## Directorios

```
src/
├── audio/          # Pipeline de audio
│   ├── capture.py  # Captura de micrófono
│   ├── playback.py # Reproducción de altavoz
│   └── vad.py      # Voice Activity Detection
│
├── engines/        # Motores AI
│   ├── wakeword.py # Porcupine wrapper
│   ├── stt.py      # Vosk wrapper
│   ├── tts.py      # Piper wrapper
│   └── llm.py      # rkllama wrapper
│
├── intents/        # Procesamiento de comandos
│   ├── processor.py# Intent classifier
│   ├── commands.py # System commands
│   └── apis.py     # API handlers
│
├── context/        # Gestión de contexto
│   └── manager.py  # Conversation history
│
├── webserver/      # Panel web
│   ├── app.py      # Flask app
│   ├── routes/     # API endpoints
│   └── templates/  # HTML templates
│
└── utils/          # Utilidades
    ├── logger.py   # Logging
    └── config.py   # Config loader
```

## Flujo de Datos

```
Usuario habla
    │
    ▼
[AudioCapture] → Buffer circular
    │
    ▼
[Porcupine] → ¿Wake word?
    │ NO → Continuar escuchando
    │ YES
    ▼
[VAD] → ¿Fin de voz?
    │ NO → Seguir grabando
    │ YES
    ▼
[Vosk STT] → Texto transcrito
    │
    ▼
[Intent Classifier] → ¿Tipo de comando?
    │
    ├──→ System command → Ejecutar
    ├──→ API query → Llamar API
    └──→ General query → LLM
    │
    ▼
[Response Generator] → Formatear respuesta
    │
    ▼
[Piper TTS] → Generar audio WAV
    │
    ▼
[AudioPlayback] → Reproducir
    │
    ▼
[Context Manager] → Guardar historia
    │
    ▼
IDLE
```

## Configuración

El archivo `config/config.json` controla todos los aspectos:

- **audio**: Configuración de hardware de audio
- **vad**: Parámetros de detección de voz
- **wake_word**: Sensibilidad y modelo
- **stt**: Motor y modelo de STT
- **tts**: Voz y velocidad de TTS
- **llm**: Modelo y parámetros del LLM
- **context**: Tiempo de espera y tamaño de historia
- **webserver**: Puerto y host del panel web
