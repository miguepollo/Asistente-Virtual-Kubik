"""
Audio Capture Module
Gestiona la captura de audio desde el micrófono con buffer circular.
"""

import pyaudio
import numpy as np
import threading
import queue
from collections import deque
from typing import Optional, Callable, List
import logging

logger = logging.getLogger(__name__)


class AudioCapture:
    """Captura audio del micrófono con buffer circular."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 512,
        device_index: Optional[int] = None,
        buffer_duration: float = 5.0  # segundos
    ):
        """
        Args:
            sample_rate: Frecuencia de muestreo (Hz)
            channels: Número de canales (1=mono, 2=estéreo)
            chunk_size: Tamaño del chunk de audio
            device_index: Índice del dispositivo (None=default)
            buffer_duration: Duración del buffer circular (segundos)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index

        # Buffer circular
        buffer_size = int(sample_rate * buffer_duration)
        self.buffer = deque(maxlen=buffer_size)
        self.buffer_lock = threading.Lock()

        # PyAudio setup
        self.p = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_running = False

        # Thread de captura
        self.capture_thread: Optional[threading.Thread] = None

        # Callbacks
        self.callbacks: List[Callable] = []

        logger.info(
            f"AudioCapture initialized: {sample_rate}Hz, "
            f"{channels}ch, chunk={chunk_size}"
        )

    def start(self) -> None:
        """Inicia la captura de audio."""
        if self.is_running:
            logger.warning("Audio capture already running")
            return

        try:
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )

            self.is_running = True
            self.stream.start_stream()
            logger.info("Audio capture started")

        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            raise

    def stop(self) -> None:
        """Detiene la captura de audio."""
        if not self.is_running:
            return

        self.is_running = False

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        logger.info("Audio capture stopped")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback interno de PyAudio."""
        if status:
            logger.warning(f"Audio callback status: {status}")

        # Convertir a numpy array
        audio_data = np.frombuffer(in_data, dtype=np.int16)

        # Añadir al buffer circular
        with self.buffer_lock:
            self.buffer.extend(audio_data)

        # Llamar callbacks registrados
        for callback in self.callbacks:
            try:
                callback(audio_data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return (None, pyaudio.paContinue)

    def register_callback(self, callback: Callable) -> None:
        """Registra un callback para procesar audio en tiempo real."""
        self.callbacks.append(callback)

    def get_buffer(self, duration: Optional[float] = None) -> np.ndarray:
        """
        Obtiene audio del buffer.

        Args:
            duration: Duración en segundos (None=todo el buffer)

        Returns:
            Array de audio
        """
        with self.buffer_lock:
            if duration is None:
                return np.array(self.buffer, dtype=np.int16)
            else:
                samples = int(self.sample_rate * duration)
                samples = min(samples, len(self.buffer))
                return np.array(list(self.buffer)[-samples:], dtype=np.int16)

    def clear_buffer(self) -> None:
        """Limpia el buffer circular."""
        with self.buffer_lock:
            self.buffer.clear()

    def get_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Obtiene un chunk de audio (bloqueante).

        Args:
            timeout: Tiempo máximo de espera

        Returns:
            Chunk de audio o None si timeout
        """
        # Para uso síncrono, capturar directamente
        if not self.is_running:
            self.start()

        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            return np.frombuffer(data, dtype=np.int16)
        except Exception as e:
            logger.error(f"Error reading audio chunk: {e}")
            return None

    def list_devices(self) -> List[dict]:
        """Lista todos los dispositivos de audio disponibles."""
        devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # Solo dispositivos de entrada
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })
        return devices

    def __del__(self):
        """Cleanup al destruir el objeto."""
        self.stop()
        self.p.terminate()


# Test del módulo
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(name)s - %(message)s'
    )

    # Listar dispositivos
    capture = AudioCapture()
    print("\nDispositivos de audio disponibles:")
    for device in capture.list_devices():
        print(f"  [{device['index']}] {device['name']} "
              f"({device['channels']}ch @ {device['sample_rate']}Hz)")

    # Test captura
    print("\nIniciando captura de 5 segundos...")
    capture.start()

    import time
    time.sleep(5)

    # Obtener buffer
    audio_data = capture.get_buffer(duration=5.0)
    print(f"Capturados {len(audio_data)} samples "
          f"({len(audio_data)/capture.sample_rate:.2f}s)")

    capture.stop()
