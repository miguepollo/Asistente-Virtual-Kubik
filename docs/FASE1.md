# Fase 1: Audio Pipeline

El pipeline de audio es la base del asistente. Maneja captura, reproducción y detección de actividad de voz.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    AUDIO PIPELINE                            │
│                                                             │
│  ┌─────────┐    ┌────────────┐    ┌──────────────────┐     │
│  │  Mic    │───▶│   Buffer   │───▶│       VAD         │     │
│  │ ES8388  │    │  Circular  │    │  (Voice Activity) │     │
│  └─────────┘    └────────────┘    └──────────────────┘     │
│                                                    │         │
│  ┌─────────┐                                      │         │
│  │ Speaker │◀─────────────────────────────────────┘         │
│  │  Jack   │                                                 │
│  └─────────┘                                                 │
└─────────────────────────────────────────────────────────────┘
```

## Módulos

### 1. AudioCapture (`src/audio/capture.py`)

Captura audio del micrófono con buffer circular.

```python
from audio.capture import AudioCapture

capture = AudioCapture(
    sample_rate=16000,
    channels=1,
    buffer_duration=5.0
)

capture.start()
audio = capture.get_buffer(duration=2.0)
capture.stop()
```

**Parámetros:**
- `sample_rate`: 16000 Hz (óptimo para Vosk)
- `channels`: 1 (mono)
- `buffer_duration`: 5 segundos de buffer circular

### 2. AudioPlayback (`src/audio/playback.py`)

Reproduce audio por el altavoz.

```python
from audio.playback import AudioPlayback

playback = AudioPlayback()
playback.set_volume(70)
playback.play_array(audio_data)
```

**Métodos:**
- `play_wav(filepath)`: Reproduce archivo WAV
- `play_array(array)`: Reproduce numpy array
- `set_volume(level)`: Ajusta volumen (0-100)

### 3. VAD (`src/audio/vad.py`)

Voice Activity Detection usando WebRTC.

```python
from audio.vad import VAD

vad = VAD(
    sample_rate=16000,
    aggressiveness=3,
    silence_duration=2.0
)

is_speech = vad.is_speech(audio_frame)
```

**Niveles de agresividad:**
- `0`: Muy permisivo (más falsos positivos)
- `1`: Permisivo
- `2`: Estándar
- `3`: Estricto (recomendado)

## Tests

### Test de latencia

```bash
python tests/test_audio.py::test_latency
```

Mide el tiempo end-to-end de captura + reproducción.

### Test de VAD

```bash
python tests/test_audio.py::test_vad_realtime
```

Prueba la detección de voz en tiempo real.

## Configuración

En `config/config.json`:

```json
{
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size": 512,
    "input_volume": 60,
    "output_volume": 70
  },
  "vad": {
    "aggressiveness": 3,
    "frame_duration_ms": 30,
    "silence_duration": 2.0
  }
}
```

## Solución de Problemas

### Audio distorsionado

Reduce el volumen:
```bash
amixer sset Master 50%
amixer sset Capture 50%
```

### VAD no detecta voz

Reduce la agresividad en config.json:
```json
{"vad": {"aggressiveness": 1}}
```

### Latencia alta

Asegúrate de usar sample_rate=16000 y chunk_size=512.

Siguiente fase: [Fase 2 - Wake Word Detection](FASE2.md)
