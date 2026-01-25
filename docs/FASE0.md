# Fase 0: Setup Inicial - Guía de Instalación

Esta guía cubre la instalación completa del entorno en la Orange Pi 5 Ultra.

## Requisitos Previos

- Orange Pi 5 Ultra con Armbian instalado
- Acceso a terminal (SSH o local)
- Conexión a internet para descarga inicial
- Al menos 16GB de almacenamiento libre

## Pasos de Instalación

### 1. Preparar el Sistema

Actualizar el sistema:

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Instalar Script de Instalación

El script principal `setup.sh` instala todas las dependencias:

```bash
cd /home/orangepi/asistente
sudo ./setup.sh
```

Selecciona **"1. Instalar TODO"**.

Este script instala:
- Herramientas básicas (git, cmake, etc.)
- Python 3.10+ y dependencias
- ALSA y PulseAudio
- NetworkManager
- Modelos STT (Vosk) y TTS (Piper)

### 3. Verificar Audio

```bash
# Listar dispositivos
arecord -l
aplay -l

# Test de grabación
arecord -D hw:0,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav
```

### 4. Configurar ALSA

El archivo `/etc/asound.conf` ya está configurado para la tarjeta ES8388.

Para ajustar volúmenes:

```bash
alsamixer
```

### 5. Crear Entorno Virtual

```bash
cd /home/orangepi/assi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Descargar Modelos LLM

**Opción 1: Desde el Panel Web**

```bash
source venv/bin/activate
python src/webserver/app.py
```

Abre `http://localhost:5000` → Menú "Modelos"

**Opción 2: Desde línea de comandos**

```bash
# Instalar huggingface-cli
pip install huggingface-hub

# Descargar modelo (ejemplo: Qwen2 1.5B RKLLM)
mkdir -p models/llm
huggingface-cli download FydeOS/Qwen2-1_5B_rkLLM --local-dir models/llm/qwen2-1.5b-rkllm
```

**Modelos RKLLM disponibles (optimizados para NPU RK3588):**

| Modelo | Tamaño | Descripción |
|--------|--------|-------------|
| `qwen2-1.5b-rkllm` | 1.2GB | ⭐ Recomendado |
| `qwen1.5-0.5b-rkllm` | 400MB | Ultra ligero |
| `qwen1.5-1.8b-rkllm` | 1.4GB | Balance calidad/velocidad |
| `phi-2-rk3588` | 1.1GB | Microsoft Phi-2 |
| `phi-3-mini-rk3588` | 1.3GB | Microsoft Phi-3 |
| `gemma-2b-rk3588` | 900MB | Google Gemma |
| `tinyllama-v1-rk3588` | 700MB | Muy ligero |

### 7. Configurar Wake Word

El wake word requiere configuración manual:

1. Ve a [Picovoice Console](https://console.picovoice.ai)
2. Crea cuenta gratis
3. Entrena la palabra "Asistente"
4. Descarga el archivo `.ppn`
5. Guárdalo en `models/wakeword/asistente_es.ppn`

### 8. Configurar API Keys (opcional)

```bash
cp config/api_keys.json.example config/api_keys.json
nano config/api_keys.json
```

## Verificación

```bash
cd /home/orangepi/asistente
source venv/bin/activate

# Test de audio
python tests/test_audio.py

# Ejecutar asistente
python src/main.py --once
```

Siguiente fase: [Fase 1 - Audio Pipeline](FASE1.md)
