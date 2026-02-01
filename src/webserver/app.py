"""
Asistente Virtual - Web Server
Flask app para configuración y gestión del asistente.
"""

import os
import sys
import json
import logging
import subprocess
import threading
import time
import requests
from pathlib import Path
from typing import Dict, List

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config_loader import get_config
from utils.logger import setup_logging, get_logger

logger = get_logger("webserver")

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'asistente-secret-key'
app.config['JSON_AS_ASCII'] = False

# Directorios
PROJECT_DIR = Path("/home/orangepi/asistente2")
MODELS_DIR = PROJECT_DIR / "models"
CONFIG_DIR = PROJECT_DIR / "config"
LOGS_DIR = PROJECT_DIR / "logs"

# Estado de descargas
download_status = {
    "downloading": False,
    "model": None,
    "progress": 0,
    "error": None,
    "type": None  # "llm" o "tts"
}

###############################################################################
# CONSTANTES - Voces de Piper TTS
###############################################################################
PIPER_VOICES = {
    "es_ES": [
        {
            "name": "davefx",
            "quality": "medium",
            "size_mb": 65,
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
            "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
            "recommended": True
        },
        {
            "name": "carlfm",
            "quality": "medium",
            "size_mb": 65,
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/carlfm/medium/es_ES-carlfm-medium.onnx",
            "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/carlfm/medium/es_ES-carlfm-medium.onnx.json",
            "recommended": False
        }
    ],
    "es_MX": [
        {
            "name": "ald",
            "quality": "medium",
            "size_mb": 65,
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_MX/ald/medium/es_MX-ald-medium.onnx",
            "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json",
            "recommended": False
        }
    ],
    "en_US": [
        {
            "name": "amy",
            "quality": "medium",
            "size_mb": 65,
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx",
            "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
            "recommended": True
        },
        {
            "name": "arctic",
            "quality": "medium",
            "size_mb": 65,
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/arctic/medium/en_US-arctic-medium.onnx",
            "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/arctic/medium/en_US-arctic-medium.onnx.json",
            "recommended": False
        },
        {
            "name": "joe",
            "quality": "medium",
            "size_mb": 65,
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx",
            "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx.json",
            "recommended": False
        }
    ]
}

###############################################################################
# Rutas Principales
###############################################################################
@app.route('/')
def index():
    """Dashboard principal o setup si es primera ejecución."""
    config_path = CONFIG_DIR / "config.json"
    if not config_path.exists():
        return render_template('setup.html')
    return render_template('index.html')

@app.route('/setup')
def setup():
    """Página de configuración inicial."""
    return render_template('setup.html')

@app.route('/config')
def config():
    """Página de configuración."""
    return render_template('config.html')

@app.route('/models')
def models():
    """Página de modelos."""
    return render_template('models.html')

@app.route('/logs')
def logs():
    """Página de logs."""
    return render_template('logs.html')

###############################################################################
# API: Sistema
###############################################################################
@app.route('/api/status')
def api_status():
    """Estado del sistema."""
    config = get_config()

    status = {
        "running": True,
        "audio": {
            "input_devices": _get_input_devices(),
            "output_devices": _get_output_devices()
        },
        "models": {
            "stt": os.path.exists(f"{MODELS_DIR}/stt/vosk-model-small-es-0.42"),
            "tts": os.path.exists(f"{MODELS_DIR}/tts/es_ES-davefx-medium.onnx"),
            "llm": _get_llm_models()
        },
        "services": {
            "asistente": _service_status("asistente.service"),
            "web": _service_status("asistente-web.service")
        }
    }
    return jsonify(status)

@app.route('/api/stats')
def api_stats():
    """Estadísticas del sistema."""
    try:
        import shutil
        cpu = _get_cpu_usage()
        memory = _get_memory_usage()
        disk = shutil.disk_usage(PROJECT_DIR)

        stats = {
            "cpu": cpu,
            "memory": memory,
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round((disk.used / disk.total) * 100, 1)
            },
            "uptime": _get_uptime()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

###############################################################################
# API: Configuración
###############################################################################
@app.route('/api/config', methods=['GET'])
def api_config_get():
    """Obtener configuración actual."""
    config = get_config()
    return jsonify(config.config)

