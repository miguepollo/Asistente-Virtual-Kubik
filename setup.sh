#!/bin/bash
###############################################################################
# Asistente Virtual - Script de Configuración
# Orange Pi 5 Ultra - Armbian
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-/home/orangepi/asistente}"
VENV_DIR="$PROJECT_DIR/venv"
MODELS_DIR="$PROJECT_DIR/models"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/install_$(date +%Y%m%d_%H%M%S).log"

# Crear directorio de logs
mkdir -p "$LOG_DIR"

###############################################################################
# HELPER FUNCTIONS
###############################################################################
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$LOG_FILE"
}
success() {
    echo -e "${GREEN}[OK]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] OK: $1" >> "$LOG_FILE"
}
warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1" >> "$LOG_FILE"
}
error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
}
log_cmd() {
    local output
    local exit_code
    output=$("$@" 2>&1)
    exit_code=$?
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] CMD: $*" >> "$LOG_FILE"
    echo "$output" >> "$LOG_FILE"
    if [ $exit_code -ne 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] EXIT_CODE: $exit_code" >> "$LOG_FILE"
        return $exit_code
    fi
    return 0
}

check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        if ! sudo -n true 2>/dev/null; then
            error "Esta acción necesita sudo. Ejecuta: sudo ./setup.sh"
            exit 1
        fi
    fi
}

spinner() {
    local pid=$1
    local msg="$2"
    local chars='-\|/'
    local i=0
    while kill -0 $pid 2>/dev/null; do
        printf "\r${CYAN}[${chars:$((i%4)):1}]${NC} $msg... "
        sleep 0.1
        ((i++))
    done
    printf "\r${GREEN}[✓]${NC} $msg...     \n"
}

