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
from utils.config_loader import get_config, Config

###############################################################################
# Configuration
###############################################################################
PROJECT_DIR = Path("/home/orangepi/asistente2")
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

        # Obtener configuración de wake word
        wake_config = self.config.get("wake_word", {})
        wake_enabled = wake_config.get("enabled", True)
        wake_engine = wake_config.get("engine", "auto")

        if not wake_enabled:
            self.wakeword = None
            logger.info(f"  Wake Word: ⚠️  Desactivado en config")
            return

        # Soporte para Vosk como motor de wake word
        if wake_engine == "vosk" or wake_config.get("wake_words"):
            wake_words = wake_config.get("wake_words", ["asistente"])
            wake_model_path = wake_config.get("model_path")

            try:
                self.wakeword = WakeWordEngine(
                    wake_words=wake_words,
                    model_path=wake_model_path,
                    on_detection=self._on_wakeword_detected,
                    engine="vosk"
                )
                logger.info(f"  Wake Word: ✅ ({wake_words}) [Vosk]")
            except Exception as e:
                logger.error(f"  Wake Word: ❌ Error iniciando Vosk: {e}")
                self.wakeword = None
            return

        # Obtener keywords del config (para Porcupine/openWakeWord)
        keywords_config = wake_config.get("keywords")

        # Compatibilidad con config antiguo
        if not keywords_config:
            # Formato antiguo: usar model_path y sensitivity
            wakeword_path = wake_config.get("model_path",
                f"{PROJECT_DIR}/models/wakeword/asistente_es.ppn")
            if os.path.exists(wakeword_path):
                keywords_config = [{
                    "path": wakeword_path,
                    "sensitivity": wake_config.get("sensitivity", 0.5),
                    "name": wake_config.get("keyword", "asistente")
                }]

        # Procesar keywords (soporta .ppn de Porcupine y .tflite de openWakeWord)
        if keywords_config:
            valid_keywords = []
            engine_type = "unknown"

            for kw in keywords_config:
                if os.path.exists(kw["path"]):
                    valid_keywords.append(kw)

                    # Detectar tipo de motor
                    if kw["path"].endswith(".tflite"):
                        engine_type = "openwakeword"
                    elif kw["path"].endswith(".ppn"):
                        engine_type = "porcupine"
                else:
                    logger.warning(f"Keyword file no encontrado: {kw['path']}")

            if valid_keywords:
                try:
                    # openWakeWord no requiere access_key
                    if engine_type == "openwakeword":
                        self.wakeword = WakeWordEngine(
                            access_key=None,  # No necesario para openWakeWord
                            keywords=valid_keywords,
                            on_detection=self._on_wakeword_detected,
                            engine="openwakeword"
                        )
                        kw_names = [kw["name"] for kw in valid_keywords]
                        logger.info(f"  Wake Word: ✅ ({kw_names}) [openWakeWord]")

                    # Porcupine requiere access_key
                    elif engine_type == "porcupine":
                        if access_key:
                            self.wakeword = WakeWordEngine(
                                access_key=access_key,
                                keywords=valid_keywords,
                                on_detection=self._on_wakeword_detected,
                                engine="porcupine"
                            )
                            kw_names = [kw["name"] for kw in valid_keywords]
                            logger.info(f"  Wake Word: ✅ ({kw_names}) [Porcupine]")
                        else:
                            logger.warning(f"  Wake Word: ⚠️  .ppn detectado pero falta API key")
                            self.wakeword = None

                    else:
                        self.wakeword = None
                        logger.info(f"  Wake Word: ⚠️  Tipo de motor no reconocido")

                except Exception as e:
                    logger.error(f"  Wake Word: ❌ Error iniciando: {e}")
                    self.wakeword = None
            else:
                self.wakeword = None
                logger.info(f"  Wake Word: ⚠️  No hay archivos válidos")
        else:
            self.wakeword = None
            logger.info(f"  Wake Word: ⚠️  No configurado")

    def _signal_handler(self, signum, frame):
        """Maneja señales de terminación."""
        logger.info(f"Señal recibida: {signum}")
        self.stop()

    def _on_wakeword_detected(self, keyword_name: str = None):
        """Callback cuando se detecta el wake word.

        Args:
            keyword_name: Nombre del keyword detectado (ej: "asistente", "hey")
        """
        if keyword_name:
            logger.info(f"🎤 ¡WAKE WORD '{keyword_name}' DETECTADO!")
        else:
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
def run_setup_server():
    """Ejecuta el servidor web en modo configuración inicial."""
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║     🔧 MODO CONFIGURACIÓN INICIAL                         ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info(f"Accede a http://localhost:5000 o http://$(hostname -I | cut -d' ' -f1):5000")
    logger.info("para configurar el asistente.")

    try:
        from webserver.app import app as web_app
        # Marcar que estamos en modo setup
        web_app.config['SETUP_MODE'] = True

        web_app.run(
            host="0.0.0.0",
            port=5000,
            debug=False
        )
    except KeyboardInterrupt:
        logger.info("Servidor de configuración detenido.")
    except Exception as e:
        logger.error(f"Error iniciando servidor web: {e}")
        logger.info("Puedes configurar manualmente creando el archivo:")
        logger.info(f"  {CONFIG_DIR}/config.json")


def is_first_run():
    """Verifica si es la primera ejecución (no existe config.json)."""
    config_path = CONFIG_DIR / "config.json"
    return not config_path.exists()


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
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Forzar inicio del servidor de configuración"
    )
    args = parser.parse_args()

    # Verificar si es primera ejecución o se forzó setup
    if args.setup or is_first_run():
        run_setup_server()
        return

    # Crear asistente
    assistant = Assistant()

    if args.once:
        assistant.run_once()
    else:
        assistant.run()


if __name__ == "__main__":
    main()