@app.route('/api/config', methods=['POST'])
def api_config_save():
    """Guardar configuración."""
    try:
        data = request.json
        config = get_config()

        # Actualizar valores
        for key, value in data.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    config.set(f"{key}.{subkey}", subvalue)
            else:
                config.set(key, value)

        config.save()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

###############################################################################
# API: Modelos
###############################################################################
@app.route('/api/models/llm')
def api_models_llm():
    """Obtener modelos LLM disponibles y actuales."""
    return jsonify({
        "available": _get_available_models(),
        "installed": _get_llm_models()
    })

@app.route('/api/models/download', methods=['POST'])
def api_models_download():
    """Iniciar descarga de modelo."""
    global download_status

    if download_status["downloading"]:
        return jsonify({"error": "Ya hay una descarga en curso"}), 400

    data = request.json
    model_name = data.get("model")

    if not model_name:
        return jsonify({"error": "No se especificó modelo"}), 400

    models = _get_available_models()
    model = next((m for m in models if m["name"] == model_name), None)

    if not model:
        return jsonify({"error": "Modelo no encontrado"}), 404

    # Iniciar descarga en thread
    thread = threading.Thread(
        target=_download_model,
        args=(model,)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "model": model_name})

@app.route('/api/models/download/status')
def api_download_status():
    """Estado de descarga."""
    return jsonify(download_status)

@app.route('/api/models/delete', methods=['POST'])
def api_models_delete():
    """Eliminar un modelo."""
    import shutil
    data = request.json
    model_name = data.get("model")

    if not model_name:
        return jsonify({"error": "No se especificó modelo"}), 400

    # Intentar eliminar como directorio (modelo RKLLM)
    model_dir = MODELS_DIR / "llm" / model_name
    if model_dir.exists() and model_dir.is_dir():
        shutil.rmtree(model_dir)
        return jsonify({"success": True})

    # Intentar eliminar como archivo .gguf
    model_file = MODELS_DIR / "llm" / f"{model_name}.gguf"
    if model_file.exists():
        model_file.unlink()
        return jsonify({"success": True})

    return jsonify({"error": "Modelo no encontrado"}), 404

###############################################################################
# API: Logs
###############################################################################
@app.route('/api/logs')
def api_logs():
    """Obtener logs."""
    log_file = LOGS_DIR / "assistant.log"
    lines = request.args.get("lines", 100, type=int)

    if log_file.exists():
        output = subprocess.run(
            ["tail", "-n", str(lines), str(log_file)],
            capture_output=True,
            text=True
        )
        return jsonify({"logs": output.stdout})
    else:
        return jsonify({"logs": "No hay logs disponibles"})