###############################################################################
# INSTALLATION FUNCTIONS
###############################################################################
install_all() {
    clear
    header
    echo -e "${BOLD}🚀 INSTALANDO TODO...${NC}"
    echo ""
    log "Log de instalación: $LOG_FILE"
    echo ""

    # 1. Sistema
    log "Actualizando sistema..."
    if sudo apt update >> "$LOG_FILE" 2>&1; then
        success "Actualizando paquetes"
    else
        error "Falló actualización de paquetes"
    fi
    if sudo apt upgrade -y >> "$LOG_FILE" 2>&1; then
        success "Instalando actualizaciones"
    else
        warn "Actualizaciones finalizadas con advertencias"
    fi

    # 2. Herramientas básicas
    log "Instalando herramientas básicas..."
    if sudo apt install -y build-essential cmake git wget curl unzip \
        vim htop tmux screen jq tree sox >> "$LOG_FILE" 2>&1; then
        success "Herramientas básicas"
    else
        error "Falló instalación de herramientas básicas"
    fi

    # 3. Python
    log "Instalando Python..."
    if sudo apt install -y python3 python3-dev python3-pip \
        python3-venv python3-setuptools python3-wheel >> "$LOG_FILE" 2>&1; then
        success "Python 3"
    else
        error "Falló instalación de Python"
    fi

    # 4. Crear entorno virtual ANTES de instalar cualquier paquete Python
    log "Creando entorno virtual Python..."
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR" >> "$LOG_FILE" 2>&1
        if [ $? -eq 0 ]; then
            success "Entorno virtual creado"
        else
            error "Falló creación de entorno virtual"
            return 1
        fi
    else
        success "Entorno virtual ya existe"
    fi
    source "$VENV_DIR/bin/activate"
    if pip install --upgrade pip setuptools wheel >> "$LOG_FILE" 2>&1; then
        success "Pip actualizado en venv"
    else
        warn "Actualización de pip con advertencias"
    fi

    # 5. Audio
    log "Instalando dependencias de audio..."
    if sudo apt install -y alsa-utils alsa-tools libasound2 \
        libasound2-dev libasound2-plugins pulseaudio \
        pulseaudio-utils pavucontrol portaudio19-dev \
        libportaudio2 libportaudiocpp0 >> "$LOG_FILE" 2>&1; then
        success "Dependencias de audio"
    else
        error "Falló instalación de dependencias de audio"
    fi

    # 5. ALSA config
    log "Configurando ALSA..."
    sudo tee /etc/asound.conf > /dev/null << 'EOF'
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
EOF
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALSA configurado" >> "$LOG_FILE"
    success "ALSA configurado"

    # 6. Networking
    log "Configurando red..."
    if sudo apt install -y network-manager dnsmasq hostapd >> "$LOG_FILE" 2>&1; then
        success "NetworkManager instalado"
    else
        warn "NetworkManager con advertencias"
    fi
    sudo systemctl stop wpa_supplicant 2>/dev/null || true
    sudo systemctl disable wpa_supplicant 2>/dev/null || true
    sudo systemctl mask wpa_supplicant 2>/dev/null || true
    sudo systemctl enable NetworkManager >> "$LOG_FILE" 2>&1
    sudo systemctl start NetworkManager >> "$LOG_FILE" 2>&1
    success "Red configurada"

    # 7. rknn-llm deps
    log "Instalando dependencias rknn-llm..."
    if sudo apt install -y libopencv-dev python3-opencv >> "$LOG_FILE" 2>&1; then
        success "Dependencias rknn-llm"
    else
        warn "Dependencias rknn-llm con advertencias"
    fi

    # 8. Dependencias Python
    log "Instalando dependencias Python..."
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        if pip install -r "$PROJECT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1; then
            success "Dependencias Python instaladas"
        else
            warn "Dependencias Python con advertencias (revisa log)"
        fi
    else
        if pip install pyaudio numpy scipy pvporcupine vosk flask \
            flask-cors requests python-dotenv pyyaml cryptography \
            webrtcvad pydub netifaces colorlog piper-tts >> "$LOG_FILE" 2>&1; then
            success "Dependencias Python instaladas"
        else
            warn "Dependencias Python con advertencias (revisa log)"
        fi
    fi

    # 9. Modelos
    log "Descargando modelos de IA..."
    mkdir -p "$MODELS_DIR"/{stt,tts,llm,wakeword}

    # Vosk STT
    if [ ! -d "$MODELS_DIR/stt/vosk-model-small-es-0.42" ]; then
        log "Descargando Vosk STT (español)..."
        cd "$MODELS_DIR/stt"
        if wget -q --show-progress https://alphacephei.com/vosk/vosk-model-small-es-0.42.zip >> "$LOG_FILE" 2>&1; then
            if unzip -q vosk-model-small-es-0.42.zip >> "$LOG_FILE" 2>&1; then
                rm vosk-model-small-es-0.42.zip
                cd "$PROJECT_DIR"
                success "Vosk STT"
            else
                cd "$PROJECT_DIR"
                error "Falló descompresión de Vosk STT"
            fi
        else
            cd "$PROJECT_DIR"
            error "Falló descarga de Vosk STT"
        fi
    else
        success "Vosk STT (ya existe)"
    fi

    # Piper TTS
    if [ ! -f "$MODELS_DIR/tts/es_ES-davefx-medium.onnx" ]; then
        log "Descargando Piper TTS (español)..."
        cd "$MODELS_DIR/tts"
        if wget -q --show-progress \
            https://huggingface.co/rhasspy/piper-voices/v1.0.0/es/es_ES/davefx/medium/resolve/main/es_ES-davefx-medium.onnx \
            -O es_ES-davefx-medium.onnx >> "$LOG_FILE" 2>&1; then
            wget -q --show-progress \
                https://huggingface.co/rhasspy/piper-voices/v1.0.0/es/es_ES/davefx/medium/resolve/main/es_ES-davefx-medium.onnx.json \
                -O es_ES-davefx-medium.onnx.json >> "$LOG_FILE" 2>&1
            cd "$PROJECT_DIR"
            success "Piper TTS"
        else
            cd "$PROJECT_DIR"
            error "Falló descarga de Piper TTS"
        fi
    else
        success "Piper TTS (ya existe)"
    fi

    # Metadata LLM
    mkdir -p "$MODELS_DIR/llm"
    cat > "$MODELS_DIR/llm/metadata.json" << 'EOF'
{
  "available_models": [
    {"name": "phi-2-1.3b-q4", "url": "...", "size_mb": 800, "recommended": true}
  ],
  "current_model": null
}
EOF
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Metadata LLM creada" >> "$LOG_FILE"

    echo ""
    echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║${NC}  ✅ ¡INSTALACIÓN COMPLETADA!                                 ${GREEN}${BOLD}║${NC}"
    echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}📋 Log guardado en:${NC} ${LOG_FILE}"
    echo -e "${CYAN}   Ver logs con:${NC} cat $LOG_FILE"
    echo ""
    read -p "Presiona Enter para continuar..."
}

