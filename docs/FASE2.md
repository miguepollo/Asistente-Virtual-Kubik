# Fase 2: Wake Word Detection

El sistema de detección de wake word permite activar el asistente con la voz.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│              WAKE WORD DETECTION                            │
│                                                             │
│  ┌─────────┐    ┌────────────┐    ┌──────────────────┐     │
│  │  Mic    │───▶│   Buffer   │───▶│    Porcupine     │     │
│  │ ES8388  │    │  Circular  │    │  Engine          │     │
│  └─────────┘    └────────────┘    └────────┬─────────┘     │
│                                            │                │
│                                    Wake Word?                │
│                                    ┌─────┴─────┐            │
│                                    │           │            │
│                                   YES          NO            │
│                                    │           │            │
│                           ┌────────▼───┐    ┌─▼──────┐     │
│                           │ Start      │    │ Buffer  │     │
│                           │ Listening  │    │ More    │     │
│                           └────────────┘    └─────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Configuración de Porcupine

### 1. Obtener Access Key

Ve a [Picovoice Console](https://console.picovoice.ai):
1. Crea cuenta gratuita
2. Copia tu Access Key

### 2. Entrenar Wake Word

1. En Picovoice Console, ve a "Wake Words"
2. Click en "Train Custom Wake Word"
3. Palabra: **Asistente**
4. Idioma: **Español**
5. Graba o sube muestras de voz (mínimo 3)
6. Entrena el modelo
7. Descarga el archivo `.ppn`

### 3. Instalar Modelo

```bash
cp asistente_es.ppn /home/orangepi/assi/models/wakeword/
```

### 4. Configurar

Edita `config/config.json`:

```json
{
  "wake_word": {
    "enabled": true,
    "keyword": "asistente",
    "sensitivity": 0.5,
    "model_path": "/home/orangepi/assi/models/wakeword/asistente_es.ppn"
  },
  "picovoice": {
    "access_key": "TU_ACCESS_KEY_AQUI"
  }
}
```

## Uso

```python
from engines.wakeword import WakeWordEngine
from audio.capture import AudioCapture

def on_wake_word():
    print("¡Asistente activado!")

engine = WakeWordEngine(
    access_key="YOUR_KEY",
    keyword_path="models/wakeword/asistente_es.ppn",
    sensitivity=0.5,
    on_detection=on_wake_word
)

capture = AudioCapture(sample_rate=16000)
engine.start(capture)
```

## Ajuste de Sensibilidad

| Sensibilidad | Comportamiento |
|-------------|----------------|
| 0.3 | Muy sensible (más falsos positivos) |
| 0.5 | Equilibrado (recomendado) |
| 0.7 | Poco sensible (puede fallar) |

## Rendimiento

- **CPU**: < 5% en idle
- **Latencia**: < 100ms
- **Precisión**: > 90%
- **False positives**: < 1/hora

## Solución de Problemas

### No detecta el wake word

1. Aumenta la sensibilidad a 0.6 o 0.7
2. Verifica que el modelo `.ppn` esté en la ruta correcta
3. Prueba con diferentes entonaciones

### Muchos falsos positivos

1. Reduce la sensibilidad a 0.4 o 0.3
2. Reentrena el modelo con más muestras
3. Usa una palabra más distintiva

Siguiente fase: [Fase 3 - STT + TTS](FASE3.md)