###############################################################################
# API: Control del Asistente
###############################################################################
@app.route('/api/assistant/start', methods=['POST'])
def api_assistant_start():
    """Iniciar el asistente."""
    try:
        subprocess.run(
            ["systemctl", "start", "asistente.service"],
            check=True
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/assistant/stop', methods=['POST'])
def api_assistant_stop():
    """Detener el asistente."""
    try:
        subprocess.run(
            ["systemctl", "stop", "asistente.service"],
            check=True
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/assistant/restart', methods=['POST'])
def api_assistant_restart():
    """Reiniciar el asistente."""
    try:
        subprocess.run(
            ["systemctl", "restart", "asistente.service"],
            check=True
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

###############################################################################
# API: WiFi
###############################################################################
@app.route('/api/wifi')
def api_wifi_list():
    """Listar redes WiFi disponibles."""
    try:
        # Primero escanear redes
        subprocess.run(["nmcli", "dev", "wifi", "rescan"], capture_output=True, timeout=5)
        time.sleep(1)

        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,CHAN", "dev", "wifi", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        networks = []
        seen_ssids = set()

        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(':')
                if len(parts) >= 3 and parts[0]:
                    ssid = parts[0]
                    # Evitar duplicados
                    if ssid not in seen_ssids:
                        seen_ssids.add(ssid)
                        signal_strength = int(parts[1]) if parts[1].isdigit() else 0
                        # Calcular calidad de señal (0-100)
                        quality = max(0, min(100, signal_strength))

                        networks.append({
                            "ssid": ssid,
                            "signal": quality,
                            "signal_bars": 4 if quality > 75 else (3 if quality > 50 else (2 if quality > 25 else 1)),
                            "security": parts[2],
                            "channel": parts[3] if len(parts) > 3 else "Unknown",
                            "secured": parts[2] != ""
                        })

        # Ordenar por señal
        networks.sort(key=lambda x: x["signal"], reverse=True)
        return jsonify({"networks": networks})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout escaneando redes"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wifi/connect', methods=['POST'])
def api_wifi_connect():
    """Conectar a una red WiFi."""
    try:
        data = request.json
        ssid = data.get("ssid")
        password = data.get("password", "")

        if not ssid:
            return jsonify({"error": "SSID es requerido"}), 400

        # Verificar si ya existe una conexión para este SSID
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
            capture_output=True,
            text=True
        )

        existing_conn = None
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(':')
                if len(parts) == 2 and parts[0] == ssid and parts[1] == "802-11-wireless":
                    existing_conn = ssid
                    break

        if existing_conn:
            # Actualizar conexión existente
            subprocess.run(
                ["nmcli", "connection", "modify", ssid, "wifi-sec.psk", password],
                capture_output=True
            )
        else:
            # Crear nueva conexión
            cmd = ["nmcli", "device", "wifi", "connect", ssid]
            if password:
                cmd.extend(["password", password])
            subprocess.run(cmd, capture_output=True, timeout=30)

        return jsonify({"success": True, "ssid": ssid})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout conectando"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wifi/disconnect', methods=['POST'])
def api_wifi_disconnect():
    """Desconectar del WiFi actual."""
    try:
        subprocess.run(
            ["nmcli", "connection", "down", "wlan0"],
            capture_output=True
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wifi/status')
def api_wifi_status():
    """Obtener estado de la conexión WiFi actual."""
    try:
        # Obtener información de conexión
        result = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
            capture_output=True,
            text=True
        )

        current = None
        for line in result.stdout.strip().split('\n'):
            if line.startswith('yes'):
                parts = line.split(':')
                if len(parts) >= 4:
                    signal_strength = int(parts[2]) if parts[2].isdigit() else 0
                    current = {
                        "ssid": parts[1],
                        "signal": max(0, min(100, signal_strength)),
                        "security": parts[3],
                        "connected": True
                    }
                break

        # Si no hay conexión activa, verificar IP
        if not current:
            ip_result = subprocess.run(
                ["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", "wlan0"],
                capture_output=True,
                text=True
            )
            if ip_result.stdout.strip():
                ip = ip_result.stdout.strip().split(':')[-1]
                current = {"connected": True, "ip": ip}
            else:
                current = {"connected": False}

        # Obtener IP si está conectado
        if current and current.get("connected") and "ip" not in current:
            ip_result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True,
                text=True
            )
            ips = ip_result.stdout.strip().split()
            current["ip"] = ips[0] if ips else "Unknown"

        return jsonify(current)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wifi/available')
def api_wifi_available():
    """Verificar si WiFi está disponible."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"],
            capture_output=True,
            text=True
        )

        wifi_available = False
        for line in result.stdout.strip().split('\n'):
            if line and 'wifi' in line.lower():
                parts = line.split(':')
                if len(parts) >= 3:
                    wifi_available = parts[2] in ['connected', 'available']
                break

        return jsonify({"available": wifi_available})
    except:
        return jsonify({"available": False})

###############################################################################
# API: Piper TTS Voices
###############################################################################
@app.route('/api/tts/voices')
def api_tts_voices():
    """Obtener voces de Piper TTS disponibles e instaladas."""
    try:
        tts_dir = MODELS_DIR / "tts"

        # Detectar voces instaladas
        installed = []
        if tts_dir.exists():
            for voice_file in tts_dir.glob("*.onnx"):
                # Extraer nombre de voz del archivo
                # Formato: es_ES-davefx-medium.onnx
                name = voice_file.stem
                installed.append(name)

        # Agrupar voces disponibles por idioma
        available = {}
        for lang, voices in PIPER_VOICES.items():
            available[lang] = []
            for voice in voices:
                # Verificar si está instalada
                voice_file = f"{lang}-{voice['name']}-{voice['quality']}"
                is_installed = any(voice_file in v for v in installed)

                available[lang].append({
                    "id": f"{lang}-{voice['name']}-{voice['quality']}",
                    "name": voice['name'],
                    "quality": voice['quality'],
                    "size_mb": voice['size_mb'],
                    "installed": is_installed,
                    "recommended": voice['recommended'],
                    "language": lang
                })

        # Obtener voz actual desde configuración
        config = get_config()
        current_voice = config.get("tts.voice", "es_ES-davefx-medium")

        return jsonify({
            "available": available,
            "installed": installed,
            "current": current_voice
        })
    except Exception as e:
        logger.error(f"Error obteniendo voces TTS: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts/voices/download', methods=['POST'])
def api_tts_download_voice():
    """Descargar una voz de Piper TTS."""
    global download_status

    if download_status["downloading"]:
        return jsonify({"error": "Ya hay una descarga en curso"}), 400

    try:
        data = request.json
        voice_id = data.get("voice_id")

        if not voice_id:
            return jsonify({"error": "No se especificó voz"}), 400

        # Buscar la voz en PIPER_VOICES
        voice_info = None
        for lang, voices in PIPER_VOICES.items():
            for voice in voices:
                v_id = f"{lang}-{voice['name']}-{voice['quality']}"
                if v_id == voice_id:
                    voice_info = {**voice, "lang": lang}
                    break
            if voice_info:
                break

        if not voice_info:
            return jsonify({"error": "Voz no encontrada"}), 404

        # Iniciar descarga en thread
        thread = threading.Thread(
            target=_download_tts_voice,
            args=(voice_info,)
        )
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "voice_id": voice_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts/voices/set', methods=['POST'])
def api_tts_set_voice():
    """Establecer la voz actual de TTS."""
    try:
        data = request.json
        voice_id = data.get("voice_id")

        if not voice_id:
            return jsonify({"error": "No se especificó voz"}), 400

        # Guardar en configuración
        config = get_config()
        config.set("tts.voice", voice_id)
        config.save()

        return jsonify({"success": True, "voice_id": voice_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts/test', methods=['POST'])
def api_tts_test():
    """Probar la voz de TTS actual."""
    try:
        # Ejecutar prueba de TTS
        import subprocess
        result = subprocess.run(
            ["piper-tts", "--help"],
            capture_output=True,
            timeout=5
        )

        # Generar un archivo de prueba
        test_file = MODELS_DIR / "tts" / "test_output.wav"
        config = get_config()
        voice = config.get("tts.voice", "es_ES-davefx-medium")

        # Comando para probar
        cmd = [
            "echo", "Hola, esta es una prueba de voz." | "piper-tts",
            "--model", f"{MODELS_DIR}/tts/{voice}.onnx",
            "--output", str(test_file)
        ]

        return jsonify({"success": True, "message": "Prueba iniciada"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

###############################################################################
# Funciones Auxiliares
###############################################################################
def _get_input_devices() -> List[Dict]:
    """Obtener dispositivos de entrada."""
    try:
        from audio.capture import AudioCapture
        capture = AudioCapture()
        return capture.list_devices()
    except:
        return []

def _get_output_devices() -> List[Dict]:
    """Obtener dispositivos de salida."""
    try:
        from audio.playback import AudioPlayback
        playback = AudioPlayback()
        return playback.list_devices()
    except:
        return []

def _get_llm_models() -> List[str]:
    """Obtener modelos LLM instalados (detecta directorios RKLLM)."""
    models_dir = MODELS_DIR / "llm"
    if not models_dir.exists():
        return []

    models = []

    # Detectar modelos RKLLM (directorios)
    for item in models_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Verificar que tenga archivos del modelo
            files = list(item.rglob("*"))
            if len(files) > 2:  # Al menos algunos archivos del modelo
                models.append(item.name)

    # También detectar modelos GGUF (archivos individuales)
    for f in models_dir.glob("*.gguf"):
        models.append(f.stem)

    return models

def _get_available_models() -> List[Dict]:
    """Obtener modelos disponibles para descargar (formato RKLLM para NPU)."""
    return [
        {
            "name": "qwen2-1.5b-rkllm",
            "url": "https://huggingface.co/FydeOS/Qwen2-1_5B_rkLLM",
            "size_mb": 1200,
            "recommended": True,
            "description": "Qwen2 1.5B - Optimizado para NPU RK3588",
            "format": "rkllm"
        },
        {
            "name": "qwen1.5-0.5b-rkllm",
            "url": "https://huggingface.co/FydeOS/Qwen1.5-0.5B_rkLLM",
            "size_mb": 400,
            "recommended": True,
            "description": "Qwen1.5 0.5B - Ultra ligero, rápido",
            "format": "rkllm"
        },
        {
            "name": "qwen1.5-1.8b-rkllm",
            "url": "https://huggingface.co/FydeOS/Qwen1.5-1_8B_rkLLM",
            "size_mb": 1400,
            "recommended": True,
            "description": "Qwen1.5 1.8B - Buen balance calidad/velocidad",
            "format": "rkllm"
        },
        {
            "name": "qwen-chat-1.8b-rkllm",
            "url": "https://huggingface.co/jxke/qwen-chat-1_8B_rkllm",
            "size_mb": 1400,
            "recommended": False,
            "description": "Qwen Chat 1.8B - Conversacional",
            "format": "rkllm"
        },
        {
            "name": "phi-2-rk3588",
            "url": "https://huggingface.co/Pelochus/ezrkllm-collection",
            "size_mb": 1100,
            "recommended": False,
            "description": "Phi-2 - Modelo compacto de Microsoft",
            "format": "rkllm"
        },
        {
            "name": "phi-3-mini-rk3588",
            "url": "https://huggingface.co/Pelochus/ezrkllm-collection",
            "size_mb": 1300,
            "recommended": False,
            "description": "Phi-3 Mini - Versión mejorada de Phi",
            "format": "rkllm"
        },
        {
            "name": "gemma-2b-rk3588",
            "url": "https://huggingface.co/Pelochus/ezrkllm-collection",
            "size_mb": 900,
            "recommended": False,
            "description": "Gemma 2B - Modelo compacto de Google",
            "format": "rkllm"
        },
        {
            "name": "tinyllama-v1-rk3588",
            "url": "https://huggingface.co/Pelochus/ezrkllm-collection",
            "size_mb": 700,
            "recommended": False,
            "description": "TinyLlama v1 - Muy ligero",
            "format": "rkllm"
        },
        {
            "name": "qwen1.5-4b-rkllm",
            "url": "https://huggingface.co/Pelochus/qwen1.5-chat-4B-rk3588",
            "size_mb": 2800,
            "recommended": False,
            "description": "Qwen1.5 4B - Mayor capacidad",
            "format": "rkllm"
        },
        {
            "name": "llama2-chat-7b-rk3588",
            "url": "https://huggingface.co/Pelochus/llama2-chat-7b-hf-rk3588",
            "size_mb": 4500,
            "recommended": False,
            "description": "Llama2 7B - Alta calidad (requiere más RAM)",
            "format": "rkllm"
        }
    ]

def _download_model(model: Dict):
    """Descarga un modelo en background usando git/huggingface-cli."""
    global download_status

    download_status["downloading"] = True
    download_status["model"] = model["name"]
    download_status["progress"] = 0
    download_status["error"] = None

    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / "llm" / model["name"]

        # Crear directorio si no existe
        model_path.mkdir(parents=True, exist_ok=True)

        download_status["progress"] = 10

        # Usar git clone con huggingface-hub
        import subprocess

        # Primero intentar con huggingface-cli
        cmd = [
            "huggingface-cli", "download",
            model["url"],
            "--local-dir", str(model_path),
            "--local-dir-use-symlinks", "False"
        ]

        logger.info(f"Descargando modelo: {model['name']}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        download_status["progress"] = 20

        # Esperar a que termine
        stdout, stderr = process.communicate(timeout=600)  # 10 min timeout

        if process.returncode != 0:
            # Si huggingface-cli falla, intentar con git
            logger.warning("huggingface-cli falló, intentando con git...")
            download_status["progress"] = 30

            # Extraer repo name de la URL
            repo = model["url"].replace("https://huggingface.co/", "")

            git_cmd = [
                "git", "clone",
                f"https://huggingface.co/{repo}",
                str(model_path)
            ]

            process2 = subprocess.Popen(
                git_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            process2.communicate(timeout=600)

            if process2.returncode != 0:
                raise Exception("Error descargando con git")

        download_status["progress"] = 90

        # Verificar que se descargó algo
        files = list(model_path.rglob("*"))
        if not files or len(files) < 3:
            raise Exception("No se descargaron archivos del modelo")

        download_status["progress"] = 100
        logger.info(f"Modelo {model['name']} descargado: {len(files)} archivos")

    except subprocess.TimeoutExpired:
        download_status["error"] = "Timeout de descarga"
        logger.error("Timeout descargando modelo")
    except Exception as e:
        download_status["error"] = str(e)
        logger.error(f"Error descargando modelo: {e}")
    finally:
        download_status["downloading"] = False

def _download_tts_voice(voice: Dict):
    """Descarga una voz de Piper TTS en background."""
    global download_status

    download_status["downloading"] = True
    download_status["model"] = voice['name']
    download_status["type"] = "tts"
    download_status["progress"] = 0
    download_status["error"] = None

    try:
        tts_dir = MODELS_DIR / "tts"
        tts_dir.mkdir(parents=True, exist_ok=True)

        voice_id = f"{voice['lang']}-{voice['name']}-{voice['quality']}"
        onnx_path = tts_dir / f"{voice_id}.onnx"
        json_path = tts_dir / f"{voice_id}.onnx.json"

        download_status["progress"] = 10

        # Descargar archivo .onnx
        logger.info(f"Descargando voz TTS: {voice['name']} ({voice['lang']})")

        response = requests.get(voice['url'], stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        download_status["progress"] = 20

        with open(onnx_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        # Progreso del 20 al 70 para el ONNX
                        download_status["progress"] = 20 + int((downloaded / total_size) * 50)

        download_status["progress"] = 75

        # Descargar archivo .json
        response_json = requests.get(voice['url_json'], stream=True, timeout=30)
        response_json.raise_for_status()

        with open(json_path, 'wb') as f:
            for chunk in response_json.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        download_status["progress"] = 90

        # Verificar que se descargaron ambos archivos
        if not onnx_path.exists() or not json_path.exists():
            raise Exception("No se descargaron todos los archivos")

        download_status["progress"] = 100
        logger.info(f"Voz TTS {voice['name']} descargada correctamente")

    except requests.TimeoutExpired:
        download_status["error"] = "Timeout de descarga"
        logger.error("Timeout descargando voz TTS")
    except Exception as e:
        download_status["error"] = str(e)
        logger.error(f"Error descargando voz TTS: {e}")
    finally:
        download_status["downloading"] = False
        download_status["type"] = None

def _service_status(service: str) -> Dict:
    """Obtener estado de un servicio."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True
        )
        active = result.stdout.strip() == "active"

        result2 = subprocess.run(
            ["systemctl", "is-enabled", service],
            capture_output=True,
            text=True
        )
        enabled = result2.stdout.strip() == "enabled"

        return {"active": active, "enabled": enabled}
    except:
        return {"active": False, "enabled": False}

