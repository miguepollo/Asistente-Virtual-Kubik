"""
Wake Word Detection Engine - Porcupine / openWakeWord / Vosk
Detecta múltiples palabras de activación personalizadas.

Soporta tres motores:
- Porcupine (archivos .ppn) - Alta precisión, requiere API key
- openWakeWord (archivos .tflite) - Open source, entrenable localmente
- Vosk (modelos de voz) - Usa STT para detectar palabras, offline
"""

import logging
from typing import Optional, Callable, List, Dict
import time
import os
import json
import numpy as np
from queue import Queue
import threading
import subprocess
import sys

# Desinstalar Porcupine si está instalado (no soporta ARM Cortex-A55)
try:
    import pkg_resources
    for pkg in list(pkg_resources.working_set):
        if pkg.project_name == "pvporcupine":
            logging.warning(f"Desinstalando {pkg.project_name} (no soportado en esta plataforma)...")
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "pvporcupine"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.warning("Porcupine desinstalado. Se usará Vosk en su lugar.")
            break
except Exception:
    pass

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except (ImportError, NotImplementedError):
    PORCUPINE_AVAILABLE = False

try:
    from openwakeword import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    vosk = None

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Detector de wake words usando Porcupine con soporte para múltiples palabras."""

    def __init__(
        self,
        access_key: str,
        keyword_paths: List[str] | str = None,
        keywords: List[Dict] = None,
        sensitivities: List[float] | float = None,
        model_path: Optional[str] = None
    ):
        """
        Args:
            access_key: API key de Picovoice
            keyword_paths: Ruta(s) al archivo .ppn del wake word (legacy, una sola ruta)
            keywords: Lista de dicts con keyword configs:
                [{"path": "/ruta/a/word.ppn", "sensitivity": 0.5, "name": "palabra"}, ...]
            sensitivities: Sensibilidad/es (0.0-1.1), usado si keywords es None
            model_path: Ruta al modelo Porcupine (opcional)
        """
        self.access_key = access_key
        self.model_path = model_path
        self.porcupine = None
        self._initialized = False
        self.detections = {}  # {keyword_name: count}
        self.start_time = time.time()

        # Procesar configuración de keywords
        self.keywords = []
        if keywords:
            # Formato nuevo: lista de dicts
            for kw in keywords:
                self.keywords.append({
                    "path": kw["path"],
                    "sensitivity": kw.get("sensitivity", 0.5),
                    "name": kw.get("name", os.path.basename(kw["path"]).replace(".ppn", ""))
                })
        elif keyword_paths:
            # Formato legacy/compatibilidad
            if isinstance(keyword_paths, str):
                keyword_paths = [keyword_paths]
            if isinstance(sensitivities, (int, float)):
                sensitivities = [sensitivities] * len(keyword_paths)
            elif sensitivities is None:
                sensitivities = [0.5] * len(keyword_paths)

            for path, sens in zip(keyword_paths, sensitivities):
                self.keywords.append({
                    "path": path,
                    "sensitivity": sens,
                    "name": os.path.basename(path).replace(".ppn", "")
                })

        # Inicializar contador de detecciones
        for kw in self.keywords:
            self.detections[kw["name"]] = 0

        if PORCUPINE_AVAILABLE:
            self._initialize()
        else:
            logger.error("Porcupine no está instalado")

    def _initialize(self) -> None:
        """Inicializa el detector Porcupine."""
        if not self.keywords:
            logger.error("No hay keywords configuradas")
            return

        try:
            keyword_paths = [kw["path"] for kw in self.keywords]
            sensitivities = [kw["sensitivity"] for kw in self.keywords]

            # Verificar que los archivos existen
            for path in keyword_paths:
                if not os.path.exists(path):
                    logger.error(f"Keyword file no encontrado: {path}")
                    return

            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=keyword_paths,
                sensitivities=sensitivities,
                model_path=self.model_path
            )

            self.sample_rate = self.porcupine.sample_rate
            self.frame_length = self.porcupine.frame_length

            self._initialized = True

            keyword_names = [kw["name"] for kw in self.keywords]
            logger.info(
                f"Porcupine inicializado con {len(self.keywords)} keyword(s): "
                f"{keyword_names}, sample_rate={self.sample_rate}, "
                f"frame_length={self.frame_length}"
            )

        except Exception as e:
            logger.error(f"Error inicializando Porcupine: {e}")

    def process(self, audio_frame) -> tuple[bool, Optional[str]]:
        """
        Procesa un frame de audio para detectar wake word.

        Args:
            audio_frame: Frame de audio (int16, longitud=frame_length)

        Returns:
            Tuple (detectado, keyword_name) donde:
            - detectado: True si detecta wake word
            - keyword_name: Nombre de la palabra detectada (o None)
        """
        if not self._initialized:
            return False, None

        try:
            keyword_index = self.porcupine.process(audio_frame)
            if keyword_index >= 0 and keyword_index < len(self.keywords):
                kw_name = self.keywords[keyword_index]["name"]
                self.detections[kw_name] = self.detections.get(kw_name, 0) + 1
                total = sum(self.detections.values())
                logger.info(
                    f"¡Wake word '{kw_name}' detectado! "
                    f"(esta: {self.detections[kw_name]}, total: {total})"
                )
                return True, kw_name
            return False, None

        except Exception as e:
            logger.error(f"Error procesando audio: {e}")
            return False, None

    def is_available(self) -> bool:
        """Retorna si el detector está disponible."""
        return self._initialized

    def get_stats(self) -> dict:
        """Retorna estadísticas."""
        uptime = time.time() - self.start_time
        total_detections = sum(self.detections.values())
        return {
            "keywords": [kw["name"] for kw in self.keywords],
            "detections": self.detections,
            "total_detections": total_detections,
            "uptime_seconds": uptime,
            "detections_per_hour": (total_detections / uptime) * 3600 if uptime > 0 else 0
        }

    def reset_stats(self) -> None:
        """Resetea estadísticas."""
        for kw in self.keywords:
            self.detections[kw["name"]] = 0
        self.start_time = time.time()

    def get_keyword_names(self) -> List[str]:
        """Retorna lista de nombres de keywords configurados."""
        return [kw["name"] for kw in self.keywords]

    def add_keyword(self, path: str, sensitivity: float = 0.5, name: str = None) -> bool:
        """
        Agrega un nuevo keyword dinámicamente.

        Args:
            path: Ruta al archivo .ppn
            sensitivity: Sensibilidad (0.0-1.0)
            name: Nombre opcional del keyword

        Returns:
            True si se agregó exitosamente
        """
        if not os.path.exists(path):
            logger.error(f"Keyword file no encontrado: {path}")
            return False

        kw_name = name or os.path.basename(path).replace(".ppn", "")

        # Verificar duplicado
        if kw_name in [kw["name"] for kw in self.keywords]:
            logger.warning(f"Keyword '{kw_name}' ya existe")
            return False

        # Guardar estado actual
        old_initialized = self._initialized

        # Limpiar instancia anterior
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
        self._initialized = False

        # Agregar nuevo keyword
        self.keywords.append({
            "path": path,
            "sensitivity": sensitivity,
            "name": kw_name
        })
        self.detections[kw_name] = 0

        # Re-inicializar
        self._initialize()

        return self._initialized

    def remove_keyword(self, name: str) -> bool:
        """
        Remueve un keyword por nombre.

        Args:
            name: Nombre del keyword a remover

        Returns:
            True si se removió exitosamente
        """
        if len(self.keywords) <= 1:
            logger.error("No se puede remover el único keyword")
            return False

        # Buscar y remover
        kw_to_remove = None
        for kw in self.keywords:
            if kw["name"] == name:
                kw_to_remove = kw
                break

        if not kw_to_remove:
            logger.warning(f"Keyword '{name}' no encontrado")
            return False

        # Limpiar instancia anterior
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
        self._initialized = False

        # Remover keyword
        self.keywords.remove(kw_to_remove)
        self.detections.pop(name, None)

        # Re-inicializar
        self._initialize()

        return self._initialized

    def reload_keywords(self, keywords: List[Dict]) -> bool:
        """
        Recarga completamente la lista de keywords.

        Args:
            keywords: Nueva lista de configs [{"path": "...", "sensitivity": 0.5, "name": "..."}]

        Returns:
            True si se recargó exitosamente
        """
        # Limpiar instancia anterior
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
        self._initialized = False

        # Procesar nuevos keywords
        self.keywords = []
        self.detections = {}

        for kw in keywords:
            name = kw.get("name", os.path.basename(kw["path"]).replace(".ppn", ""))
            self.keywords.append({
                "path": kw["path"],
                "sensitivity": kw.get("sensitivity", 0.5),
                "name": name
            })
            self.detections[name] = 0

        # Re-inicializar
        self._initialize()

        return self._initialized

    def __del__(self):
        """Cleanup."""
        if self.porcupine:
            self.porcupine.delete()


class OpenWakeWordDetector:
    """Detector de wake words usando openWakeWord.

    openWakeWord es una alternativa open-source que permite entrenar
    modelos personalizados sin necesidad de servicios externos.
    """

    def __init__(
        self,
        keyword_paths: List[str] | str = None,
        keywords: List[Dict] = None,
        threshold: float = 0.5,
        model_path: Optional[str] = None
    ):
        """
        Args:
            keyword_paths: Ruta(s) a archivos .tflite del modelo
            keywords: Lista de dicts con configs:
                [{"path": "/ruta/a/model.tflite", "threshold": 0.5, "name": "palabra"}, ...]
            threshold: Umbral de detección (0.0-1.0)
            model_path: Ruta al modelo base de openWakeWord (opcional)
        """
        self.model = None
        self._initialized = False
        self.detections = {}  # {keyword_name: count}
        self.start_time = time.time()
        self.threshold = threshold

        # Procesar configuración de keywords
        self.keywords = []
        if keywords:
            for kw in keywords:
                path = kw["path"]
                name = kw.get("name", os.path.basename(path).replace(".tflite", ""))
                self.keywords.append({
                    "path": path,
                    "threshold": kw.get("threshold", threshold),
                    "name": name
                })
        elif keyword_paths:
            if isinstance(keyword_paths, str):
                keyword_paths = [keyword_paths]
            for path in keyword_paths:
                self.keywords.append({
                    "path": path,
                    "threshold": threshold,
                    "name": os.path.basename(path).replace(".tflite", "")
                })

        # Inicializar contadores
        for kw in self.keywords:
            self.detections[kw["name"]] = 0

        if OPENWAKEWORD_AVAILABLE:
            self._initialize()
        else:
            logger.error("openWakeWord no está instalado. Instala con: pip install openwakeword")

    def _initialize(self) -> None:
        """Inicializa el detector openWakeWord."""
        if not self.keywords:
            logger.error("No hay keywords configuradas")
            return

        try:
            # Filtrar solo archivos tflite que existen
            valid_paths = []
            for kw in self.keywords:
                path = kw["path"]
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    logger.warning(f"Modelo no encontrado: {path}")

            if not valid_paths:
                logger.error("No se encontraron modelos válidos")
                return

            # Crear modelo con los archivos personalizados
            self.model = Model(
                wakeword_models=valid_paths,
                inference_framework="tflite"
            )

            self.sample_rate = 16000  # openWakeWord usa 16kHz
            self.frame_length = 1280  # 80ms frames

            self._initialized = True

            keyword_names = [kw["name"] for kw in self.keywords]
            logger.info(
                f"openWakeWord inicializado con {len(self.keywords)} modelo(s): "
                f"{keyword_names}"
            )

        except Exception as e:
            logger.error(f"Error inicializando openWakeWord: {e}")

    def process(self, audio_frame) -> tuple[bool, Optional[str]]:
        """
        Procesa un frame de audio para detectar wake word.

        Args:
            audio_frame: Frame de audio (int16, longitud=frame_length)

        Returns:
            Tuple (detectado, keyword_name)
        """
        if not self._initialized:
            return False, None

        try:
            # openWakeWord usa float32 y necesita arrays más grandes
            # Convertir int16 a float32 normalizado
            if audio_frame.dtype != np.float32:
                audio_float = audio_frame.astype(np.float32) / 32768.0
            else:
                audio_float = audio_frame

            # Predicción necesita al least 1280 samples (80ms)
            if len(audio_float) < 1280:
                return False, None

            # Detectar
            predictions = self.model.predict(audio_float)

            # Buscar detecciones sobre el umbral
            for kw in self.keywords:
                name = kw["name"]
                threshold = kw["threshold"]

                if name in predictions and predictions[name] > threshold:
                    self.detections[name] = self.detections.get(name, 0) + 1
                    total = sum(self.detections.values())
                    logger.info(
                        f"¡Wake word '{name}' detectado! (conf: {predictions[name]:.3f}, "
                        f"esta: {self.detections[name]}, total: {total})"
                    )
                    return True, name

            return False, None

        except Exception as e:
            logger.error(f"Error procesando audio: {e}")
            return False, None

    def is_available(self) -> bool:
        """Retorna si el detector está disponible."""
        return self._initialized

    def get_stats(self) -> dict:
        """Retorna estadísticas."""
        uptime = time.time() - self.start_time
        total_detections = sum(self.detections.values())
        return {
            "engine": "openWakeWord",
            "keywords": [kw["name"] for kw in self.keywords],
            "detections": self.detections,
            "total_detections": total_detections,
            "uptime_seconds": uptime,
            "detections_per_hour": (total_detections / uptime) * 3600 if uptime > 0 else 0
        }

    def reset_stats(self) -> None:
        """Resetea estadísticas."""
        for kw in self.keywords:
            self.detections[kw["name"]] = 0
        self.start_time = time.time()

    def get_keyword_names(self) -> List[str]:
        """Retorna lista de nombres de keywords configurados."""
        return [kw["name"] for kw in self.keywords]


class VoskWakeWordDetector:
    """Detector de wake words usando Vosk STT.

    Usa Vosk para transcribir audio continuamente y detecta palabras clave.
    Ventaja: No requiere modelos .ppn especiales, funciona con cualquier idioma.
    Desventaja: Mayor uso de CPU que Porcupine/openWakeWord.
    """

    def __init__(
        self,
        keywords: List[str] | str = None,
        model_path: str = None,
        sample_rate: int = 16000,
        detection_threshold: float = 0.5
    ):
        """
        Args:
            keywords: Palabra(s) a detectar (ej: "asistente", "hola")
            model_path: Ruta al modelo Vosk
            sample_rate: Tasa de muestreo del audio (16000 para Vosk)
            detection_threshold: Confianza mínima para detección (0.0-1.0)
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.detection_threshold = detection_threshold
        self.model = None
        self.recognizer = None
        self._initialized = False
        self.detections = {}  # {keyword: count}
        self.start_time = time.time()
        self._last_detection_time = {}  # Cooldown por keyword
        self._cooldown_seconds = 2.0  # Cooldown entre detecciones del mismo keyword

        # Procesar keywords
        if isinstance(keywords, str):
            keywords = [keywords]

        self.keywords = [kw.lower().strip() for kw in keywords] if keywords else ["asistente"]

        # Inicializar contadores
        for kw in self.keywords:
            self.detections[kw] = 0
            self._last_detection_time[kw] = 0

        if VOSK_AVAILABLE:
            self._initialize()
        else:
            logger.error("Vosk no está instalado. Instala con: pip install vosk")

    def _initialize(self) -> None:
        """Inicializa el detector Vosk."""
        if not self.model_path:
            # Intentar usar modelo por defecto
            self.model_path = os.path.join(
                os.path.dirname(__file__),
                "../../models/stt/vosk-model-small-es-0.42"
            )
            self.model_path = os.path.abspath(self.model_path)

        if not os.path.exists(self.model_path):
            logger.error(f"Modelo Vosk no encontrado: {self.model_path}")
            return

        try:
            # Cargar modelo Vosk
            self.model = vosk.Model(self.model_path)

            # Crear recognizer
            self.recognizer = vosk.KaldiRecognizer(
                self.model,
                self.sample_rate,
                # Usamos gramática para mejorar detección de keywords
                # Opcional: puedes agregar palabras específicas aquí
            )

            self.sample_rate = 16000  # Vosk siempre usa 16kHz
            self.frame_length = 1600  # 100ms frames para procesamiento continuo

            self._initialized = True

            logger.info(
                f"Vosk inicializado con {len(self.keywords)} keyword(s): "
                f"{self.keywords}, model_path={self.model_path}"
            )

        except Exception as e:
            logger.error(f"Error inicializando Vosk: {e}")

    def process(self, audio_frame) -> tuple[bool, Optional[str]]:
        """
        Procesa un frame de audio para detectar wake word.

        Args:
            audio_frame: Frame de audio (int16, longitud=frame_length)

        Returns:
            Tuple (detectado, keyword_name)
        """
        if not self._initialized:
            return False, None

        try:
            current_time = time.time()

            # Convertir int16 a bytes para Vosk
            if isinstance(audio_frame, np.ndarray):
                audio_bytes = audio_frame.tobytes()
            else:
                audio_bytes = audio_frame

            # Intentar reconocer
            if self.recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").lower().strip()

                # Verificar si alguna keyword está en el texto
                for kw in self.keywords:
                    # Buscar keyword como palabra completa o parte del texto
                    if (kw in text or
                        text in kw or
                        # Variaciones con articulos
                        f"oye {kw}" in text or
                        f"eh {kw}" in text or
                        f"hey {kw}" in text):

                        # Verificar cooldown
                        last_time = self._last_detection_time.get(kw, 0)
                        if current_time - last_time >= self._cooldown_seconds:
                            self.detections[kw] = self.detections.get(kw, 0) + 1
                            self._last_detection_time[kw] = current_time
                            total = sum(self.detections.values())

                            logger.info(
                                f"¡Wake word '{kw}' detectado! "
                                f"(texto: '{text}', esta: {self.detections[kw]}, "
                                f"total: {total})"
                            )
                            return True, kw

            else:
                # Resultado parcial (útil para palabras largas)
                partial = self.recognizer.PartialResult()
                if partial:
                    partial_result = json.loads(partial)
                    partial_text = partial_result.get("partial", "").lower()

                    # Verificar keyword en resultado parcial
                    for kw in self.keywords:
                        if kw in partial_text:
                            # No incrementar contador en parcial, solo si está completo
                            pass

            return False, None

        except Exception as e:
            logger.error(f"Error procesando audio: {e}")
            return False, None

    def is_available(self) -> bool:
        """Retorna si el detector está disponible."""
        return self._initialized

    def get_stats(self) -> dict:
        """Retorna estadísticas."""
        uptime = time.time() - self.start_time
        total_detections = sum(self.detections.values())
        return {
            "engine": "vosk",
            "keywords": self.keywords,
            "detections": self.detections,
            "total_detections": total_detections,
            "uptime_seconds": uptime,
            "detections_per_hour": (total_detections / uptime) * 3600 if uptime > 0 else 0
        }

    def reset_stats(self) -> None:
        """Resetea estadísticas."""
        for kw in self.keywords:
            self.detections[kw] = 0
        self.start_time = time.time()

    def get_keyword_names(self) -> List[str]:
        """Retorna lista de nombres de keywords configurados."""
        return self.keywords.copy()

    def add_keyword(self, keyword: str) -> bool:
        """
        Agrega un nuevo keyword dinámicamente.

        Args:
            keyword: Palabra a detectar

        Returns:
            True si se agregó exitosamente
        """
        keyword = keyword.lower().strip()
        if keyword in self.keywords:
            logger.warning(f"Keyword '{keyword}' ya existe")
            return False

        self.keywords.append(keyword)
        self.detections[keyword] = 0
        self._last_detection_time[keyword] = 0
        logger.info(f"Keyword '{keyword}' agregado")
        return True

    def remove_keyword(self, keyword: str) -> bool:
        """
        Remueve un keyword.

        Args:
            keyword: Palabra a remover

        Returns:
            True si se removió exitosamente
        """
        if len(self.keywords) <= 1:
            logger.error("No se puede remover el único keyword")
            return False

        keyword = keyword.lower().strip()
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            self.detections.pop(keyword, None)
            self._last_detection_time.pop(keyword, None)
            logger.info(f"Keyword '{keyword}' removido")
            return True

        logger.warning(f"Keyword '{keyword}' no encontrado")
        return False


