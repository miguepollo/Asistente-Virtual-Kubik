"""
Logging Module
Configura el sistema de logging con colores y rotación de archivos.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

try:
    from colorlog import ColoredFormatter
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class Logger:
    """Configura y gestiona el logging de la aplicación."""

    # Formato con colores
    COLOR_FORMAT = "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)-25s%(reset)s %(message)s"
    PLAIN_FORMAT = "%(levelname)-8s %(name)-25s %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # Formato para archivo (sin colores)
    FILE_FORMAT = "%(asctime)s - %(levelname)-8s - %(name)-25s - %(message)s"

    def __init__(
        self,
        name: str = "asistente",
        log_dir: str = "/home/orangepi/asistente/logs",
        level: str = "INFO",
        console: bool = True,
        file: bool = True
    ):
        """
        Args:
            name: Nombre del logger
            log_dir: Directorio para logs
            level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console: Si True, loguea a consola
            file: Si True, loguea a archivo
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.level = getattr(logging, level.upper(), logging.INFO)

        # Crear directorio de logs
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configurar logger raíz
        self.logger = logging.getLogger()
        self.logger.setLevel(self.level)

        # Limpiar handlers existentes
        self.logger.handlers.clear()

        # Console handler
        if console:
            self._add_console_handler()

        # File handler
        if file:
            self._add_file_handlers()

    def _add_console_handler(self) -> None:
        """Añade handler para consola con colores."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)

        if COLORLOG_AVAILABLE:
            formatter = ColoredFormatter(
                self.COLOR_FORMAT,
                datefmt=self.DATE_FORMAT,
                reset=True,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            formatter = logging.Formatter(self.PLAIN_FORMAT, self.DATE_FORMAT)

        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _add_file_handlers(self) -> None:
        """Añade handlers para archivos con rotación."""
        # Log principal
        main_log = self.log_dir / "assistant.log"
        main_handler = RotatingFileHandler(
            main_log,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(self.level)
        main_handler.setFormatter(logging.Formatter(self.FILE_FORMAT))
        self.logger.addHandler(main_handler)

        # Log de errores
        error_log = self.log_dir / "errors.log"
        error_handler = RotatingFileHandler(
            error_log,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(self.FILE_FORMAT))
        self.logger.addHandler(error_handler)

        # Log de debug (si está en modo debug)
        if self.level <= logging.DEBUG:
            debug_log = self.log_dir / "debug.log"
            debug_handler = RotatingFileHandler(
                debug_log,
                maxBytes=10 * 1024 * 1024,
                backupCount=3,
                encoding='utf-8'
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(logging.Formatter(self.FILE_FORMAT))
            self.logger.addHandler(debug_handler)

    @staticmethod
    def get(name: str) -> logging.Logger:
        """
        Obtiene un logger con el nombre especificado.

        Args:
            name: Nombre del logger

        Returns:
            Logger instance
        """
        return logging.getLogger(name)


def setup_logging(
    level: str = "INFO",
    log_dir: str = "/home/orangepi/asistente/logs"
) -> None:
    """
    Configura el logging para toda la aplicación.

    Args:
        level: Nivel de logging
        log_dir: Directorio para logs
    """
    Logger(level=level, log_dir=log_dir)


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado.

    Args:
        name: Nombre del logger (usualmente __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


if __name__ == '__main__':
    # Test del logger
    logger = Logger(level="DEBUG")

    log = get_logger("test")

    log.debug("Este es un mensaje DEBUG")
    log.info("Este es un mensaje INFO")
    log.warning("Este es un mensaje WARNING")
    log.error("Este es un mensaje ERROR")
    log.critical("Este es un mensaje CRITICAL")

    # Test desde otro módulo
    audio_log = get_logger("audio.capture")
    audio_log.info("Mensaje desde audio.capture")
