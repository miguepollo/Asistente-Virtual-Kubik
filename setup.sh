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
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
VENV_DIR="$PROJECT_DIR/venv"
MODELS_DIR="$PROJECT_DIR/models"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/install_$(date +%Y%m%d_%H%M%S).log"

# Python executable en venv
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"
SRC_DIR="$PROJECT_DIR/src"

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
# RKLLM RUNTIME INSTALLATION
###############################################################################
install_rkllm_runtime() {
    log "Instalando RKLLM Runtime para Rockchip NPU..."

    local RKLLM_VERSION="1.2.3"
    local RKLLM_REPO="https://github.com/airockchip/rknn-llm"
    local BUILD_DIR="$PROJECT_DIR/build/rkllm"
    local LIB_INSTALL_DIR="/usr/local/lib"
    local INCLUDE_INSTALL_DIR="/usr/local/include"

    # Crear directorio de build
    mkdir -p "$BUILD_DIR"

    # Verificar si ya está instalado
    if [ -f "$LIB_INSTALL_DIR/librkllmrt.so" ]; then
        success "RKLLM Runtime ya está instalado"
        return 0
    fi

    # Descargar el release si no existe
    if [ ! -d "$BUILD_DIR/rknn-llm" ]; then
        log "Clonando repositorio rknn-llm..."
        if git clone --depth 1 "$RKLLM_REPO" "$BUILD_DIR/rknn-llm" >> "$LOG_FILE" 2>&1; then
            success "Repositorio clonado"
        else
            warn "No se pudo clonar el repositorio. Intentando descarga directa..."

            # Alternativa: descargar release como zip
            local zip_file="$BUILD_DIR/rknn-llm-release.zip"
            if wget -qO "$zip_file" "$RKLLM_REPO/archive/refs/tags/release-$RKLLM_VERSION.zip" >> "$LOG_FILE" 2>&1; then
                unzip -q "$zip_file" -d "$BUILD_DIR" >> "$LOG_FILE" 2>&1
                mv "$BUILD_DIR/rknn-llm-release-$RKLLM_VERSION" "$BUILD_DIR/rknn-llm"
                rm "$zip_file"
                success "Release descargado"
            else
                warn "No se pudo descargar RKLLM Runtime (opcional para LLM)"
                return 1
            fi
        fi
    fi

    # Copiar runtime para aarch64
    local RUNTIME_PATH="$BUILD_DIR/rknn-llm/rkllm-runtime/Linux/librkllm_api/aarch64"

    if [ ! -d "$RUNTIME_PATH" ]; then
        warn "No se encontró el runtime para aarch64. Puede que necesites compilarlo."
        return 1
    fi

    # Instalar biblioteca
    log "Instalando biblioteca librkllmrt.so..."
    if sudo cp "$RUNTIME_PATH/librkllmrt.so" "$LIB_INSTALL_DIR/" >> "$LOG_FILE" 2>&1; then
        sudo chmod 644 "$LIB_INSTALL_DIR/librkllmrt.so"
        sudo ldconfig >> "$LOG_FILE" 2>&1
        success "Biblioteca instalada en $LIB_INSTALL_DIR"
    else
        warn "No se pudo instalar la biblioteca"
        return 1
    fi

    # Instalar headers
    if [ -f "$RUNTIME_PATH/include/rkllm_api.h" ]; then
        sudo mkdir -p "$INCLUDE_INSTALL_DIR"
        sudo cp "$RUNTIME_PATH/include/rkllm_api.h" "$INCLUDE_INSTALL_DIR/" >> "$LOG_FILE" 2>&1
        success "Headers instalados en $INCLUDE_INSTALL_DIR"
    fi

    # Crear symlink para el proyecto
    mkdir -p "$PROJECT_DIR/lib"
    ln -sf "$LIB_INSTALL_DIR/librkllmrt.so" "$PROJECT_DIR/lib/librkllmrt.so"

    success "RKLLM Runtime instalado correctamente"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] RKLLM Runtime instalado" >> "$LOG_FILE"
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
    if "$PIP" install --upgrade pip setuptools wheel >> "$LOG_FILE" 2>&1; then
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

    # 7.1. RKLLM Runtime - Biblioteca nativa para LLM en NPU de Rockchip
    install_rkllm_runtime

    # 8. Dependencias Python
    log "Instalando dependencias Python..."
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        if "$PIP" install -r "$PROJECT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1; then
            success "Dependencias Python instaladas"
        else
            warn "Dependencias Python con advertencias (revisa log)"
        fi
    else
        if "$PIP" install pyaudio numpy scipy pvporcupine vosk flask \
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
        if wget -q --show-progress https://huggingface.co/localstack/vosk-models/resolve/main/vosk-model-small-es-0.42.zip >> "$LOG_FILE" 2>&1; then
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
            https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx \
            -O es_ES-davefx-medium.onnx >> "$LOG_FILE" 2>&1; then
            wget -q --show-progress \
                https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json \
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

    # Preguntar si configurar Porcupine ahora
    echo -e "${YELLOW}🎤 ¿Quieres configurar el wake word (Porcupine) ahora?${NC}"
    read -p "Requiere una Access Key de Picovoice [s/N]: " config_porcupine
    if [[ $config_porcupine =~ ^[Ss]$ ]]; then
        setup_porcupine
    fi
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

    # Test 1: Imports básicos
    echo -e "${CYAN}Test 1: Módulos Python${NC}"
    "$PYTHON" << EOF