def _get_cpu_usage() -> float:
    """Obtener uso de CPU."""
    try:
        result = subprocess.run(
            ["top", "-bn1", "-p", "1"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if '%Cpu(s):' in line:
                # Extraer el valor de user
                parts = line.split(',')
                for part in parts:
                    if 'user' in part:
                        return float(part.split()[0])
        return 0.0
    except:
        return 0.0

def _get_memory_usage() -> Dict:
    """Obtener uso de memoria."""
    try:
        result = subprocess.run(
            ["free", "-m"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            return {
                "total_mb": int(parts[1]),
                "used_mb": int(parts[2]),
                "free_mb": int(parts[3]),
                "percent": round((int(parts[2]) / int(parts[1])) * 100, 1)
            }
        return {}
    except:
        return {}

def _get_uptime() -> str:
    """Obtener uptime del sistema."""
    try:
        result = subprocess.run(
            ["uptime", "-p"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip().replace("up ", "")
    except:
        return "Desconocido"


###############################################################################
# Error Handlers
###############################################################################
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "No encontrado"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Error del servidor"}), 500


###############################################################################
# Main
###############################################################################
if __name__ == '__main__':
    # Setup logging
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging(level="INFO", log_dir=str(LOGS_DIR))

    logger.info("Iniciando servidor web...")

    # Iniciar servidor
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
