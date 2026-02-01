"""
Módulo de Validación y Sanitización de Entrada
Proporciona funciones para validar y sanitizar datos de entrada del usuario.
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Patrones de validación precompilados
SSID_PATTERN = re.compile(r'^[a-zA-Z0-9 _-]{1,32}$')
MODEL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')


def validate_ssid(ssid: str) -> bool:
    """
    Valida un SSID de WiFi.

    Args:
        ssid: Nombre de la red WiFi

    Returns:
        True si el SSID es válido, False en caso contrario
    """
    if not ssid or not isinstance(ssid, str):
        return False
    if len(ssid) > 32:
        return False
    return bool(SSID_PATTERN.match(ssid))


def validate_wifi_password(password: str) -> bool:
    """
    Valida una contraseña WiFi (8-63 caracteres ASCII imprimibles).

    Args:
        password: Contraseña de WiFi

    Returns:
        True si la contraseña es válida, False en caso contrario
    """
    if not password or not isinstance(password, str):
        return False
    if not 8 <= len(password) <= 63:
        return False
    # Solo caracteres ASCII imprimibles (32-126)
    return all(32 <= ord(c) <= 126 for c in password)


def validate_model_name(name: str) -> bool:
    """
    Valida un nombre de modelo de IA.

    Args:
        name: Nombre del modelo

    Returns:
        True si el nombre es válido, False en caso contrario
    """
    if not name or not isinstance(name, str):
        return False
    if len(name) > 255:
        return False
    return bool(MODEL_NAME_PATTERN.match(name))


def validate_path_traversal(path: Path, allowed_dir: Path) -> bool:
    """
    Verifica que un path no escape del directorio permitido (previene path traversal).

    Args:
        path: Ruta a verificar
        allowed_dir: Directorio permitido

    Returns:
        True si el path es seguro, False si intenta escapar
    """
    try:
        resolved = path.resolve()
        allowed = allowed_dir.resolve()
        return resolved.is_relative_to(allowed)
    except (ValueError, RuntimeError) as e:
        logger.debug(f"Error validando path traversal: {e}")
        return False


def sanitize_tts_text(text: str) -> str:
    """
    Sanitiza texto para TTS eliminando caracteres potencialmente peligrosos.

    Args:
        text: Texto a sanitizar

    Returns:
        Texto sanitizado seguro para TTS
    """
    if not text or not isinstance(text, str):
        return ""

    # Limitar longitud para prevenir DoS
    text = text[:1000]

    # Eliminar caracteres de control y peligrosos
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '$', '`', '\\', '\n', '\r', '\t', '\x00']
    for char in dangerous_chars:
        text = text.replace(char, ' ')

    return text.strip()


def validate_integer(value: any, min_val: int = None, max_val: int = None) -> Optional[int]:
    """
    Valida y convierte un valor a entero.

    Args:
        value: Valor a validar
        min_val: Valor mínimo aceptado (opcional)
        max_val: Valor máximo aceptado (opcional)

    Returns:
        Entero validado o None si inválido
    """
    try:
        int_val = int(value)
        if min_val is not None and int_val < min_val:
            return None
        if max_val is not None and int_val > max_val:
            return None
        return int_val
    except (ValueError, TypeError):
        return None


def validate_port(port: any) -> bool:
    """
    Valida un número de puerto.

    Args:
        port: Número de puerto a validar

    Returns:
        True si es un puerto válido (1-65535)
    """
    p = validate_integer(port, min_val=1, max_val=65535)
    return p is not None


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo eliminando caracteres peligrosos.

    Args:
        filename: Nombre de archivo a sanitizar

    Returns:
        Nombre de archivo seguro
    """
    if not filename or not isinstance(filename, str):
        return ""

    # Eliminar caracteres peligrosos
    dangerous = ['/', '\\', '..', ':', '*', '?', '"', '<', '>', '|', '\x00']
    for char in dangerous:
        filename = filename.replace(char, '_')

    # Limitar longitud
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')

    return filename.strip()


def validate_ip_address(ip: str) -> bool:
    """
    Valida una dirección IPv4.

    Args:
        ip: Dirección IP a validar

    Returns:
        True si es una IPv4 válida
    """
    if not ip or not isinstance(ip, str):
        return False

    parts = ip.split('.')
    if len(parts) != 4:
        return False

    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False