import sys
sys.path.insert(0, "$SRC_DIR")
for m in ["numpy", "pyaudio", "scipy", "webrtcvad"]:
    try: __import__(m); print(f"  ✅ {m}")
    except: print(f"  ❌ {m}")
EOF

    # Test 2: Audio
    echo ""
    echo -e "${CYAN}Test 2: Dispositivos de audio${NC}"
    arecord -l 2>/dev/null && echo "  ✅ Dispositivos de entrada detectados" || echo "  ❌ Sin dispositivos de entrada"
    aplay -l 2>/dev/null && echo "  ✅ Dispositivos de salida detectados" || echo "  ❌ Sin dispositivos de salida"

    # Test 3: Módulos del proyecto
    echo ""
    echo -e "${CYAN}Test 3: Módulos del proyecto${NC}"
    "$PYTHON" << EOF
import sys
sys.path.insert(0, "$SRC_DIR")
try:
    from audio.capture import AudioCapture
    from audio.playback import AudioPlayback
    from audio.vad import VAD
    print(f"  ✅ audio.capture")
    print(f"  ✅ audio.playback")
    print(f"  ✅ audio.vad")
except Exception as e:
    print(f"  ❌ Módulos audio: {e}")
EOF

    # Test 4: VAD
    echo ""
    echo -e "${CYAN}Test 4: VAD${NC}"
    "$PYTHON" << EOF
import sys
sys.path.insert(0, "$SRC_DIR")
try:
    from audio.vad import VAD
    import numpy as np
    vad = VAD()
    silence = np.zeros(16000, dtype=np.int16)
    t = np.linspace(0, 1, 16000)
    tone = (np.sin(2*np.pi*200*t)*10000).astype(np.int16)
    audio = np.concatenate([silence, tone, silence])
    has_speech, _ = vad.process_stream(audio)
    print(f"  ✅ VAD detecta voz: {has_speech}")
except Exception as e:
    print(f"  ❌ VAD error: {e}")
EOF

    # Test 5: Modelos
    echo ""
    echo -e "${CYAN}Test 5: Modelos${NC}"
    [ -d "$MODELS_DIR/stt/vosk-model-small-es-0.42" ] && echo "  ✅ Vosk STT" || echo "  ❌ Vosk STT"
    [ -f "$MODELS_DIR/tts/es_ES-davefx-medium.onnx" ] && echo "  ✅ Piper TTS" || echo "  ❌ Piper TTS"

    echo ""
    echo -e "${GREEN}${BOLD}✅ TESTS COMPLETADOS${NC}"
    echo ""
    read -p "Presiona Enter para continuar..."
}