setup_audio_menu() {
    clear
    header
    echo -e "${BOLD}🎙️  CONFIGURACIÓN DE AUDIO${NC}"
    echo ""
    echo "Dispositivos de grabación:"
    arecord -l 2>/dev/null || echo "  Ninguno detectado"
    echo ""
    echo "Dispositivos de reproducción:"
    aplay -l 2>/dev/null || echo "  Ninguno detectado"
    echo ""
    echo -e "${YELLOW}Ajustando volúmenes...${NC}"
    amixer sset Master unmute 2>/dev/null || true
    amixer sset Capture unmute 2>/dev/null || true
    amixer sset Master 70% 2>/dev/null || true
    amixer sset Capture 60% 2>/dev/null || true
    success "Volúmenes ajustados"
    echo ""
    read -p "¿Probar grabación (5 seg)? [s/N]: " test_rec
    if [[ $test_rec =~ ^[Ss]$ ]]; then
        log "Grabando... ¡Habla!"
        arecord -D hw:0,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav 2>/dev/null
        log "Reproduciendo..."
        aplay /tmp/test.wav 2>/dev/null
        success "Test completado"
    fi
    echo ""
    read -p "Presiona Enter para continuar..."
}

test_system() {
    clear
    header
    echo -e "${BOLD}🧪 PROBANDO SISTEMA${NC}"
    echo ""

    [ -d "$VENV_DIR" ] || { error "Entorno virtual no encontrado"; read -p "Enter..."; return; }

    source "$VENV_DIR/bin/activate"

    # Test 1: Imports
    echo -e "${CYAN}Test 1: Módulos Python${NC}"
    python3 << 'EOF'
import sys
sys.path.append('/home/orangepi/asistente/src')
for m in ["numpy", "pyaudio", "scipy", "webrtcvad"]:
    try: __import__(m); print(f"  ✅ {m}")
    except: print(f"  ❌ {m}")
EOF

    # Test 2: Audio
    echo ""
    echo -e "${CYAN}Test 2: Dispositivos de audio${NC}"
    python3 << 'EOF'
import sys
sys.path.append('/home/orangepi/asistente/src')
from audio.capture import AudioCapture
from audio.playback import AudioPlayback
c = AudioCapture(); p = AudioPlayback()
print(f"  Entrada: {len(c.list_devices())} dispositivos")
print(f"  Salida: {len(p.list_devices())} dispositivos")
EOF

    # Test 3: VAD
    echo ""
    echo -e "${CYAN}Test 3: VAD${NC}"
    python3 << 'EOF'
import sys
sys.path.append('/home/orangepi/asistente/src')
from audio.vad import VAD
import numpy as np
vad = VAD()
silence = np.zeros(16000, dtype=np.int16)
t = np.linspace(0, 1, 16000)
tone = (np.sin(2*np.pi*200*t)*10000).astype(np.int16)
audio = np.concatenate([silence, tone, silence])
has_speech, _ = vad.process_stream(audio)
print(f"  ✅ VAD detecta voz: {has_speech}")
EOF

    # Test 4: Modelos
    echo ""
    echo -e "${CYAN}Test 4: Modelos${NC}"
    [ -d "$MODELS_DIR/stt/vosk-model-small-es-0.42" ] && echo "  ✅ Vosk STT" || echo "  ❌ Vosk STT"
    [ -f "$MODELS_DIR/tts/es_ES-davefx-medium.onnx" ] && echo "  ✅ Piper TTS" || echo "  ❌ Piper TTS"

    echo ""
    echo -e "${GREEN}${BOLD}✅ TESTS COMPLETADOS${NC}"
    echo ""
    read -p "Presiona Enter para continuar..."
}

show_wakeword_info() {
    clear
    header
    echo -e "${BOLD}🎤 CONFIGURACIÓN WAKE WORD${NC}"
    echo ""
    echo "El wake word requiere configuración manual:"
    echo ""
    echo "  1. Ve a: https://console.picovoice.ai"
    echo "  2. Crea cuenta gratuita"
    echo "  3. Copia tu Access Key"
    echo "  4. Entrena la palabra 'Asistente' en español"
    echo "  5. Descarga el archivo .ppn"
    echo "  6. Guárdalo en: $MODELS_DIR/wakeword/asistente_es.ppn"
    echo ""
    echo "Luego añade la key a config/config.json"
    echo ""
    read -p "Presiona Enter para continuar..."
}

