"""
Tests del pipeline de audio completo.
"""

import sys
sys.path.append('/home/orangepi/asistente/src')

from audio.capture import AudioCapture
from audio.playback import AudioPlayback
from audio.vad import VAD
import numpy as np
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_latency():
    """Test de latencia end-to-end."""
    logger.info("=== Test de latencia ===")

    capture = AudioCapture()
    playback = AudioPlayback()

    # Grabar 1 segundo
    logger.info("Grabando 1 segundo...")
    start_time = time.time()

    capture.start()
    time.sleep(1.0)
    audio_data = capture.get_buffer(duration=1.0)
    capture.stop()

    capture_time = time.time() - start_time
    logger.info(f"Captura completada en {capture_time:.3f}s")

    # Reproducir
    logger.info("Reproduciendo...")
    start_time = time.time()
    playback.play_array(audio_data)
    playback_time = time.time() - start_time

    logger.info(f"Reproducción completada en {playback_time:.3f}s")
    logger.info(f"Latencia total: {capture_time + playback_time:.3f}s")


def test_vad_realtime():
    """Test VAD en tiempo real."""
    logger.info("\n=== Test VAD en tiempo real ===")
    logger.info("Habla durante 5 segundos...")

    capture = AudioCapture()
    vad = VAD(aggressiveness=2, silence_duration=2.0)

    speech_detected = False
    end_detected = False

    def vad_callback(audio_chunk):
        nonlocal speech_detected, end_detected

        # Procesar en frames VAD
        frame_size = vad.frame_size
        for i in range(0, len(audio_chunk), frame_size):
            frame = audio_chunk[i:i+frame_size]
            if len(frame) < frame_size:
                continue

            if vad.is_speech(frame):
                if not speech_detected:
                    logger.info("¡VOZ DETECTADA!")
                    speech_detected = True

            if vad.detect_speech_end(frame):
                if not end_detected:
                    logger.info("¡FIN DE VOZ DETECTADO!")
                    end_detected = True

    capture.register_callback(vad_callback)
    capture.start()

    time.sleep(5.0)

    capture.stop()

    logger.info(f"Voz detectada: {speech_detected}")
    logger.info(f"Fin detectado: {end_detected}")


def test_volume_control():
    """Test control de volumen."""
    logger.info("\n=== Test control de volumen ===")

    playback = AudioPlayback()

    # Volumen inicial
    initial_vol = playback.get_volume()
    logger.info(f"Volumen inicial: {initial_vol}%")

    # Generar tono
    duration = 1.0
    t = np.linspace(0, duration, int(16000 * duration))
    tone = (np.sin(2 * np.pi * 440 * t) * 32767 * 0.3).astype(np.int16)

    # Test subir volumen
    logger.info("Subiendo volumen...")
    playback.set_volume(30)
    logger.info(f"Reproduciendo a {playback.get_volume()}%")
    playback.play_array(tone)

    time.sleep(0.5)

    logger.info("Subiendo más...")
    playback.set_volume(70)
    logger.info(f"Reproduciendo a {playback.get_volume()}%")
    playback.play_array(tone)

    # Restaurar volumen
    playback.set_volume(initial_vol)
    logger.info(f"Volumen restaurado a {initial_vol}%")


def test_vad_with_generated_audio():
    """Test VAD con audio generado."""
    logger.info("\n=== Test VAD con audio generado ===")

    vad = VAD(sample_rate=16000, aggressiveness=3)

    # Generar audio de prueba (silencio + tono + silencio)
    duration = 5.0
    sample_rate = 16000

    silence_duration = 1.0
    tone_duration = 2.0

    # Silencio inicial
    silence1 = np.zeros(int(sample_rate * silence_duration), dtype=np.int16)

    # Tono (simula voz)
    t = np.linspace(0, tone_duration, int(sample_rate * tone_duration))
    tone = (np.sin(2 * np.pi * 200 * t) * 10000).astype(np.int16)

    # Silencio final
    silence2 = np.zeros(int(sample_rate * silence_duration * 2), dtype=np.int16)

    # Concatenar
    audio = np.concatenate([silence1, tone, silence2])

    logger.info(f"Procesando audio de {len(audio)/sample_rate:.2f}s...")
    has_speech, _ = vad.process_stream(audio)
    logger.info(f"¿Contiene voz? {has_speech}")

    # Obtener segmentos de voz
    segments = vad.get_speech_frames(audio)
    logger.info(f"Segmentos de voz detectados: {len(segments)}")
    for start, end in segments:
        start_time = start * vad.frame_duration_ms / 1000
        end_time = end * vad.frame_duration_ms / 1000
        logger.info(f"  Voz: {start_time:.2f}s - {end_time:.2f}s")


def test_buffer_consistency():
    """Test de consistencia del buffer circular."""
    logger.info("\n=== Test de consistencia del buffer ===")

    capture = AudioCapture(buffer_duration=5.0)

    # Verificar tamaño del buffer
    expected_size = 16000 * 5  # 5 segundos a 16kHz
    logger.info(f"Tamaño esperado del buffer: {expected_size} samples")

    capture.start()
    time.sleep(2.0)

    buffer = capture.get_buffer()
    logger.info(f"Samples en buffer: {len(buffer)}")

    # Verificar que no hay NaN o valores inválidos
    if np.any(np.isnan(buffer.astype(float))):
        logger.error("¡Buffer contiene NaN!")
    else:
        logger.info("Buffer: OK (sin NaN)")

    if np.any(np.isinf(buffer.astype(float))):
        logger.error("¡Buffer contiene valores infinitos!")
    else:
        logger.info("Buffer: OK (sin infinitos)")

    capture.stop()


if __name__ == '__main__':
    logger.info("Iniciando tests de audio...\n")

    try:
        # Tests que requieren hardware de audio
        print("\n" + "="*50)
        print("Tests con hardware de audio")
        print("="*50)

        # Descomentar para probar con hardware real
        # test_latency()
        # test_vad_realtime()
        # test_volume_control()

        # Tests sin hardware
        print("\n" + "="*50)
        print("Tests sin hardware de audio")
        print("="*50)

        test_vad_with_generated_audio()
        test_buffer_consistency()

        logger.info("\n✅ Todos los tests completados!")

    except Exception as e:
        logger.error(f"\n❌ Error en tests: {e}", exc_info=True)
