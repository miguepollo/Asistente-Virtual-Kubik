#!/bin/bash
###############################################################################
# Asistente Virtual - Script de Inicio
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
NC='\033[0m'

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"

###############################################################################
# FUNCTIONS
###############################################################################

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║     🤖 ASISTENTE VIRTUAL - Iniciando                       ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        error "El entorno virtual no existe. Ejecuta primero: ./setup.sh"
        exit 1
    fi

    if [ ! -x "$PYTHON" ]; then
        error "Python no es ejecutable en el venv"
        exit 1
    fi
}

check_config() {
    if [ ! -f "$PROJECT_DIR/config/config.json" ]; then
        warn "config.json no encontrado, usando valores por defecto"
    fi
}

show_help() {
    cat << EOF
Uso: $0 [OPCIÓN]

Inicia el asistente virtual con diferentes configuraciones.

OPCIONES:
    -h, --help      Muestra esta ayuda
    -d, --debug     Modo debug (verbose)
    -v, --verbose   Modo verbose
    --no-wakeword   Inicia sin detección de wake word
    --web-only      Inicia solo el servidor web
    --test          Modo prueba (no inicia servicios)

Ejemplos:
    $0              Inicia el asistente normalmente
    $0 -d           Inicia en modo debug
    $0 --web-only   Inicia solo el servidor web

EOF
}

###############################################################################
# MAIN
###############################################################################

# Parse arguments
DEBUG=""
NO_WAKEWORD=false
WEB_ONLY=false
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--debug)
            DEBUG="--debug"
            VERBOSE="--verbose"
            shift
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --no-wakeword)
            NO_WAKEWORD=true
            shift
            ;;
        --web-only)
            WEB_ONLY=true
            shift
            ;;
        --test)
            log "Modo prueba - no se inicia el servicio"
            exit 0
            ;;
        *)
            error "Opción no reconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

header

# Verificaciones
log "Verificando entorno..."
check_venv
success "Entorno virtual OK"

check_config
success "Configuración OK"

echo ""

# Activar venv y ejecutar
log "Iniciando asistente..."
echo ""

if [ "$WEB_ONLY" = true ]; then
    log "Modo: Solo servidor web"
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    exec "$PYTHON" -m src.webserver.app $DEBUG $VERBOSE
else
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"

    if [ "$NO_WAKEWORD" = true ]; then
        log "Modo: Sin wake word"
        exec "$PYTHON" -m src.main --no-wakeword $DEBUG $VERBOSE
    else
        exec "$PYTHON" -m src.main $DEBUG $VERBOSE
    fi
fi
