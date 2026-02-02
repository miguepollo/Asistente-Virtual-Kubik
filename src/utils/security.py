"""
Módulo de Seguridad - Gestión de secretos y claves criptográficas
"""

import secrets
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Import paths configuration
try:
    from utils.paths import CONFIG_DIR
except ImportError:
    # Fallback for when paths module is not available
    CONFIG_DIR = Path("/home/orangepi/asistente2/config")


def get_or_create_secret_key(key_dir: Path = None) -> str:
    """
    Obtiene la clave secreta de Flask desde el entorno o genera una nueva.

    La clave se obtiene en el siguiente orden de prioridad:
    1. Variable de entorno FLASK_SECRET_KEY
    2. Archivo .secret_key en el directorio de configuración
    3. Generar nueva clave y guardarla

    Args:
        key_dir: Directorio donde guardar/buscar la clave (default: CONFIG_DIR from paths module)

    Returns:
        Clave secreta hexadecimal de 64 caracteres (32 bytes)

    Raises:
        ValueError: Si la clave del entorno es demasiado corta
        IOError: Si no se puede escribir el archivo de clave
    """
    # Primero verificar variable de entorno
    env_key = os.environ.get('FLASK_SECRET_KEY')
    if env_key:
        if len(env_key) < 32:
            raise ValueError("FLASK_SECRET_KEY debe tener al menos 32 caracteres")
        logger.info("Usando SECRET_KEY del entorno")
        return env_key

    # Directorio por defecto - usar CONFIG_DIR del módulo paths
    if key_dir is None:
        key_dir = CONFIG_DIR

    key_file = key_dir / ".secret_key"

    # Verificar si existe el archivo
    if key_file.exists():
        try:
            key = key_file.read_text().strip()
            if len(key) >= 32:
                logger.info("Usando SECRET_KEY existente del archivo")
                return key
            else:
                logger.warning("SECRET_KEY existente es demasiado corta, regenerando")
        except Exception as e:
            logger.error(f"Error leyendo archivo de clave: {e}")

    # Generar nueva clave
    logger.info("Generando nueva SECRET_KEY")
    key = secrets.token_hex(32)  # 64 caracteres hexadecimales

    try:
        # Crear directorio si no existe
        key_dir.mkdir(parents=True, exist_ok=True)

        # Escribir clave con permisos restrictivos
        key_file.write_text(key)
        key_file.chmod(0o600)  # Solo lectura/escritura para el propietario

        logger.info(f"Nueva SECRET_KEY guardada en: {key_file}")
    except Exception as e:
        logger.error(f"Error guardando SECRET_KEY: {e}")
        # Continuar con la clave generada aunque no se pueda guardar
        raise IOError(f"No se pudo guardar el archivo de clave: {e}")

    return key


def generate_api_key(length: int = 32) -> str:
    """
    Genera una clave API aleatoria.

    Args:
        length: Longitud de la clave en bytes (default: 32)

    Returns:
        Clave API hexadecimal
    """
    return secrets.token_hex(length)


def verify_password_strength(password: str) -> tuple[bool, str]:
    """
    Verifica la fortaleza de una contraseña.

    Args:
        password: Contraseña a verificar

    Returns:
        Tuple (es_fuerte, mensaje)
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"

    if len(password) > 128:
        return False, "La contraseña no puede exceder 128 caracteres"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    score = sum([has_upper, has_lower, has_digit, has_special])

    if score < 2:
        return False, "La contraseña es débil. Usa mayúsculas, minúsculas, números y símbolos"
    elif score < 3:
        return True, "Contraseña aceptable pero podría ser más fuerte"
    else:
        return True, "Contraseña fuerte"