class WakeWordEngine:
    """Motor completo de wake word con integración de audio y soporte para múltiples keywords.

    Soporta tres motores:
    - Porcupine (archivos .ppn) - requiere API key de Picovoice
    - openWakeWord (archivos .tflite) - open-source, sin API key
    - Vosk (modelos STT) - usa reconocimiento de voz para detectar palabras
    """

    def __init__(
        self,
        access_key: str = None,
        keyword_path: str = None,
        sensitivity: float = 0.5,
        keywords: List[Dict] = None,
        wake_words: List[str] = None,
        on_detection: Optional[Callable] = None,
        engine: str = "auto",
        model_path: str = None
    ):
        """
        Args:
            access_key: API key Picovoice (solo para Porcupine)
            keyword_path: Ruta al modelo (legacy, para un solo keyword)
            sensitivity: Sensibilidad/umbral (0.0-1.0)
            keywords: Lista de configs [{"path": "...", "sensitivity": 0.5, "name": "..."}]
                      Para Porcupine/openWakeWord
            wake_words: Lista de palabras para detectar (solo para Vosk)
                        ej: ["asistente", "hola"]
            on_detection: Callback cuando se detecta, recibe (keyword_name)
            engine: Motor a usar ("auto", "porcupine", "openwakeword", "vosk")
            model_path: Ruta al modelo (para Vosk o modelos personalizados)
        """
        self.on_detection = on_detection
        self.is_running = False
        self.engine_type = engine
        self.model_path = model_path

        # Procesar keywords según motor
        kw_list = []
        if keywords:
            kw_list = keywords
        elif keyword_path:
            kw_list = [{
                "path": keyword_path,
                "sensitivity": sensitivity,
                "name": os.path.basename(keyword_path).split('.')[0]
            }]

        # Auto-detectar motor basado en configuración
        if engine == "auto":
            # Si se especifican wake_words, usar Vosk
            if wake_words:
                self.engine_type = "vosk"
            elif kw_list and "path" in kw_list[0]:
                first_path = kw_list[0]["path"]

                if first_path.endswith(".tflite") or first_path.endswith(".mar"):
                    self.engine_type = "openwakeword"
                elif first_path.endswith(".ppn"):
                    self.engine_type = "porcupine"
                else:
                    # Intentar detectar por disponibilidad
                    if VOSK_AVAILABLE:
                        self.engine_type = "vosk"
                    elif access_key and PORCUPINE_AVAILABLE:
                        self.engine_type = "porcupine"
                    elif OPENWAKEWORD_AVAILABLE:
                        self.engine_type = "openwakeword"
                    else:
                        self.engine_type = "vosk"  # Default preferido
            else:
                # Sin keywords específicos, usar Vosk por defecto
                self.engine_type = "vosk"

        # Crear detector según tipo
        if self.engine_type == "vosk":
            if not VOSK_AVAILABLE:
                logger.error("Vosk no está instalado")
                raise ValueError("Vosk no disponible. Instala con: pip install vosk")

            # Usar wake_words o extraer de keywords
            vw_keywords = wake_words or []
            if not vw_keywords and kw_list:
                vw_keywords = [kw.get("name", "asistente") for kw in kw_list]
            if not vw_keywords:
                vw_keywords = ["asistente"]

            self.detector = VoskWakeWordDetector(
                keywords=vw_keywords,
                model_path=model_path
            )
            logger.info(f"Usando motor: Vosk (keywords: {vw_keywords})")

        elif self.engine_type == "openwakeword":
            if not OPENWAKEWORD_AVAILABLE:
                logger.warning("openWakeWord no disponible, usando configuración simple")
            self.detector = OpenWakeWordDetector(keywords=kw_list, threshold=sensitivity)
            logger.info("Usando motor: openWakeWord")

        else:  # porcupine (default)
            if not access_key:
                raise ValueError("Porcupine requiere access_key")

            # Filtrar solo archivos .ppn
            ppn_keywords = [kw for kw in kw_list if kw["path"].endswith(".ppn")]

            if not ppn_keywords:
                raise ValueError("No se encontraron archivos .ppn para Porcupine")

            self.detector = WakeWordDetector(
                access_key=access_key,
                keywords=ppn_keywords
            )
            logger.info("Usando motor: Porcupine")

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
                detected, keyword_name = self.detector.process(frame)
                if detected:
                    if self.on_detection:
                        try:
                            # Callback recibe el nombre del keyword detectado
                            self.on_detection(keyword_name)
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

    def get_keyword_names(self) -> List[str]:
        """Retorna lista de nombres de keywords configurados."""
        return self.detector.get_keyword_names()

    def add_keyword(self, path: str, sensitivity: float = 0.5, name: str = None) -> bool:
        """Agrega un nuevo keyword dinámicamente."""
        return self.detector.add_keyword(path, sensitivity, name)

    def remove_keyword(self, name: str) -> bool:
        """Remueve un keyword por nombre."""
        return self.detector.remove_keyword(name)

    def reload_keywords(self, keywords: List[Dict]) -> bool:
        """Recarga completamente la lista de keywords."""
        return self.detector.reload_keywords(keywords)

    def get_stats(self) -> dict:
        """Retorna estadísticas del detector."""
        return self.detector.get_stats()


