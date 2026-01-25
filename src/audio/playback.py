"""
Audio Playback Module
Gestiona la reproducción de audio por el altavoz.
"""

import pyaudio
import wave
import subprocess
import logging
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class AudioPlayback:
    """Reproduce audio por el altavoz con control de volumen."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device_index: Optional[int] = None
    ):
        """
        Args:
            sample_rate: Frecuencia de muestreo
            channels: Número de canales
            device_index: Índice del dispositivo de salida
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index

        self.p = pyaudio.PyAudio()
        self.current_stream: Optional[pyaudio.Stream] = None

        logger.info(f"AudioPlayback initialized: {sample_rate}Hz, {channels}ch")

    def play_wav(self, filepath: str, blocking: bool = True) -> None:
        """
        Reproduce un archivo WAV.

        Args:
            filepath: Ruta al archivo WAV
            blocking: Si True, espera a que termine la reproducción
        """
        try:
            # Abrir archivo WAV
            wf = wave.open(filepath, 'rb')

            # Crear stream
            stream = self.p.open(
                format=self.p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
                output_device_index=self.device_index
            )

            self.current_stream = stream

            # Reproducir
            chunk_size = 1024
            data = wf.readframes(chunk_size)

            while data:
                stream.write(data)
                data = wf.readframes(chunk_size)

            if blocking:
                stream.stop_stream()
                stream.close()
                self.current_stream = None

            wf.close()
            logger.debug(f"Played audio file: {filepath}")

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            raise

    def play_array(
        self,
        audio_data: np.ndarray,
        sample_rate: Optional[int] = None,
        blocking: bool = True
    ) -> None:
        """
        Reproduce audio desde un numpy array.

        Args:
            audio_data: Array de audio (int16)
            sample_rate: Frecuencia de muestreo (None=usar default)
            blocking: Si True, espera a que termine
        """
        if sample_rate is None:
            sample_rate = self.sample_rate

        try:
            stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=sample_rate,
                output=True,
                output_device_index=self.device_index
            )

            # Convertir a bytes
            audio_bytes = audio_data.astype(np.int16).tobytes()

            stream.write(audio_bytes)

            if blocking:
                stream.stop_stream()
                stream.close()

            logger.debug(f"Played audio array: {len(audio_data)} samples")

        except Exception as e:
            logger.error(f"Error playing array: {e}")
            raise

    def stop(self) -> None:
        """Detiene la reproducción actual."""
        if self.current_stream:
            self.current_stream.stop_stream()
            self.current_stream.close()
            self.current_stream = None

    def set_volume(self, level: int) -> None:
        """
        Ajusta el volumen del sistema.

        Args:
            level: Nivel de volumen (0-100)
        """
        level = max(0, min(100, level))  # Clamp 0-100

        try:
            # Usando amixer
            subprocess.run(
                ['amixer', 'sset', 'Master', f'{level}%'],
                check=True,
                capture_output=True
            )
            logger.info(f"Volume set to {level}%")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error setting volume: {e}")

    def get_volume(self) -> int:
        """
        Obtiene el volumen actual del sistema.

        Returns:
            Nivel de volumen (0-100)
        """
        try:
            result = subprocess.run(
                ['amixer', 'get', 'Master'],
                check=True,
                capture_output=True,
                text=True
            )

            # Parsear output (formato: [XX%])
            import re
            match = re.search(r'\[(\d+)%\]', result.stdout)
            if match:
                return int(match.group(1))

            return 50  # Default

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error getting volume: {e}")
            return 50

    def volume_up(self, step: int = 10) -> None:
        """Sube el volumen."""
        current = self.get_volume()
        self.set_volume(current + step)

    def volume_down(self, step: int = 10) -> None:
        """Baja el volumen."""
        current = self.get_volume()
        self.set_volume(current - step)

    def list_devices(self) -> list:
        """Lista dispositivos de salida disponibles."""
        devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxOutputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })
        return devices

    def __del__(self):
        """Cleanup."""
        self.stop()
        self.p.terminate()


# Test del módulo
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(name)s - %(message)s'
    )

    playback = AudioPlayback()

    # Listar dispositivos
    print("\nDispositivos de salida disponibles:")
    for device in playback.list_devices():
        print(f"  [{device['index']}] {device['name']}")

    # Test volumen
    print(f"\nVolumen actual: {playback.get_volume()}%")
    playback.set_volume(50)
    print(f"Volumen ajustado a: {playback.get_volume()}%")

    # Test reproducción (genera un tono de prueba)
    print("\nGenerando tono de prueba...")
    duration = 2.0
    frequency = 440.0  # La (A4)

    t = np.linspace(0, duration, int(16000 * duration))
    audio = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.3).astype(np.int16)

    print("Reproduciendo tono...")
    playback.play_array(audio)
    print("¡Hecho!")
