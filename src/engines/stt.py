"""
Speech-to-Text Engine - Vosk
Transcribe audio a texto offline.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict
import numpy as np

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

logger = logging.getLogger(__name__)


class STTEngine:
    """Motor de Speech-to-Text usando Vosk."""

    def __init__(
        self,
        model_path: str = "/home/orangepi/asistente/models/stt/vosk-model-small-es-0.42",
        sample_rate: int = 16000
    ):
        """
        Args:
            model_path: Ruta al modelo Vosk
            sample_rate: Frecuencia de muestreo del audio
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self._loaded = False

        if not VOSK_AVAILABLE:
            logger.error("Vosk no está instalado")
            return

        self._load_model()

    def _load_model(self) -> None:
        """Carga el modelo Vosk."""
        if not os.path.exists(self.model_path):
            logger.error(f"Modelo no encontrado: {self.model_path}")
            return

        try:
            log_path = os.path.join(self.model_path, 'am', 'final', 'log')
            if os.path.exists(log_path):
                os.remove(log_path)

            self.model = Model(self.model_path)
            self._loaded = True
            logger.info(f"Modelo Vosk cargado: {self.model_path}")
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")

    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: Optional[int] = None
    ) -> Dict:
        """
        Transcribe audio a texto.

        Args:
            audio_data: Array de audio (int16)
            sample_rate: Frecuencia de muestreo (usa default si None)

        Returns:
            Dict con 'text' y 'confidence'
        """
        if not self._loaded:
            return {"text": None, "error": "Modelo no cargado"}

        if sample_rate is None:
            sample_rate = self.sample_rate

        if sample_rate != self.sample_rate:
            logger.warning(
                f"Sample rate mismatch: {sample_rate} != {self.sample_rate}"
            )

        try:
            # Crear recognizer
            rec = KaldiRecognizer(self.model, self.sample_rate)
            rec.SetWords(True)

            # Convertir audio a bytes
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)

            audio_bytes = audio_data.tobytes()

            # Procesar
            if rec.AcceptWaveform(audio_bytes):
                result = json.loads(rec.Result())
                text = result.get("text", "")
            else:
                # Procesar final
                result = json.loads(rec.FinalResult())
                text = result.get("text", "")

            # Obtener palabras para confidence
            words = result.get("result", [])
            if words:
                confidences = [w.get("conf", 0) for w in words]
                confidence = sum(confidences) / len(confidences) if confidences else 0.5
            else:
                confidence = 0.0

            return {
                "text": text if text else None,
                "confidence": confidence,
                "words": words
            }

        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            return {"text": None, "error": str(e)}

    def transcribe_file(self, wav_path: str) -> Dict:
        """
        Transcribe un archivo WAV.

        Args:
            wav_path: Ruta al archivo WAV

        Returns:
            Dict con 'text' y 'confidence'
        """
        try:
            import wave

            with wave.open(wav_path, "rb") as wf:
                if wf.getnchannels() != 1:
                    logger.warning("Audio no es mono, convirtiendo...")
                if wf.getframerate() != self.sample_rate:
                    logger.warning(f"Sample rate: {wf.getframerate()}")

                rec = KaldiRecognizer(self.model, wf.getframerate())

                result_text = ""
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        result_text += " " + result.get("text", "")

                # Resultado final
                final = json.loads(rec.FinalResult())
                result_text += " " + final.get("text", "")

                return {
                    "text": result_text.strip() or None,
                    "confidence": 0.8
                }

        except Exception as e:
            logger.error(f"Error transcribiendo archivo: {e}")
            return {"text": None, "error": str(e)}

    def is_available(self) -> bool:
        """Retorna si el motor está disponible."""
        return self._loaded

    def __del__(self):
        """Cleanup."""
        if self.model:
            del self.model


# Test
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    stt = STTEngine()

    if not stt.is_available():
        print("Vosk no disponible")
        exit(1)

    # Generar audio de prueba
    duration = 2.0
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * 440 * t) * 0.1).astype(np.int16)

    result = stt.transcribe(audio)
    print(f"Texto: {result['text']}")
    print(f"Confidence: {result.get('confidence', 0)}")