# Test
if __name__ == '__main__':
    import sys
    sys.path.append('/home/orangepi/asistente2/src')

    logging.basicConfig(level=logging.INFO)

    # Test solo si hay access key
    import os
    access_key = os.environ.get("PICOVOCICE_ACCESS_KEY")

    if not access_key:
        print("Set PICOVOCICE_ACCESS_KEY environment variable")
        exit(1)

    # Ejemplo con múltiples keywords
    keywords_config = [
        {
            "path": "/home/orangepi/asistente2/models/wakeword/asistente_es.ppn",
            "sensitivity": 0.5,
            "name": "asistente"
        },
        # Agrega más keywords aquí
        # {
        #     "path": "/ruta/a/otro.ppn",
        #     "sensitivity": 0.5,
        #     "name": "otra_palabra"
        # },
    ]

    # Verificar que los archivos existen
    for kw in keywords_config:
        if not os.path.exists(kw["path"]):
            print(f"Keyword file not found: {kw['path']}")
            exit(1)

    def on_detected(keyword_name: str):
        print(f"\n🎤 ¡WAKE WORD '{keyword_name}' DETECTADO! 🎤\n")

    engine = WakeWordEngine(
        access_key=access_key,
        keywords=keywords_config,
        on_detection=on_detected
    )

    from audio.capture import AudioCapture

    capture = AudioCapture(sample_rate=16000)
    engine.start(capture)

    print("Escuchando wake words... Ctrl+C para salir")
    print(f"Keywords configurados: {engine.get_keyword_names()}")

    try:
        while True:
            import time
            time.sleep(0.1)
    except KeyboardInterrupt:
        engine.stop()
        capture.stop()
