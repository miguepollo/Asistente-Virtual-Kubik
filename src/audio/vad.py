"""
Voice Activity Detection Module
Detecta cuando hay voz activa y cuándo hay silencio.
"""

import webrtcvad
import numpy as np
import logging
from collections import deque
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class VAD:
    """Voice Activity Detection usando WebRTC VAD."""

    # Duraciones de frame válidas para WebRTC VAD (ms)
    VALID_FRAME_DURATIONS = [10, 20, 30]

    def __init__(
        self,
        sample_rate: int = 16000,
        aggressiveness: int = 3,
        frame_duration_ms: int = 30,
        silence_duration: float = 2.0
    ):
        """
        Args:
            sample_rate: Frecuencia de muestreo (8000, 16000, 32000, 48000)
            aggressiveness: Nivel de agresividad (0-3, mayor=más estricto)
            frame_duration_ms: Duración del frame (10, 20, 30 ms)
            silence_duration: Duración de silencio para considerar fin (s)
        """
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Invalid sample rate: {sample_rate}")

        if frame_duration_ms not in self.VALID_FRAME_DURATIONS:
            raise ValueError(f"Invalid frame duration: {frame_duration_ms}")

        if not 0 <= aggressiveness <= 3:
            raise ValueError(f"Invalid aggressiveness: {aggressiveness}")

        self.sample_rate = sample_rate
        self.aggressiveness = aggressiveness
        self.frame_duration_ms = frame_duration_ms
        self.silence_duration = silence_duration

        # Calcular tamaño de frame en samples
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)

        # WebRTC VAD instance
        self.vad = webrtcvad.Vad(aggressiveness)

        # Estado
        self.speech_frames = 0
        self.silence_frames = 0
        self.silence_threshold = int(
            (silence_duration * 1000) / frame_duration_ms
        )

        logger.info(
            f"VAD initialized: {sample_rate}Hz, aggressiveness={aggressiveness}, "
            f"frame={frame_duration_ms}ms, silence_threshold={self.silence_threshold} frames"
        )

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Detecta si el chunk de audio contiene voz.

        Args:
            audio_chunk: Array de audio (int16)

        Returns:
            True si detecta voz, False si es silencio
        """
        # Asegurar que el chunk tiene el tamaño correcto
        if len(audio_chunk) != self.frame_size:
            # Rellenar con ceros si es necesario
            if len(audio_chunk) < self.frame_size:
                audio_chunk = np.pad(
                    audio_chunk,
                    (0, self.frame_size - len(audio_chunk)),
                    'constant'
                )
            else:
                audio_chunk = audio_chunk[:self.frame_size]

        # Convertir a bytes
        audio_bytes = audio_chunk.astype(np.int16).tobytes()

        try:
            return self.vad.is_speech(audio_bytes, self.sample_rate)
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False

    def detect_speech_end(self, audio_chunk: np.ndarray) -> bool:
        """
        Detecta si ha terminado la voz (silencio prolongado).

        Args:
            audio_chunk: Array de audio

        Returns:
            True si detecta fin de voz
        """
        is_speech = self.is_speech(audio_chunk)

        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1

        # Fin de voz: hubo voz antes y ahora silencio prolongado
        if self.speech_frames > 0 and self.silence_frames >= self.silence_threshold:
            self.reset()
            return True

        return False

    def reset(self) -> None:
        """Resetea el estado del detector."""
        self.speech_frames = 0
        self.silence_frames = 0

    def process_stream(
        self,
        audio_stream: np.ndarray,
        return_chunks: bool = False
    ) -> Tuple[bool, Optional[List[np.ndarray]]]:
        """
        Procesa un stream completo de audio.

        Args:
            audio_stream: Stream de audio completo
            return_chunks: Si True, retorna los chunks procesados

        Returns:
            (tiene_voz, chunks_opcionales)
        """
        has_speech = False
        chunks = [] if return_chunks else None

        # Dividir en frames
        num_frames = len(audio_stream) // self.frame_size

        for i in range(num_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio_stream[start:end]

            if self.is_speech(frame):
                has_speech = True
                if return_chunks:
                    chunks.append(frame)

        return has_speech, chunks

    def get_speech_frames(
        self,
        audio_stream: np.ndarray
    ) -> List[Tuple[int, int]]:
        """
        Retorna los timestamps de frames con voz.

        Args:
            audio_stream: Stream de audio completo

        Returns:
            Lista de (start_frame, end_frame) con voz
        """
        speech_segments = []
        in_speech = False
        start_frame = 0

        num_frames = len(audio_stream) // self.frame_size

        for i in range(num_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio_stream[start:end]

            if self.is_speech(frame):
                if not in_speech:
                    start_frame = i
                    in_speech = True
            else:
                if in_speech:
                    speech_segments.append((start_frame, i))
                    in_speech = False

        if in_speech:
            speech_segments.append((start_frame, num_frames))

        return speech_segments


# Test del módulo
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(name)s - %(message)s'
    )

    # Test con audio de prueba
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

    print(f"\nProcesando audio de {len(audio)/sample_rate:.2f}s...")
    has_speech, _ = vad.process_stream(audio)
    print(f"¿Contiene voz? {has_speech}")

    # Obtener segmentos de voz
    segments = vad.get_speech_frames(audio)
    print(f"Segmentos de voz detectados: {len(segments)}")
    for start, end in segments:
        start_time = start * vad.frame_duration_ms / 1000
        end_time = end * vad.frame_duration_ms / 1000
        print(f"  Voz: {start_time:.2f}s - {end_time:.2f}s")
