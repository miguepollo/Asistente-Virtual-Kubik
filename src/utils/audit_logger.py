"""
Módulo de Auditoría de Seguridad
Registra eventos de seguridad para análisis forense y detección de intrusos.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class AuditLogger:
    """
    Gestiona el registro de eventos de seguridad.

    Los eventos registrados incluyen:
    - Intentos de autenticación (exitosos y fallidos)
    - Intentos de acceso no autorizado
    - Violaciones de seguridad (path traversal, command injection)
    - Cambios en la configuración
    - Operaciones críticas del sistema
    """

    def __init__(self, log_dir: Path):
        """
        Inicializa el audit logger.

        Args:
            log_dir: Directorio donde guardar los logs de auditoría
        """
        self.log_dir = log_dir
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configura el logger de auditoría."""
        log_file = self.log_dir / "audit.log"

        # Crear directorio si no existe
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configurar handler
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

        # Configurar logger
        self.logger = logging.getLogger('security_audit')
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Prevenir duplicación de logs
        self.logger.propagate = False

    def log_auth_attempt(
        self,
        username: str,
        success: bool,
        ip: str = "unknown",
        user_agent: str = "unknown"
    ) -> None:
        """
        Registra un intento de autenticación.

        Args:
            username: Nombre de usuario
            success: Si el intento fue exitoso
            ip: Dirección IP del cliente
            user_agent: User-Agent del cliente
        """
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"AUTH {status} - user={username} ip={ip} ua={user_agent[:50]}")

    def log_auth_failure(
        self,
        username: str,
        reason: str,
        ip: str = "unknown"
    ) -> None:
        """
        Registra un fallo de autenticación con razón específica.

        Args:
            username: Nombre de usuario
            reason: Razón del fallo
            ip: Dirección IP del cliente
        """
        self.logger.warning(f"AUTH FAILED - user={username} reason={reason} ip={ip}")

    def log_authorization_failure(
        self,
        user: str,
        resource: str,
        ip: str = "unknown"
    ) -> None:
        """
        Registra un fallo de autorización (acceso denegado).

        Args:
            user: Usuario autenticado
            resource: Recurso al que se intentó acceder
            ip: Dirección IP del cliente
        """
        self.logger.warning(f"ACCESS DENIED - user={user} resource={resource} ip={ip}")

    def log_path_traversal_attempt(
        self,
        path: str,
        user: str = "unknown",
        ip: str = "unknown"
    ) -> None:
        """
        Registra un intento de path traversal.

        Args:
            path: Ruta maliciosa intentada
            user: Usuario (si está autenticado)
            ip: Dirección IP del cliente
        """
        self.logger.error(f"PATH_TRAVERSAL_ATTEMPT - path={path} user={user} ip={ip}")

    def log_command_injection_attempt(
        self,
        command: str,
        user: str = "unknown",
        ip: str = "unknown"
    ) -> None:
        """
        Registra un intento de inyección de comandos.

        Args:
            command: Comando malicioso intentado
            user: Usuario (si está autenticado)
            ip: Dirección IP del cliente
        """
        self.logger.error(f"COMMAND_INJECTION_ATTEMPT - cmd={command} user={user} ip={ip}")

    def log_invalid_input(
        self,
        field: str,
        value: str,
        user: str = "unknown",
        ip: str = "unknown"
    ) -> None:
        """
        Registra entrada inválida que fue rechazada.

        Args:
            field: Campo que recibió la entrada inválida
            value: Valor inválido (sanitizado en el log)
            user: Usuario (si está autenticado)
            ip: Dirección IP del cliente
        """
        # Sanitizar valor para el log
        safe_value = repr(value)[:100]
        self.logger.warning(f"INVALID_INPUT - field={field} value={safe_value} user={user} ip={ip}")

    def log_security_config_change(
        self,
        setting: str,
        old_value: str,
        new_value: str,
        user: str = "unknown"
    ) -> None:
        """
        Registra cambios en la configuración de seguridad.

        Args:
            setting: Configuración modificada
            old_value: Valor anterior
            new_value: Nuevo valor
            user: Usuario que hizo el cambio
        """
        self.logger.info(
            f"SECURITY_CONFIG_CHANGE - setting={setting} "
            f"old={old_value[:50]} new={new_value[:50]} user={user}"
        )

    def log_model_operation(
        self,
        operation: str,
        model_name: str,
        success: bool,
        user: str = "unknown"
    ) -> None:
        """
        Registra operaciones sobre modelos de IA.

        Args:
            operation: Operación realizada (download, delete, etc)
            model_name: Nombre del modelo
            success: Si la operación fue exitosa
            user: Usuario que realizó la operación
        """
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"MODEL_{operation} {status} - model={model_name} user={user}")

    def log_system_operation(
        self,
        operation: str,
        target: str,
        success: bool,
        user: str = "unknown"
    ) -> None:
        """
        Registra operaciones críticas del sistema.

        Args:
            operation: Operación realizada (start, stop, restart)
            target: Servicio objetivo
            success: Si la operación fue exitosa
            user: Usuario que realizó la operación
        """
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"SYSTEM_{operation} {status} - target={target} user={user}")

    def log_rate_limit_exceeded(
        self,
        endpoint: str,
        ip: str = "unknown"
    ) -> None:
        """
        Registra cuando se excede el límite de rate.

        Args:
            endpoint: Endpoint que excedió el límite
            ip: Dirección IP del cliente
        """
        self.logger.warning(f"RATE_LIMIT_EXCEEDED - endpoint={endpoint} ip={ip}")
