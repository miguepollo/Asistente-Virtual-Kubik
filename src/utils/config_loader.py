"""
Configuration Loader Module
Gestiona la carga y guardado de configuraciones.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)


class Config:
    """Gestiona la configuración del asistente."""

    def __init__(
        self,
        config_path: str = "/home/orangepi/asistente/config/config.json",
        api_keys_path: str = "/home/orangepi/asistente/config/api_keys.json",
        encryption_key: Optional[bytes] = None
    ):
        """
        Args:
            config_path: Ruta al archivo de configuración principal
            api_keys_path: Ruta al archivo de API keys
            encryption_key: Clave para encriptar/desencriptar (None=sin encriptación)
        """
        self.config_path = Path(config_path)
        self.api_keys_path = Path(api_keys_path)

        # Cifrado para API keys
        self.encryption_key = encryption_key
        self.cipher = Fernet(encryption_key) if encryption_key else None

        # Cargar configuraciones
        self.config: Dict[str, Any] = {}
        self.api_keys: Dict[str, Any] = {}

        self._load_config()
        self._load_api_keys()

    def _load_config(self) -> None:
        """Carga la configuración principal."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuración cargada desde {self.config_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Error decodificando config.json: {e}")
                self.config = self._get_default_config()
        else:
            logger.warning(f"Archivo de config no encontrado: {self.config_path}")
            self.config = self._get_default_config()

    def _load_api_keys(self) -> None:
        """Carga las API keys (con desencriptación si está habilitado)."""
        if self.api_keys_path.exists():
            try:
                with open(self.api_keys_path, 'r') as f:
                    data = json.load(f)

                # Desencriptar si hay cipher
                if self.cipher:
                    self.api_keys = self._decrypt_keys(data)
                else:
                    self.api_keys = data

                logger.info("API keys cargadas")
            except json.JSONDecodeError as e:
                logger.error(f"Error decodificando api_keys.json: {e}")
                self.api_keys = {}
        else:
            logger.warning(f"Archivo de API keys no encontrado: {self.api_keys_path}")
            self.api_keys = {}

    def _decrypt_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Desencripta valores de API keys."""
        decrypted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                decrypted[key] = {
                    k: self._decrypt_value(v) if k != "description" else v
                    for k, v in value.items()
                }
            else:
                decrypted[key] = self._decrypt_value(value)
        return decrypted

    def _decrypt_value(self, value: str) -> str:
        """Desencripta un valor individual."""
        try:
            decoded = base64.urlsafe_b64decode(value.encode())
            return self.cipher.decrypt(decoded).decode()
        except Exception:
            return value

    def _encrypt_value(self, value: str) -> str:
        """Encripta un valor individual."""
        if not self.cipher:
            return value
        encrypted = self.cipher.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna la configuración por defecto."""
        return {
            "audio": {
                "sample_rate": 16000,
                "channels": 1,
                "chunk_size": 512,
                "input_device": None,
                "output_device": None,
                "input_volume": 60,
                "output_volume": 70
            },
            "vad": {
                "sample_rate": 16000,
                "aggressiveness": 3,
                "frame_duration_ms": 30,
                "silence_duration": 2.0
            },
            "wake_word": {
                "enabled": True,
                "keyword": "asistente",
                "sensitivity": 0.5
            },
            "stt": {
                "engine": "vosk",
                "language": "es"
            },
            "tts": {
                "engine": "piper",
                "voice": "es_ES-davefx-medium",
                "speed": 1.0
            },
            "llm": {
                "engine": "rkllm",
                "context_length": 2048,
                "temperature": 0.7,
                "max_tokens": 256
            },
            "context": {
                "timeout_seconds": 60,
                "max_history": 5
            },
            "webserver": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 5000
            },
            "logging": {
                "level": "INFO"
            }
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración usando notación de puntos.

        Args:
            key_path: Ruta de la clave (ej: "audio.sample_rate")
            default: Valor por defecto si no existe

        Returns:
            Valor de configuración o default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Establece un valor de configuración usando notación de puntos.

        Args:
            key_path: Ruta de la clave (ej: "audio.sample_rate")
            value: Nuevo valor
        """
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        logger.debug(f"Config actualizada: {key_path} = {value}")

    def get_api_key(self, service: str, key: str = "api_key") -> Optional[str]:
        """
        Obtiene una API key específica.

        Args:
            service: Nombre del servicio (ej: "openweathermap")
            key: Clave específica (default: "api_key")

        Returns:
            API key o None si no existe
        """
        if service in self.api_keys:
            if isinstance(self.api_keys[service], dict):
                return self.api_keys[service].get(key)
            return self.api_keys[service]
        return None

    def save(self, include_api_keys: bool = False) -> None:
        """
        Guarda la configuración a archivo.

        Args:
            include_api_keys: Si True, también guarda API keys
        """
        # Guardar config principal
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuración guardada en {self.config_path}")

        # Guardar API keys
        if include_api_keys and self.api_keys:
            with open(self.api_keys_path, 'w') as f:
                json.dump(self.api_keys, f, indent=2)
            logger.info(f"API keys guardadas en {self.api_keys_path}")

    def reload(self) -> None:
        """Recarga las configuraciones desde archivo."""
        self._load_config()
        self._load_api_keys()
        logger.info("Configuración recargada")

    @property
    def audio(self) -> Dict[str, Any]:
        """Acceso directo a configuración de audio."""
        return self.config.get("audio", {})

    @property
    def vad(self) -> Dict[str, Any]:
        """Acceso directo a configuración de VAD."""
        return self.config.get("vad", {})

    @property
    def wake_word(self) -> Dict[str, Any]:
        """Acceso directo a configuración de wake word."""
        return self.config.get("wake_word", {})

    @property
    def stt(self) -> Dict[str, Any]:
        """Acceso directo a configuración de STT."""
        return self.config.get("stt", {})

    @property
    def tts(self) -> Dict[str, Any]:
        """Acceso directo a configuración de TTS."""
        return self.config.get("tts", {})

    @property
    def llm(self) -> Dict[str, Any]:
        """Acceso directo a configuración de LLM."""
        return self.config.get("llm", {})


# Singleton instance
_config_instance: Optional[Config] = None


def get_config(**kwargs) -> Config:
    """Retorna la instancia singleton de Config."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(**kwargs)
    return _config_instance


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Test
    config = Config()

    print("\n=== Configuración actual ===")
    print(f"Sample rate: {config.get('audio.sample_rate')}")
    print(f"VAD aggressiveness: {config.get('vad.aggressiveness')}")
    print(f"Wake word: {config.get('wake_word.keyword')}")

    print("\n=== Propiedades ===")
    print(f"Audio: {config.audio}")
    print(f"VAD: {config.vad}")