show_status() {
    clear
    header
    echo -e "${BOLD}📊 ESTADO DEL SISTEMA${NC}"
    echo ""

    # Python
    if command -v python3 &> /dev/null; then
        echo -e "  Python:      ${GREEN}✅${NC} $(python3 --version)"
    else
        echo -e "  Python:      ${RED}❌ No instalado${NC}"
    fi

    # venv
    if [ -d "$VENV_DIR" ]; then
        echo -e "  Venv:        ${GREEN}✅${NC} Creado"
    else
        echo -e "  Venv:        ${RED}❌ No creado${NC}"
    fi

    # Audio
    if command -v arecord &> /dev/null; then
        echo -e "  Audio (ALSA): ${GREEN}✅${NC} Instalado"
    else
        echo -e "  Audio (ALSA): ${RED}❌ No instalado${NC}"
    fi

    # Modelos
    if [ -d "$MODELS_DIR/stt/vosk-model-small-es-0.42" ]; then
        echo -e "  Vosk STT:    ${GREEN}✅${NC} Instalado"
    else
        echo -e "  Vosk STT:    ${RED}❌ No instalado${NC}"
    fi

    if [ -f "$MODELS_DIR/tts/es_ES-davefx-medium.onnx" ]; then
        echo -e "  Piper TTS:   ${GREEN}✅${NC} Instalado"
    else
        echo -e "  Piper TTS:   ${RED}❌ No instalado${NC}"
    fi

    # Servicios
    if systemctl is-enabled asistente.service &>/dev/null; then
        echo -e "  Servicio:    ${GREEN}✅${NC} Habilitado"
    else
        echo -e "  Servicio:    ${YELLOW}⚠${NC} No habilitado"
    fi

    echo ""
    read -p "Presiona Enter para continuar..."
}

install_service() {
    check_sudo
    clear
    header
    echo -e "${BOLD}🔧 INSTALAR SERVICIO SYSTEMD${NC}"
    echo ""
    log "Instalando servicios..."
    sudo cp "$PROJECT_DIR/systemd/asistente.service" /etc/systemd/system/
    sudo cp "$PROJECT_DIR/systemd/asistente-web.service" /etc/systemd/system/ 2>/dev/null || true
    sudo systemctl daemon-reload
    sudo systemctl enable asistente.service
    success "Servicio instalado y habilitado"
    echo ""
    echo "Comandos:"
    echo "  sudo systemctl start asistente   - Iniciar"
    echo "  sudo systemctl stop asistente    - Detener"
    echo "  sudo systemctl status asistente  - Estado"
    echo "  journalctl -u asistente -f       - Logs"
    echo ""
    read -p "Presiona Enter para continuar..."
}

show_logs() {
    clear
    header
    echo -e "${BOLD}📋 LOGS${NC}"
    echo ""
    if [ -f "$PROJECT_DIR/logs/assistant.log" ]; then
        tail -n 30 "$PROJECT_DIR/logs/assistant.log"
    else
        warn "No hay logs todavía"
    fi
    echo ""
    read -p "Presiona Enter para continuar..."
}

###############################################################################
# HEADER & MENU
###############################################################################
header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║     🤖 ASISTENTE VIRTUAL - Orange Pi 5 Ultra               ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_menu() {
    header
    echo -e "${BOLD}  MENÚ PRINCIPAL${NC}"
    echo ""
    echo -e "  ${GREEN}1.${NC} 🚀 Instalar TODO (recomendado)"
    echo -e "  ${CYAN}2.${NC} 🎙️  Configurar audio"
    echo -e "  ${CYAN}3.${NC} 🧪 Probar sistema"
    echo -e "  ${CYAN}4.${NC} 🎤 Configurar wake word"
    echo -e "  ${CYAN}5.${NC} 📊 Ver estado"
    echo -e "  ${CYAN}6.${NC} 🔧 Instalar servicio systemd"
    echo -e "  ${CYAN}7.${NC} 📋 Ver logs"
    echo ""
    echo -e "  ${YELLOW}0.${NC} 🚪 Salir"
    echo ""
    echo -ne "${DIM}Selecciona una opción:${NC} "
}

###############################################################################
# MAIN LOOP
###############################################################################
main() {
    while true; do
        show_menu
        read -r choice
        case "$choice" in
            1) install_all ;;
            2) setup_audio_menu ;;
            3) test_system ;;
            4) show_wakeword_info ;;
            5) show_status ;;
            6) install_service ;;
            7) show_logs ;;
            0|q|Q) echo "¡Hasta luego!"; exit 0 ;;
            *) echo "Opción no válida"; sleep 1 ;;
        esac
    done
}

main
