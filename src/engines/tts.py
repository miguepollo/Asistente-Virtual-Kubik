"""
Text-to-Speech Engine - Piper
Genera audio desde texto offline.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TTSEngine:
    """Motor de Text-to-Speech usando Piper."""

    def __init__(
        self,
        model_path: str = "/home/orangepi/asistente2/models/tts/es_ES-davefx-medium.onnx",
        config_path: Optional[str] = None,
        speed: float = 1.0
    ):
        """
        Args:
            model_path: Ruta al modelo .onnx
            config_path: Ruta al JSON de configuración (auto si None)
            speed: Velocidad de habla (1.0 = normal)
        """
        self.model_path = model_path
        self.config_path = config_path or f"{model_path}.json"
        self.speed = speed
        self._available = self._check_available()

        if self._available:
            logger.info(f"Piper TTS inicializado: {Path(model_path).stem}")
        else:
            logger.warning("Piper TTS no disponible")

    def _check_available(self) -> bool:
        """Verifica si Piper está disponible."""
        # Verificar modelo
        if not os.path.exists(self.model_path):
            logger.error(f"Modelo no encontrado: {self.model_path}")
            return False

        # Verificar config
        if not os.path.exists(self.config_path):
            logger.error(f"Config no encontrado: {self.config_path}")
            return False

        # Verificar piper executable
        try:
            result = subprocess.run(
                ["piper", "--help"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Intentar con módulo Python
            try:
                import piper
                return True
            except ImportError:
                return False

    def synthesize(
        self,
        text: str,
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """
        Sintetiza texto a audio.

        Args:
            text: Texto a sintetizar
            output_file: Ruta de salida (temporal si None)

        Returns:
            Ruta al archivo WAV generado o None
        """
        if not self._available:
            logger.error("Piper no disponible")
            return None

        if not text or not text.strip():
            logger.warning("Texto vacío")
            return None

        # Crear archivo temporal si no se especifica
        delete_after = False
        if output_file is None:
            output_file = tempfile.mktemp(suffix=".wav")
            delete_after = True

        try:
            # Usar piper desde CLI
            cmd = [
                "piper",
                "--model", self.model_path,
                "--config", self.config_path,
                "--output_file", output_file
            ]

            if self.speed != 1.0:
                # Length scale para velocidad (1/speed)
                length_scale = 1.0 / self.speed
                cmd.extend(["--length_scale", str(length_scale)])

            # Ejecutar
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = proc.communicate(input=text.encode(), timeout=30)

            if proc.returncode != 0:
                logger.error(f"Piper error: {stderr.decode()}")
                return None

            logger.debug(f"TTS generado: {output_file}")
            return output_file

        except subprocess.TimeoutExpired:
            logger.error("TTS timeout")
            return None
        except Exception as e:
            logger.error(f"Error en TTS: {e}")
            return None

    def synthesize_to_bytes(self, text: str) -> Optional[bytes]:
        """
        Sintetiza texto y retorna los bytes del audio.

        Args:
            text: Texto a sintetizar

        Returns:
            Bytes del WAV o None
        """
        output_file = self.synthesize(text)

        if output_file and os.path.exists(output_file):
            try:
                with open(output_file, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(output_file)
                return audio_bytes
            except Exception as e:
                logger.error(f"Error leyendo audio: {e}")
                if os.path.exists(output_file):
                    os.unlink(output_file)
                return None

        return None

    def speak(
        self,
        text: str,
        play_command: str = "aplay"
    ) -> bool:
        """
        Sintetiza y reproduce texto directamente.

        Args:
            text: Texto a hablar
            play_command: Comando para reproducir (aplay, paplay, etc)

        Returns:
            True si exitoso
        """
        output_file = self.synthesize(text)

        if output_file:
            try:
                subprocess.run(
                    [play_command, output_file],
                    check=True,
                    capture_output=True
                )
                os.unlink(output_file)
                return True
            except Exception as e:
                logger.error(f"Error reproduciendo: {e}")
                if os.path.exists(output_file):
                    os.unlink(output_file)
                return False

        return False

    def is_available(self) -> bool:
        """Retorna si el motor está disponible."""
        return self._available

    @property
    def voice_name(self) -> str:
        """Retorna el nombre de la voz."""
        return Path(self.model_path).stem


# Test
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    tts = TTSEngine()

    if not tts.is_available():
        print("Piper no disponible")
        exit(1)

    print(f"Voz: {tts.voice_name}")
    print("Sintetizando 'Hola, esto es una prueba'...")

    output = tts.synthesize("Hola, esto es una prueba.")

    if output:
        print(f"Archivo generado: {output}")
        print("Reproduciendo...")
        subprocess.run(["aplay", output])
        os.unlink(output)
    else:
        print("Error generando audio")