setup_porcupine() {
    clear
    header
    echo -e "${BOLD}🎤 CONFIGURACIÓN WAKE WORD (PORCUPINE)${NC}"
    echo ""
    echo "Porcupine requiere una Access Key de Picovoice."
    echo ""
    echo "  1. Ve a: https://console.picovoice.ai"
    echo "  2. Crea cuenta gratuita (Free Tier)"
    echo "  3. Copia tu Access Key"
    echo ""
    echo -e "${CYAN}Opciones de wake word:${NC}"
    echo "  - Keywords predefinidas (porcupine, computer, jarvis, etc.)"
    echo "  - Keywords personalizadas (.ppn) - crea en https://picovoice.ai/console/ppn"
    echo ""

    # Verificar si ya existe una API key
    local current_key=""
    if [ -f "$PROJECT_DIR/.env" ]; then
        current_key=$(grep "^PICOVOCICE_ACCESS_KEY=" "$PROJECT_DIR/.env" 2>/dev/null | cut -d'=' -f2)
        if [ -n "$current_key" ] && [ "$current_key" != "your_access_key_here" ]; then
            echo -e "${GREEN}Access Key actual:${NC} ${current_key:0:10}...${current_key: -4}"
            echo ""
            read -p "¿Usar la key existente? [S/n]: " use_existing
            if [[ ! $use_existing =~ ^[Nn]$ ]]; then
                api_key="$current_key"
            else
                api_key=""
            fi
        fi
    fi

    if [ -z "$api_key" ]; then
        echo ""
        read -p "Introduce tu Access Key de Picovoice: " api_key

        if [ -z "$api_key" ]; then
            warn "No se introdujo Access Key"
            read -p "Presiona Enter para continuar..."
            return 1
        fi

        # Crear o actualizar .env
        if [ -f "$PROJECT_DIR/.env" ]; then
            if grep -q "^PICOVOCICE_ACCESS_KEY=" "$PROJECT_DIR/.env"; then
                sed -i "s|^PICOVOCICE_ACCESS_KEY=.*|PICOVOCICE_ACCESS_KEY=$api_key|" "$PROJECT_DIR/.env"
            else
                echo "PICOVOCICE_ACCESS_KEY=$api_key" >> "$PROJECT_DIR/.env"
            fi
        else
            mkdir -p "$PROJECT_DIR"
            echo "PICOVOCICE_ACCESS_KEY=$api_key" > "$PROJECT_DIR/.env"
        fi
        success "Access Key guardada en .env"
    fi

    # Configurar keywords
    echo ""
    echo -e "${BOLD}CONFIGURAR PALABRAS DE ACTIVACIÓN${NC}"
    echo ""
    echo "Puedes agregar múltiples palabras. Cada una debe:"
    echo "  - Ser predefinida de Porcupine, O"
    echo "  - Ser un archivo .ppn personalizado en $MODELS_DIR/wakeword/"
    echo ""

    # Array para keywords
    declare -a keywords_list=()

    while true; do
        echo ""
        echo "Palabra actual:"
        [ ${#keywords_list[@]} -eq 0 ] && echo "  (ninguna configurada)" || printf "  - %s\n" "${keywords_list[@]}"
        echo ""
        echo "Agregar nueva palabra:"
        echo "  1) porcupine (predefinida, español)"
        echo "  2) computer (predefinida, inglés)"
        echo "  3) jarvis (predefinida, inglés)"
        echo "  4) alexa (predefinida, inglés)"
        echo "  5) hey google (predefinida, inglés)"
        echo "  6) Archivo .ppn personalizado"
        echo "  0) Terminar y guardar"
        echo ""
        read -p "Opción: " kw_opt

        case "$kw_opt" in
            1)
                keywords_list+=("porcupine:builtin:es:0.5")
                success "Agregado: porcupine"
                ;;
            2)
                keywords_list+=("computer:builtin:en:0.5")
                success "Agregado: computer"
                ;;
            3)
                keywords_list+=("jarvis:builtin:en:0.5")
                success "Agregado: jarvis"
                ;;
            4)
                keywords_list+=("alexa:builtin:en:0.5")
                success "Agregado: alexa"
                ;;
            5)
                keywords_list+=("hey google:builtin:en:0.5")
                success "Agregado: hey google"
                ;;
            6)
                read -p "Ruta al archivo .ppn: " ppn_path
                if [ -f "$ppn_path" ]; then
                    read -p "Nombre para la palabra: " ppn_name
                    read -p "Sensibilidad (0.0-1.0) [0.5]: " ppn_sens
                    ppn_sens=${ppn_sens:-0.5}
                    keywords_list+=("${ppn_name}:${ppn_path}:custom:${ppn_sens}")
                    success "Agregado: ${ppn_name}"
                else
                    error "Archivo no encontrado: $ppn_path"
                fi
                ;;
            0)
                if [ ${#keywords_list[@]} -eq 0 ]; then
                    warn "Debes agregar al menos una palabra"
                    continue
                fi
                break
                ;;
            *)
                echo "Opción no válida"
                ;;
        esac
    done

    # Construir JSON de keywords
    local keywords_json="["
    local first=true
    for kw in "${keywords_list[@]}"; do
        IFS=':' read -r name path lang sens <<< "$kw"
        if [ "$first" = true ]; then
            first=false
        else
            keywords_json+=","
        fi

        # Para builtin, usar path especial
        if [ "$lang" = "builtin" ]; then
            keywords_json+="{\"name\":\"$name\",\"path\":\"builtin:$lang\",\"sensitivity\":$sens}"
        else
            # Escapar barras en path
            path_escaped=$(echo "$path" | sed 's/\\/\\\\/g')
            keywords_json+="{\"name\":\"$name\",\"path\":\"$path_escaped\",\"sensitivity\":$sens}"
        fi
    done
    keywords_json+="]"

    # Actualizar config.json
    if [ -f "$PROJECT_DIR/config/config.json" ]; then
        "$PYTHON" << EOF
import json
config_path = "$PROJECT_DIR/config/config.json"
with open(config_path, 'r') as f:
    config = json.load(f)

# Asegurar que wake_word existe
if 'wake_word' not in config:
    config['wake_word'] = {}

config['wake_word']['enabled'] = True
config['wake_word']['keywords'] = $keywords_json

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
EOF
        success "Configuración actualizada"
        echo ""
        echo -e "${CYAN}Palabras configuradas:${NC}"
        for kw in "${keywords_list[@]}"; do
            IFS=':' read -r name path lang sens <<< "$kw"
            echo "  - $name"
        done
    else
        error "No se encontró config.json"
    fi

    echo ""
    echo -e "${GREEN}${BOLD}✅ Porcupine configurado correctamente${NC}"
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
        if [ -x "$PYTHON" ]; then
            echo -e "    └─ Versión: $($PYTHON --version)"
        fi
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

    # Porcupine
    if [ -f "$PROJECT_DIR/.env" ]; then
        pv_key=$(grep "^PICOVOCICE_ACCESS_KEY=" "$PROJECT_DIR/.env" 2>/dev/null | cut -d'=' -f2)
        if [ -n "$pv_key" ] && [ "$pv_key" != "your_access_key_here" ]; then
            # Mostrar keywords configurados
            pv_keywords=$("$PYTHON" -c "
import json
try:
    with open('$PROJECT_DIR/config/config.json', 'r') as f:
        config = json.load(f)
    keywords = config.get('wake_word', {}).get('keywords', [])
    if keywords:
        kw_names = [kw.get('name', '?') for kw in keywords]
        print(', '.join(kw_names))
    else:
        print('(ninguno)')
except:
        print('(error)')
" 2>/dev/null)
            echo -e "  Porcupine:  ${GREEN}✅${NC} Configurado (${pv_key:0:8}...)"
            echo -e "    Keywords: ${CYAN}${pv_keywords}${NC}"
        else
            echo -e "  Porcupine:  ${YELLOW}⚠${NC} Sin API key"
        fi
    else
        echo -e "  Porcupine:  ${RED}❌ No configurado${NC}"
    fi

    # RKLLM Runtime
    if [ -f "/usr/local/lib/librkllmrt.so" ] || [ -f "/usr/lib/librkllmrt.so" ]; then
        echo -e "  RKLLM RT:   ${GREEN}✅${NC} Instalado (NPU LLM)"
    else
        echo -e "  RKLLM RT:   ${YELLOW}⚠${NC} No instalado (opcional)"
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

create_custom_wakeword() {
    clear
    header
    echo -e "${BOLD}🎤 CREAR WAKE WORD PERSONALIZADO${NC}"
    echo ""
    echo "Este generador crea modelos de wake word personalizados usando:"
    echo "  - Piper TTS para generar muestras de voz en español"
    echo "  - openWakeWord para entrenar el modelo"
    echo ""
    echo "El proceso puede tardar varios minutos..."
    echo ""
    source venv/bin/activate
    # Verificar dependencias
    if ! command -v piper-tts &> /dev/null && ! "$PIP" show piper-tts &> /dev/null; then
        warn "Piper TTS no está instalado. Instalando..."
        "$PIP" install piper-tts >> "$LOG_FILE" 2>&1
    fi

    # Pedir palabra
    while true; do
        read -p "Introduce la palabra (ej: asistente, hola, hey): " word
        if [ -n "$word" ]; then
            # Validar que sea solo letras y espacios
            if [[ "$word" =~ ^[a-zA-ZáéíóúñÁÉÍÓÚÑ[:space:]]+$ ]]; then
                break
            else
                error "Solo se permiten letras y espacios"
            fi
        fi
    done

    # Opciones avanzadas
    echo ""
    read -p "Número de muestras [100]: " samples
    samples=${samples:-100}

    read -p "¿Probar el modelo después de crearlo? [s/N]: " test_model
    if [[ $test_model =~ ^[Ss]$ ]]; then
        test_flag="--test"
    else
        test_flag=""
    fi

    # Asegurar directorio de salida
    mkdir -p "$MODELS_DIR/wakeword"

    echo ""
    log "Generando wake word: $word..."
    echo ""

    # Ejecutar generador
    local result
    result=$("$PYTHON" "$SRC_DIR/utils/custom_wakeword.py" \
        "$word" \
        --output "$MODELS_DIR/wakeword" \
        --samples "$samples" \
        $test_flag \
        --print-config 2>&1)

    local exit_code=$?

    echo "$result"

    if [ $exit_code -eq 0 ]; then
        echo ""
        success "¡Wake word creado exitosamente!"

        # Extraer config JSON del resultado
        local config_json
        config_json=$(echo "$result" | sed -n '/{/,/}/p')

        if [ -n "$config_json" ]; then
            echo ""
            echo "¿Agregar al config.json automáticamente? [s/N]: "
            read -t 10 add_config || add_config="n"

            if [[ $add_config =~ ^[Ss]$ ]]; then
                "$PYTHON" << EOF
import json

config_path = "$PROJECT_DIR/config/config.json"
with open(config_path, 'r') as f:
    config = json.load(f)

# Asegurar wake_word existe
if 'wake_word' not in config:
    config['wake_word'] = {}
if 'keywords' not in config['wake_word']:
    config['wake_word']['keywords'] = []

# Agregar nueva keyword
new_kw = $config_json
config['wake_word']['keywords'].append(new_kw)
config['wake_word']['enabled'] = True

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"✅ Agregado '{new_kw['name']}' al config.json")
EOF
            fi
        fi

        echo ""
        echo "El modelo está guardado en: $MODELS_DIR/wakeword/${word}.tflite"

    else
        error "Falló la creación del wake word"
        echo "Revisa el log para más detalles: $LOG_FILE"
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
    echo -e "  ${CYAN}4.${NC} 🎤 Configurar Porcupine (API key)"
    echo -e "  ${CYAN}5.${NC} 📊 Ver estado"
    echo -e "  ${CYAN}6.${NC} 🔧 Instalar servicio systemd"
    echo -e "  ${CYAN}7.${NC} 📋 Ver logs"
    echo -e "  ${YELLOW}8.${NC} ✨ Crear wake word personalizado"
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
            4) setup_porcupine ;;
            5) show_status ;;
            6) install_service ;;
            7) show_logs ;;
            8) create_custom_wakeword ;;
            0|q|Q) echo "¡Hasta luego!"; exit 0 ;;
            *) echo "Opción no válida"; sleep 1 ;;
        esac
    done
}

main
