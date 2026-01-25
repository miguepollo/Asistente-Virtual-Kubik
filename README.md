# Asistente Virtual - Orange Pi 5 Ultra

Asistente de voz offline-first para Orange Pi 5 Ultra con IA local, wake word detection, integración de APIs externas y servidor web de configuración.

## Características

- **100% Offline First**: Funciona sin conexión a internet
- **Wake Word Detection**: Activación por voz "Asistente"
- **STT Offline**: Speech-to-Text con Vosk en español
- **TTS Natural**: Text-to-Speech con Piper
- **LLM Local**: rkllama acelerado por NPU (6 TOPS)
- **Web UI**: Panel de configuración vía WiFi AP
- **Baja Latencia**: < 200ms end-to-end

## Hardware

- **Placa**: Orange Pi 5 Ultra
- **SoC**: Rockchip RK3588 (4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz)
- **NPU**: 6 TOPS para aceleración de IA
- **RAM**: 16GB LPDDR4X
- **Audio**: Codec ES8388 integrado

## Instalación Rápida

### 1. Copiar archivos a la Orange Pi

```bash
# Desde tu PC
scp -r asistente/ orangepi@192.168.1.XX:/home/orangepi/
```

### 2. Ejecutar instalación completa

```bash
# En la Orange Pi
cd /home/orangepi/asistente
sudo ./setup.sh install
```

Esto instala:
- Sistema actualizado
- Python 3.10+ y dependencias
- Audio (ALSA, PulseAudio)
- Modelos IA (Vosk STT, Piper TTS)
- Entorno virtual Python

### 3. Configurar audio

```bash
./setup.sh audio
```

### 4. Probar el sistema

```bash
./setup.sh test
```

## Estructura del Proyecto

```
/home/orangepi/assi/
├── config/                 # Configuración
│   ├── config.json        # Config principal
│   └── api_keys.json      # API keys (encriptado)
├── models/                 # Modelos AI
│   ├── llm/               # LLM (.gguf)
│   ├── stt/               # Vosk models
│   ├── tts/               # Piper voices
│   └── wakeword/          # Porcupine .ppn
├── src/                    # Código fuente
│   ├── audio/             # Pipeline de audio
│   ├── engines/           # STT, TTS, LLM, WakeWord
│   ├── intents/           # Procesamiento de intents
│   ├── context/           # Gestión de contexto
│   ├── webserver/         # Flask web app
│   └── utils/             # Utilidades
├── scripts/                # Scripts de instalación
├── systemd/                # Servicios systemd
└── tests/                  # Tests unitarios
```

## Configuración

### Archivo de configuración principal

Edita `config/config.json`:

```json
{
  "audio": {
    "sample_rate": 16000,
    "output_volume": 70
  },
  "wake_word": {
    "sensitivity": 0.5
  },
  "llm": {
    "model_path": "/path/to/model.gguf",
    "temperature": 0.7
  }
}
```

### API Keys (opcional, para servicios online)

Copia y edita el archivo de API keys:

```bash
cp config/api_keys.json.example config/api_keys.json
nano config/api_keys.json
```

## Uso

### Ejecutar el asistente

```bash
cd /home/orangepi/asistente
source venv/bin/activate

# Modo continuo (con wake word)
python src/main.py

# Modo single (un comando y sale)
python src/main.py --once
```

### Panel Web

```bash
# Iniciar servidor web
source venv/bin/activate
python src/webserver/app.py

# O como servicio
sudo systemctl start asistente-web
```

Luego abre en tu navegador: **http://localhost:5000**

#### Características del Panel Web:
- **Dashboard**: Estado del sistema, CPU, memoria, disco
- **Modelos**: Descargar modelos LLM con spinner de progreso
  - Modelos RKLLM optimizados para NPU RK3588:
    - `qwen2-1.5b-rkllm` (1.2GB) - Recomendado
    - `qwen1.5-0.5b-rkllm` (400MB) - Ultra ligero
    - `qwen1.5-1.8b-rkllm` (1.4GB) - Balance calidad/velocidad
    - `phi-2-rk3588`, `phi-3-mini-rk3588` (Microsoft)
    - `gemma-2b-rk3588` (Google)
    - `tinyllama-v1-rk3588` (Muy ligero)
- **Configuración**: Ajustar audio, VAD, TTS, LLM
- **Logs**: Ver logs del sistema en tiempo real

### Comandos de voz

- "Asistente" - Activa el asistente
- "¿Qué hora es?" - Dice la hora actual
- "Cuéntame un chiste" - Cuenta un chiste
- "Gracias" - Responde de nada
- "Para/Stop" - Detiene el asistente

### Logs

```bash
# Ver logs en tiempo real
tail -f logs/assistant.log
```

## Opciones del Script setup.sh

```bash
./setup.sh              # Menú interactivo
./setup.sh install      # Instalación completa (incluye modelos)
./setup.sh audio        # Configurar y probar audio
./setup.sh models       # Descargar modelos IA
./setup.sh test         # Probar sistema completo
./setup.sh services     # Instalar servicios systemd
./setup.sh wakeword     # Instrucciones para wake word
```

## Panel Web de Configuración

1. Conéctate al WiFi AP: `Asistente-Config`
2. Abre el navegador: `http://192.168.12.1`
3. Configura:
   - WiFi
   - Modelos
   - API keys
   - Ajustes de audio

## Comandos de Voz

- "Asistente, ¿qué hora es?"
- "Asistente, ¿clima hoy?"
- "Asistente, dime un chiste"
- "Asistente, sube el volumen"
- "Asistente, reproduce música en Spotify"

## Desarrollo

### Ejecutar tests

```bash
source venv/bin/activate
pytest tests/
```

### Test de audio

```bash
python tests/test_audio.py
```

## Solución de Problemas

### Sin audio de entrada

```bash
# Verificar dispositivos
arecord -l

# Ajustar volumen de captura
alsamixer
# F4 para captura, ajustar niveles
```

### Wake word no detecta

- Ajusta `wake_word.sensitivity` en config.json
- Prueba valores entre 0.3 y 0.7

### LLM lento

- Usa modelo más pequeño: phi-2-1.3b-q4
- Reduce `llm.context_length`

## Roadmap

- [x] Fase 0: Setup inicial
- [x] Fase 1: Audio Pipeline
- [ ] Fase 2: Wake Word Detection
- [ ] Fase 3: STT + TTS
- [ ] Fase 4: LLM Integration
- [ ] Fase 5: Intents y APIs
- [ ] Fase 6: Web Server

## Licencia

MIT License

## Créditos

- Vosk: Alpha Cephei
- Piper: rhasspy/piper
- Porcupine: Picovoice
- rkllama: airockchip
