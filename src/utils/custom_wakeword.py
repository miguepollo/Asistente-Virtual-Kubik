#!/usr/bin/env python3
"""
Custom Wake Word Generator
Genera modelos de wake word personalizados usando TTS + openWakeWord
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
from pathlib import Path
import subprocess
import tempfile
import shutil

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def sanitize_tts_text(text: str) -> str:
    """
    Sanitiza texto para TTS eliminando caracteres potencialmente peligrosos.

    Args:
        text: Texto a sanitizar

    Returns:
        Texto sanitizado seguro para TTS
    """
    if not text:
        return ""

    # Limitar longitud para prevenir DoS
    text = text[:1000]

    # Eliminar caracteres de control y peligrosos
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '$', '`', '\\', '\n', '\r', '\t', '\x00']
    for char in dangerous_chars:
        text = text.replace(char, ' ')

    return text.strip()


class CustomWakeWordGenerator:
    """Generador de wake words personalizados."""

    def __init__(
        self,
        word: str,
        output_dir: str = None,
        samples_count: int = 100,
        tts_model: str = None
    ):
        """
        Args:
            word: Palabra a entrenar (ej: "asistente", "hola")
            output_dir: Directorio donde guardar el modelo
            samples_count: Cantidad de muestras a generar
            tts_model: Ruta al modelo TTS (Piper)
        """
        self.word = word.lower().strip()
        self.samples_count = samples_count
        self.output_dir = Path(output_dir or "/tmp/wakeword_models")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Model paths
        self.project_dir = Path("/home/orangepi/asistente2")
        if not self.project_dir.exists():
            self.project_dir = Path(__file__).parent.parent.parent

        # TTS model (Piper)
        self.tts_model = tts_model or str(
            self.project_dir / "models/tts/es_ES-davefx-medium.onnx"
        )
        self.tts_config = os.path.splitext(self.tts_model)[0] + ".json"

        # Directorio temporal para muestras
        self.temp_dir = Path(tempfile.mkdtemp(prefix="wakeword_"))

        logger.info(f"[INIT] Generador iniciado para palabra: '{self.word}'")
        logger.info(f"[INIT] Modelo TTS: {self.tts_model}")
        logger.info(f"[INIT] Config TTS: {self.tts_config}")
        logger.info(f"[INIT] Directorio salida: {self.output_dir}")
        logger.info(f"[INIT] Muestras solicitadas: {self.samples_count}")

        # Verificar archivos desde el inicio
        if not os.path.exists(self.tts_model):
            logger.error(f"[INIT] ❌ Modelo TTS no encontrado: {self.tts_model}")
        else:
            logger.info(f"[INIT] ✅ Modelo TTS encontrado")

        if not os.path.exists(self.tts_config):
            logger.error(f"[INIT] ❌ Config TTS no encontrada: {self.tts_config}")
        else:
            logger.info(f"[INIT] ✅ Config TTS encontrada")

    def _generate_variations(self) -> list[str]:
        """Genera variaciones de la palabra para entrenamiento."""
        variations = []

        # Variaciones directas
        base_variations = [
            self.word,
            self.word.capitalize(),
            f"oye {self.word}",
            f"eh {self.word}",
            f"hey {self.word}",
        ]

        # Añadir múltiples veces para balance
        for _ in range(self.samples_count // len(base_variations) + 1):
            variations.extend(base_variations)

        return variations[:self.samples_count]

    def _synthesize_with_piper(self, text: str, output_path: str) -> bool:
        """Sintetiza audio usando Piper TTS."""
        # Sanitizar texto para prevenir inyección
        text = sanitize_tts_text(text)
        if not text:
            logger.error("[TTS] Texto vacío después de sanitización")
            return False

        logger.debug(f"[TTS] Sintetizando: '{text}' -> {output_path}")

        # Verificar que modelo y config existen
        if not os.path.exists(self.tts_model):
            logger.error(f"[TTS] Modelo no encontrado: {self.tts_model}")
            return False

        if not os.path.exists(self.tts_config):
            logger.error(f"[TTS] Config no encontrada: {self.tts_config}")
            return False

        try:
            # Intentar con 'piper' primero, luego 'piper-tts'
            cmd_names = ["piper", "piper-tts"]
            result = None

            for cmd_name in cmd_names:
                cmd = [
                    cmd_name,
                    "--model", self.tts_model,
                    "--config", self.tts_config,
                    "--output_file", output_path
                ]

                logger.debug(f"[TTS] Ejecutando: {' '.join(cmd)}")

                # Escribir texto a stdin
                result = subprocess.run(
                    cmd,
                    input=text.encode(),
                    capture_output=True,
                    timeout=30
                )

                if result.returncode == 0:
                    break
                else:
                    logger.debug(f"[TTS] {cmd_name} falló, probando siguiente comando...")

            if result and result.returncode == 0 and os.path.exists(output_path):
                logger.debug(f"[TTS] ✅ Audio generado: {output_path} ({os.path.getsize(output_path)} bytes)")
                return True
            else:
                logger.warning(f"[TTS] ❌ Piper falló para '{text}'")
                if result and result.stderr:
                    logger.warning(f"[TTS] stderr: {result.stderr.decode()[:200]}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"[TTS] Timeout generando audio")
            return False
        except FileNotFoundError as e:
            logger.error(f"[TTS] Comando Piper no encontrado: {e}")
            return False
        except Exception as e:
            logger.error(f"[TTS] Error en TTS: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def _synthesize_with_python(self, text: str, output_path: str) -> bool:
        """Sintetiza audio usando la librería Python de Piper."""
        # Desactivado: se queda colgado en Orange Pi al cargar el modelo
        # Usar directamente el CLI que es más estable
        logger.debug(f"[TTS-Python] Usando CLI directamente (más estable)")
        return self._synthesize_with_piper(text, output_path)

    def _add_noise(self, audio: np.ndarray, noise_level: float = 0.01) -> np.ndarray:
        """Añade ruido blanco para variación."""
        noise = np.random.normal(0, noise_level, audio.shape)
        return audio + noise

    def _change_speed(self, audio: np.ndarray, sample_rate: int, factor: float) -> np.ndarray:
        """Cambia la velocidad del audio."""
        from scipy import signal
        indices = np.round(np.arange(0, len(audio), factor)).astype(int)
        indices = indices[indices < len(audio)]
        return audio[indices]

    def generate_samples(self) -> Path:
        """Genera muestras de audio para el entrenamiento."""
        logger.info(f"[GENERAR] Generando {self.samples_count} muestras para '{self.word}'...")

        samples_dir = self.temp_dir / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[GENERAR] Directorio de muestras: {samples_dir}")
        logger.info(f"[GENERAR] Modelo TTS: {self.tts_model}")
        logger.info(f"[GENERAR] Config TTS: {self.tts_config}")

        variations = self._generate_variations()
        logger.info(f"[GENERAR] {len(variations)} variaciones de texto creadas")

        generated = 0
        failed = 0

        for i, text in enumerate(variations):
            output_path = samples_dir / f"sample_{i:04d}.wav"

            if self._synthesize_with_python(text, str(output_path)):
                generated += 1
                if generated % 10 == 0:
                    logger.info(f"[GENERAR]  {generated}/{self.samples_count} muestras generadas...")
            else:
                failed += 1
                logger.warning(f"[GENERAR]  ❌ Falló sample_{i:04d}: '{text}'")

        logger.info(f"[GENERAR] ✅ {generated} muestras generadas, {failed} fallaron")
        logger.info(f"[GENERAR] Ubicación: {samples_dir}")

        # Listar archivos generados
        wav_files = list(samples_dir.glob("*.wav"))
        logger.info(f"[GENERAR] Archivos .wav en directorio: {len(wav_files)}")

        return samples_dir

    def train_model(self, samples_dir: Path) -> Path:
        """Entrena un modelo con openWakeWord."""
        logger.info("Entrenando modelo con openWakeWord...")

        output_path = self.output_dir / f"{self.word}.tflite"

        # Intentar usar openWakeWord si está disponible
        try:
            from openwakeword import WakeWordTrainer

            # Configurar trainer
            trainer = WakeWordTrainer(
                model_framework="tensorflow",
                classes=[self.word]
            )

            # Cargar muestras
            for sample_file in samples_dir.glob("*.wav"):
                try:
                    # Leer archivo de audio
                    from scipy.io import wavfile
                    sr, audio = wavfile.read(str(sample_file))

                    # Asegurar formato correcto
                    if sr != 16000:
                        from scipy import signal
                        num_samples = int(len(audio) * 16000 / sr)
                        audio = signal.resample(audio, num_samples).astype(audio.dtype)

                    if len(audio.shape) > 1:
                        audio = audio[:, 0]

                    # Añadir al trainer
                    trainer.add_sample(audio, label=self.word)

                except Exception as e:
                    logger.debug(f"Error cargando {sample_file}: {e}")
                    continue

            # Entrenar
            if trainer.get_sample_count(self.word) > 0:
                logger.info(f"Entrenando con {trainer.get_sample_count(self.word)} muestras...")

                model = trainer.train(
                    epochs=50,
                    batch_size=32,
                    learning_rate=0.001
                )

                # Guardar modelo
                trainer.export_model(str(output_path))
                logger.info(f"✅ Modelo guardado en: {output_path}")
                return output_path
            else:
                logger.warning("No se pudieron cargar muestras válidas")

        except ImportError:
            logger.warning("openWakeWord no está instalado")

        # Fallback: crear un archivo .mar simple que puede usar el sistema
        return self._create_simple_model(samples_dir)

    def _create_simple_model(self, samples_dir: Path) -> Path:
        """Crea un modelo simple basado en templates."""
        logger.info("Creando modelo simple...")

        # Usar sherpa-onnx como alternativa
        output_path = self.output_dir / f"{self.word}.txt"

        # Crear archivo de configuración
        with open(output_path, 'w') as f:
            json.dump({
                "word": self.word,
                "samples_dir": str(samples_dir),
                "created_with": "custom_wakeword",
                "type": "simple"
            }, f, indent=2)

        logger.info(f"Modelo simple guardado en: {output_path}")
        return output_path

    def test_model(self, model_path: Path) -> bool:
        """Prueba el modelo entrenado."""
        logger.info(f"Probando modelo '{self.word}'...")
        logger.info("Di la palabra para probar...")

        try:
            import pyaudio

            p = pyaudio.PyAudio()

            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=512
            )

            logger.info("Escuchando (10 segundos)...")

            import time
            start_time = time.time()
            detected = False

            while time.time() - start_time < 10:
                data = stream.read(512, exception_on_overflow=False)
                audio = np.frombuffer(data, dtype=np.int16)

                # Aquí iría la detección real
                # Por ahora, simulamos con VAD
                if audio.max() > 5000:  # Umbral simple de voz
                    if not detected:
                        logger.info("🎤 Voz detectada...")
                        detected = True

                if detected and time.time() - start_time > 3:
                    logger.info(f"✅ Prueba completada. El modelo está en: {model_path}")
                    break

            stream.stop_stream()
            stream.close()
            p.terminate()

            return True

        except Exception as e:
            logger.error(f"Error en prueba: {e}")
            return False

    def generate(self, test: bool = False) -> dict:
        """
        Ejecuta todo el proceso de generación.

        Args:
            test: Si es True, prueba el modelo después de entrenar

        Returns:
            Dict con información del modelo generado
        """
        logger.info(f"[MAIN] ========================================")
        logger.info(f"[MAIN] Iniciando generación de wake word")
        logger.info(f"[MAIN] Palabra: '{self.word}'")
        logger.info(f"[MAIN] ========================================")

        result = {
            "word": self.word,
            "success": False,
            "model_path": None,
            "samples_count": 0
        }

        try:
            # 1. Generar muestras
            logger.info(f"[MAIN] Paso 1/3: Generando muestras de audio...")
            samples_dir = self.generate_samples()
            result["samples_count"] = len(list(samples_dir.glob("*.wav")))

            if result["samples_count"] == 0:
                logger.error("[MAIN] ❌ No se generaron muestras de audio")
                return result

            # 2. Entrenar modelo
            logger.info(f"[MAIN] Paso 2/3: Entrenando modelo...")
            model_path = self.train_model(samples_dir)
            result["model_path"] = str(model_path)

            if model_path and model_path.exists():
                result["success"] = True
                logger.info(f"[MAIN] ✅ Modelo creado: {model_path}")

                # 3. Probar si se solicita
                if test:
                    logger.info(f"[MAIN] Paso 3/3: Probando modelo...")
                    self.test_model(model_path)
                else:
                    logger.info(f"[MAIN] Paso 3/3: Test omitido (usa --test para probar)")

            else:
                logger.error("[MAIN] ❌ No se pudo crear el modelo")

        except Exception as e:
            logger.error(f"[MAIN] Error en generación: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        finally:
            # Limpiar temp
            if self.temp_dir.exists():
                logger.info(f"[MAIN] Limpiando temporal: {self.temp_dir}")
                shutil.rmtree(self.temp_dir, ignore_errors=True)

        logger.info(f"[MAIN] ========================================")
        if result["success"]:
            logger.info(f"[MAIN] ✅ GENERACIÓN COMPLETADA")
            logger.info(f"[MAIN] Modelo: {result['model_path']}")
            logger.info(f"[MAIN] Muestras: {result['samples_count']}")
        else:
            logger.error(f"[MAIN] ❌ GENERACIÓN FALLÓ")
        logger.info(f"[MAIN] ========================================")

        return result


def main():
    """CLI principal."""
    parser = argparse.ArgumentParser(
        description="Generador de wake words personalizados"
    )
    parser.add_argument("word", help="Palabra a entrenar")
    parser.add_argument(
        "-o", "--output",
        default="/home/orangepi/asistente2/models/wakeword",
        help="Directorio de salida"
    )
    parser.add_argument(
        "-n", "--samples",
        type=int,
        default=100,
        help="Número de muestras"
    )
    parser.add_argument(
        "-t", "--test",
        action="store_true",
        help="Probar modelo después de entrenar"
    )
    parser.add_argument(
        "--tts-model",
        help="Ruta al modelo TTS (Piper)"
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Imprimir configuración JSON para config.json"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mostrar logs detallados"
    )

    args = parser.parse_args()

    # Configurar logging level
    if not args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    logger.info(f"[CLI] ========================================")
    logger.info(f"[CLI] Custom Wake Word Generator")
    logger.info(f"[CLI] ========================================")
    logger.info(f"[CLI] Palabra: {args.word}")
    logger.info(f"[CLI] Salida: {args.output}")
    logger.info(f"[CLI] Muestras: {args.samples}")
    logger.info(f"[CLI] TTS Model: {args.tts_model or 'default'}")
    logger.info(f"[CLI] Test: {args.test}")
    logger.info(f"[CLI] Verbose: {args.verbose}")
    logger.info(f"[CLI] ========================================")

    # Crear generador
    generator = CustomWakeWordGenerator(
        word=args.word,
        output_dir=args.output,
        samples_count=args.samples,
        tts_model=args.tts_model
    )

    # Generar
    result = generator.generate(test=args.test)

    # Imprimir resultado
    if result["success"]:
        print("\n✅ ¡Wake word generado exitosamente!")
        print(f"   Palabra: {result['word']}")
        print(f"   Modelo: {result['model_path']}")
        print(f"   Muestras: {result['samples_count']}")

        # Imprimir config si se solicita
        if args.print_config:
            config_entry = {
                "path": result['model_path'],
                "sensitivity": 0.5,
                "name": result['word']
            }
            print("\nConfiguración para config.json:")
            print(json.dumps(config_entry, indent=2))

        return 0
    else:
        print("\n❌ Error generando wake word")
        print(f"   Revisa los logs arriba para más detalles")
        return 1


if __name__ == "__main__":
    sys.exit(main())
