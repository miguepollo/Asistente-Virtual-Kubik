#!/usr/bin/env python3
"""
Asistente Virtual - Main Entry Point
Orange Pi 5 Ultra

Un asistente de voz offline-first con wake word detection,
STT, TTS y LLM local.
"""

import sys
import os
import time
import signal
import logging
import numpy as np
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent))

from audio.capture import AudioCapture
from audio.playback import AudioPlayback
from audio.vad import VAD
from engines.stt import STTEngine
from engines.tts import TTSEngine
from engines.llm import LLMEngine
from engines.wakeword import WakeWordEngine
from utils.logger import setup_logging, get_logger
from utils.config_loader import get_config

###############################################################################
# Configuration
###############################################################################
PROJECT_DIR = Path("/home/orangepi/asistente")
CONFIG_DIR = PROJECT_DIR / "config"
LOGS_DIR = PROJECT_DIR / "logs"

###############################################################################
# Setup Logging
###############################################################################
LOGS_DIR.mkdir(parents=True, exist_ok=True)
setup_logging(level="INFO", log_dir=str(LOGS_DIR))
logger = get_logger("main")

###############################################################################
# Assistant Class
###############################################################################
class Assistant:
    """Asistente de voz principal."""

    def __init__(self):
        """Inicializa todos los componentes del asistente."""
        logger.info("╔════════════════════════════════════════════════════════════╗")
        logger.info("║     🤖 ASISTENTE VIRTUAL - Iniciando                       ║")
        logger.info("╚════════════════════════════════════════════════════════════╝")

        # Cargar configuración
        self.config = get_config()

        # Estado
        self.running = False
        self.listening = False
        self.context_active = False
        self.context_timer = None

        # Inicializar componentes
        self._init_audio()
        self._init_engines()

        # Configurar señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("✅ Asistente inicializado")

    def _init_audio(self):
        """Inicializa componentes de audio."""
        logger.info("Inicializando audio...")

        self.capture = AudioCapture(
            sample_rate=self.config.get("audio.sample_rate", 16000),
            channels=self.config.get("audio.channels", 1),
            chunk_size=self.config.get("audio.chunk_size", 512)
        )

        self.playback = AudioPlayback(
            sample_rate=self.config.get("audio.sample_rate", 16000),
            channels=self.config.get("audio.channels", 1)
        )

        self.vad = VAD(
            sample_rate=self.config.get("vad.sample_rate", 16000),
            aggressiveness=self.config.get("vad.aggressiveness", 3),
            silence_duration=self.config.get("vad.silence_duration", 2.0)
        )

        # Ajustar volumen inicial
        initial_vol = self.config.get("audio.output_volume", 70)
        self.playback.set_volume(initial_vol)

        logger.info("✅ Audio inicializado")

    def _init_engines(self):
        """Inicializa motores de IA."""
        logger.info("Inicializando motores de IA...")

        # STT
        stt_path = self.config.get("stt.model_path",
            f"{PROJECT_DIR}/models/stt/vosk-model-small-es-0.42")
        self.stt = STTEngine(model_path=stt_path)
        logger.info(f"  STT: {'✅' if self.stt.is_available() else '❌'}")

        # TTS
        tts_path = self.config.get("tts.model_path",
            f"{PROJECT_DIR}/models/tts/es_ES-davefx-medium.onnx")
        self.tts = TTSEngine(model_path=tts_path)
        logger.info(f"  TTS: {'✅' if self.tts.is_available() else '❌'}")

        # LLM
        llm_path = self.config.get("llm.model_path")
        self.llm = LLMEngine(model_path=llm_path)
        logger.info(f"  LLM: {'✅' if self.llm.is_available() else '❌'}")

        # Wake Word (opcional)
        access_key = self.config.get_api_key("picovoice", "access_key")
        wakeword_path = self.config.get("wake_word.model_path",
            f"{PROJECT_DIR}/models/wakeword/asistente_es.ppn")

        if access_key and os.path.exists(wakeword_path):
            self.wakeword = WakeWordEngine(
                access_key=access_key,
                keyword_path=wakeword_path,
                sensitivity=self.config.get("wake_word.sensitivity", 0.5),
                on_detection=self._on_wakeword_detected
            )
            logger.info(f"  Wake Word: ✅")
        else:
            self.wakeword = None
            logger.info(f"  Wake Word: ⚠️  No configurado")

    def _signal_handler(self, signum, frame):
        """Maneja señales de terminación."""
        logger.info(f"Señal recibida: {signum}")
        self.stop()

    def _on_wakeword_detected(self):
        """Callback cuando se detecta el wake word."""
        logger.info("🎤 ¡WAKE WORD DETECTADO!")
        self.start_listening()

   ###############################################################################
    # Estado: Listening
   ###############################################################################
    def start_listening(self):
        """Comienza a escuchar un comando."""
        if self.listening:
            return

        self.listening = True
        logger.info("🎤 Escuchando...")

        # Reproducir beep de confirmación (opcional)
        # self._play_beep()

        # Iniciar captura
        if not self.capture.is_running:
            self.capture.start()

        # Capturar audio con VAD
        self._capture_with_vad()

    def _capture_with_vad(self):
        """Captura audio usando VAD para detectar fin de voz."""
        self.vad.reset()

        audio_chunks = []
        silence_count = 0
        max_silence = int(self.vad.silence_threshold)

        chunk_size = self.vad.frame_size

        logger.info("Habla ahora...")

        while self.listening and self.running:
            # Obtener chunk
            audio = self.capture.get_chunk(timeout=0.5)
            if audio is None:
                continue

            # Procesar con VAD
            for i in range(0, len(audio), chunk_size):
                if not self.listening:
                    break

                frame = audio[i:i+chunk_size]
                if len(frame) < chunk_size:
                    frame = np.pad(frame, (0, chunk_size - len(frame)), 'constant')

                is_speech = self.vad.is_speech(frame)

                if is_speech:
                    audio_chunks.append(frame)
                    silence_count = 0
                else:
                    silence_count += 1

                # Fin de voz detectado
                if len(audio_chunks) > 0 and silence_count >= max_silence:
                    logger.info("Fin de voz detectado")
                    self.listening = False
                    break

            if not self.listening:
                break

        # Procesar audio capturado
        if audio_chunks:
            import numpy as np
            full_audio = np.concatenate(audio_chunks)
            self._process_audio(full_audio)
        else:
            logger.info("No se detectó voz")
            self._speak("No te he entendido")

    def _process_audio(self, audio_data):
        """Procesa el audio capturado."""
        logger.info("Procesando audio...")

        # Transcribir
        result = self.stt.transcribe(audio_data)
        text = result.get("text")

        if not text:
            logger.info("No se pudo transcribir")
            self._speak("No te he entendido")
            return

        logger.info(f"Texto reconocido: '{text}'")
        self._process_intent(text)

    def _process_intent(self, text):
        """Procesa el intent del texto."""
        text_lower = text.lower()

        # Comandos del sistema
        if "para" in text_lower or "stop" in text_lower:
            self._speak("Adiós")
            return

        if "gracias" in text_lower:
            self._speak("De nada")
            return

        # Generar respuesta con LLM
        response = self.llm.generate(text)
        logger.info(f"Respuesta: '{response}'")

        # Hablar respuesta
        self._speak(response)

    def _speak(self, text: str):
        """Sintetiza y reproduce texto."""
        if not text:
            return

        logger.info(f"Hablando: '{text}'")

        output_file = self.tts.synthesize(text)
        if output_file:
            self.playback.play_wav(output_file)
            os.unlink(output_file)
        else:
            logger.error("No se pudo sintetizar audio")

    def _play_beep(self):
        """Reproduce un beep de confirmación."""
        import numpy as np
        duration = 0.1
        frequency = 880
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))
        beep = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.3).astype(np.int16)
        self.playback.play_array(beep)

   ###############################################################################
    # Main Loop
   ###############################################################################
    def run(self):
        """Ejecuta el asistente en modo continuo."""
        self.running = True
        logger.info("🚀 Asistente iniciado")

        # Mensaje de bienvenida
        self._speak("Sistema iniciado. Di Asistente para activarme.")

        # Iniciar captura continua para wake word
        if self.wakeword:
            self.wakeword.start(self.capture)
            logger.info("Escuchando wake word...")

        # Loop principal
        try:
            while self.running:
                time.sleep(0.1)

                # Si no hay wake word, escuchar continuamente
                if not self.wakeword and not self.listening:
                    # Modo simple: sin wake word, escuchar continuamente
                    pass

        except Exception as e:
            logger.error(f"Error en loop principal: {e}", exc_info=True)
        finally:
            self.stop()

    def run_once(self):
        """Ejecuta el asistente una sola vez (sin wake word)."""
        self.running = True
        logger.info("🚀 Asistente iniciado (modo single)")

        self._speak("Di tu comando.")

        if not self.capture.is_running:
            self.capture.start()

        self.start_listening()

        # Esperar a que termine de escuchar
        while self.listening:
            time.sleep(0.1)

        self.stop()

    def stop(self):
        """Detiene el asistente."""
        logger.info("Deteniendo asistente...")
        self.running = False
        self.listening = False

        if self.capture.is_running:
            self.capture.stop()

        logger.info("👋 Asistente detenido")


###############################################################################
# Entry Point
###############################################################################
def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Asistente Virtual Orange Pi")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecutar un solo comando y salir"
    )
    parser.add_argument(
        "--no-wakeword",
        action="store_true",
        help="Desactivar wake word detection"
    )
    args = parser.parse_args()

    # Crear asistente
    assistant = Assistant()

    if args.once:
        assistant.run_once()
    else:
        assistant.run()


if __name__ == "__main__":
    main()
