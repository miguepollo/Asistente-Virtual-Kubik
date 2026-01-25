"""
Wake Word Detection Engine - Porcupine
Detecta la palabra de activación "Asistente".
"""

import logging
from typing import Optional, Callable
import time

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Detector de wake word usando Porcupine."""

    def __init__(
        self,
        access_key: str,
        keyword_path: str,
        sensitivity: float = 0.5,
        model_path: Optional[str] = None
    ):
        """
        Args:
            access_key: API key de Picovoice
            keyword_path: Ruta al archivo .ppn del wake word
            sensitivity: Sensibilidad (0.0-1.0)
            model_path: Ruta al modelo Porcupine (opcional)
        """
        self.access_key = access_key
        self.keyword_path = keyword_path
        self.sensitivity = sensitivity
        self.model_path = model_path

        self.porcupine = None
        self._initialized = False
        self.detections = 0
        self.start_time = time.time()

        if PORCUPINE_AVAILABLE:
            self._initialize()
        else:
            logger.error("Porcupine no está instalado")

    def _initialize(self) -> None:
        """Inicializa el detector Porcupine."""
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.keyword_path],
                sensitivities=[self.sensitivity],
                model_path=self.model_path
            )

            self.sample_rate = self.porcupine.sample_rate
            self.frame_length = self.porcupine.frame_length

            self._initialized = True
            logger.info(
                f"Porcupine inicializado: "
                f"sample_rate={self.sample_rate}, "
                f"frame_length={self.frame_length}"
            )

        except Exception as e:
            logger.error(f"Error inicializando Porcupine: {e}")

    def process(self, audio_frame) -> bool:
        """
        Procesa un frame de audio para detectar wake word.

        Args:
            audio_frame: Frame de audio (int16, longitud=frame_length)

        Returns:
            True si detecta wake word
        """
        if not self._initialized:
            return False

        try:
            keyword_index = self.porcupine.process(audio_frame)
            if keyword_index >= 0:
                self.detections += 1
                logger.info(f"¡Wake word detectado! (total: {self.detections})")
                return True
            return False

        except Exception as e:
            logger.error(f"Error procesando audio: {e}")
            return False

    def is_available(self) -> bool:
        """Retorna si el detector está disponible."""
        return self._initialized

    def get_stats(self) -> dict:
        """Retorna estadísticas."""
        uptime = time.time() - self.start_time
        return {
            "detections": self.detections,
            "uptime_seconds": uptime,
            "detections_per_hour": (self.detections / uptime) * 3600 if uptime > 0 else 0
        }

    def reset_stats(self) -> None:
        """Resetea estadísticas."""
        self.detections = 0
        self.start_time = time.time()

    def __del__(self):
        """Cleanup."""
        if self.porcupine:
            self.porcupine.delete()


class WakeWordEngine:
    """Motor completo de wake word con integración de audio."""

    def __init__(
        self,
        access_key: str,
        keyword_path: str,
        sensitivity: float = 0.5,
        on_detection: Optional[Callable] = None
    ):
        """
        Args:
            access_key: API key Picovoice
            keyword_path: Ruta al .ppn
            sensitivity: Sensibilidad
            on_detection: Callback cuando se detecta
        """
        self.detector = WakeWordDetector(
            access_key=access_key,
            keyword_path=keyword_path,
            sensitivity=sensitivity
        )

        self.on_detection = on_detection
        self.is_running = False

    def start(self, audio_capture) -> None:
        """
        Inicia la detección de wake word.

        Args:
            audio_capture: Instancia de AudioCapture
        """
        if not self.detector.is_available():
            logger.error("Detector no disponible")
            return

        if self.is_running:
            logger.warning("Ya está corriendo")
            return

        # Verificar compatibilidad de sample rate
        if audio_capture.sample_rate != self.detector.sample_rate:
            logger.error(
                f"Sample rate mismatch: "
                f"{audio_capture.sample_rate} != {self.detector.sample_rate}"
            )
            return

        # Registrar callback
        def callback(audio_chunk):
            frame_len = self.detector.frame_length
            for i in range(0, len(audio_chunk), frame_len):
                frame = audio_chunk[i:i+frame_len]
                if len(frame) < frame_len:
                    continue
                if self.detector.process(frame):
                    if self.on_detection:
                        try:
                            self.on_detection()
                        except Exception as e:
                            logger.error(f"Error en callback: {e}")

        audio_capture.register_callback(callback)

        if not audio_capture.is_running:
            audio_capture.start()

        self.is_running = True
        logger.info("Wake word detection iniciada")

    def stop(self) -> None:
        """Detiene la detección."""
        self.is_running = False
        logger.info("Wake word detection detenida")


# Test
if __name__ == '__main__':
    import sys
    sys.path.append('/home/orangepi/asistente/src')

    logging.basicConfig(level=logging.INFO)

    # Test solo si hay access key
    import os
    access_key = os.environ.get("PICOVOCICE_ACCESS_KEY")

    if not access_key:
        print("Set PICOVOCICE_ACCESS_KEY environment variable")
        exit(1)

    keyword_path = "/home/orangepi/asistente/models/wakeword/asistente_es.ppn"

    if not os.path.exists(keyword_path):
        print(f"Keyword file not found: {keyword_path}")
        exit(1)

    def on_detected():
        print("\n🎤 ¡WAKE WORD DETECTADO! 🎤\n")

    engine = WakeWordEngine(
        access_key=access_key,
        keyword_path=keyword_path,
        sensitivity=0.5,
        on_detection=on_detected
    )

    from audio.capture import AudioCapture

    capture = AudioCapture(sample_rate=16000)
    engine.start(capture)

    print("Escuchando wake word... Ctrl+C para salir")

    try:
        while True:
            import time
            time.sleep(0.1)
    except KeyboardInterrupt:
        engine.stop()
        capture.stop()
