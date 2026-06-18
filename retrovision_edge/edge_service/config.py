"""
RetroVision Edge Service - Configuración

Módulo de configuración centralizado para el microservicio Edge.
Maneja variables de entorno y parámetros del sistema.
"""

import os
import json
from dataclasses import dataclass
from typing import Optional, Union

from .camera_config_client import CameraConfigClient


@dataclass
class VideoConfig:
    """Configuración de captura de video."""
    camera_index: int = 0
    video_source: Union[int, str] = 0
    frame_width: int = 1280
    frame_height: int = 720
    fps: int = 30
    fourcc_codec: str = 'MJPG'  # Motion JPEG para mejor compresión
    timeout_seconds: int = 10


@dataclass
class RingBufferConfig:
    """Configuración del Ring Buffer para almacenamiento en RAM."""
    buffer_duration_seconds: int = 30
    cleanup_interval_seconds: int = 60


@dataclass
class MQTTConfig:
    """Configuración del broker MQTT."""
    broker_host: str = "localhost"
    broker_port: int = 1883
    client_id: str = "retrovision-edge-01"
    camera_id: str = "camera-01"
    topic: str = "retrovision/edge/alerts"
    telemetry_topic: str = "retrovision/telemetry"
    roi_polygon: list = None
    queue_wait_threshold: float = 5.0
    queue_roi_polygon: list = None
    queue_dwell_seconds: float = 2.0
    queue_alert_people_threshold: int = 3
    queue_alert_duration_seconds: float = 5.0
    max_allowed_wait_seconds: float = 120.0
    cashier_count: int = 1
    service_rate_per_cashier_per_minute: float = 12.0
    keep_alive: int = 60
    enabled: bool = True


@dataclass
class LoggingConfig:
    """Configuración de logging."""
    level: str = "INFO"
    log_file: str = "logs/edge_service.log"
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5


@dataclass
class BackendApiConfig:
    """Configuración para sincronizar perfiles de cámara con el backend."""
    base_url: str = "http://localhost:8000"
    edge_node_id: str = ""
    edge_api_key: str = ""
    username: str = ""
    password: str = ""
    token: str = ""
    timeout_seconds: int = 10
    sync_camera_config: bool = False


@dataclass
class ControlApiConfig:
    """Configuración HTTP local del edge para snapshots y control liviano."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8081


class EdgeServiceConfig:
    """Clase principal de configuración. Gestiona todas las secciones."""

    @staticmethod
    def _parse_video_source(raw_value: Optional[str], fallback_camera_index: int) -> Union[int, str]:
        """
        Normaliza la fuente de video desde variables de entorno.

        Reglas:
        - Si no existe VIDEO_SOURCE, usa CAMERA_INDEX para mantener compatibilidad.
        - Si VIDEO_SOURCE es un entero, se interpreta como índice de webcam.
        - En otro caso se trata como URL RTSP o ruta de archivo.
        """
        if raw_value is None or raw_value.strip() == "":
            return fallback_camera_index

        normalized = raw_value.strip()
        try:
            return int(normalized)
        except ValueError:
            return normalized

    def __init__(self):
        """Inicializa la configuración desde variables de entorno."""
        camera_index = int(os.getenv('CAMERA_INDEX', 0))
        video_source = self._parse_video_source(
            os.getenv('VIDEO_SOURCE'),
            fallback_camera_index=camera_index,
        )

        self.video = VideoConfig(
            camera_index=camera_index,
            video_source=video_source,
            frame_width=int(os.getenv('FRAME_WIDTH', 1280)),
            frame_height=int(os.getenv('FRAME_HEIGHT', 720)),
            fps=int(os.getenv('FPS', 30)),
        )

        self.ring_buffer = RingBufferConfig(
            buffer_duration_seconds=int(os.getenv('BUFFER_DURATION', 30)),
        )

        # Parse polygon ROI
        roi_env = os.getenv('ROI_POLYGON', '[[500, 350], [900, 350], [1100, 650], [400, 650]]')
        try:
            roi_poly = json.loads(roi_env)
        except Exception:
            roi_poly = [[500, 350], [900, 350], [1100, 650], [400, 650]]

        queue_roi_env = os.getenv('QUEUE_ROI_POLYGON', roi_env)
        try:
            queue_roi_poly = json.loads(queue_roi_env)
        except Exception:
            queue_roi_poly = roi_poly

        self.mqtt = MQTTConfig(
            broker_host=os.getenv('MQTT_BROKER_HOST', 'localhost'),
            broker_port=int(os.getenv('MQTT_BROKER_PORT', 1883)),
            client_id=os.getenv('MQTT_CLIENT_ID', 'retrovision-edge-01'),
            camera_id=os.getenv('CAMERA_ID', 'camera-01'),
            topic=os.getenv('MQTT_ALERTS_TOPIC', 'retrovision/edge/alerts'),
            telemetry_topic=os.getenv('MQTT_TELEMETRY_TOPIC', 'retrovision/telemetry'),
            roi_polygon=roi_poly,
            queue_wait_threshold=float(os.getenv('QUEUE_WAIT_THRESHOLD', 5.0)),
            queue_roi_polygon=queue_roi_poly,
            queue_dwell_seconds=float(os.getenv('QUEUE_DWELL_SECONDS', 2.0)),
            queue_alert_people_threshold=int(os.getenv('QUEUE_ALERT_PEOPLE_THRESHOLD', 3)),
            queue_alert_duration_seconds=float(os.getenv('QUEUE_ALERT_DURATION_SECONDS', 5.0)),
            max_allowed_wait_seconds=float(os.getenv('MAX_ALLOWED_WAIT_SECONDS', 120.0)),
            cashier_count=int(os.getenv('CASHIER_COUNT', 1)),
            service_rate_per_cashier_per_minute=float(os.getenv('SERVICE_RATE_PER_CASHIER_PER_MINUTE', 12.0)),
            keep_alive=int(os.getenv('MQTT_KEEP_ALIVE', 60)),
            enabled=os.getenv('MQTT_ENABLED', 'true').lower() == 'true',
        )

        self.logging = LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'logs/edge_service.log'),
        )

        self.backend_api = BackendApiConfig(
            base_url=os.getenv('BACKEND_API_BASE_URL', 'http://localhost:8000'),
            edge_node_id=os.getenv('EDGE_NODE_ID', ''),
            edge_api_key=os.getenv('EDGE_API_KEY', ''),
            username=os.getenv('BACKEND_API_USERNAME', ''),
            password=os.getenv('BACKEND_API_PASSWORD', ''),
            token=os.getenv('BACKEND_API_TOKEN', ''),
            timeout_seconds=int(os.getenv('BACKEND_API_TIMEOUT', 10)),
            sync_camera_config=os.getenv('SYNC_CAMERA_CONFIG', 'false').lower() == 'true',
        )

        self.control_api = ControlApiConfig(
            enabled=os.getenv('CONTROL_API_ENABLED', 'true').lower() == 'true',
            host=os.getenv('CONTROL_API_HOST', '0.0.0.0'),
            port=int(os.getenv('CONTROL_API_PORT', 8081)),
        )

        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self._apply_remote_camera_profile()

    def _apply_remote_camera_profile(self) -> None:
        """Sobrescribe la configuración local con el perfil de cámara remoto si está habilitado."""
        if not self.backend_api.sync_camera_config:
            return

        if not self.mqtt.camera_id:
            return

        try:
            client = CameraConfigClient(
                base_url=self.backend_api.base_url,
                edge_node_id=self.backend_api.edge_node_id,
                edge_api_key=self.backend_api.edge_api_key,
                token=self.backend_api.token,
                username=self.backend_api.username,
                password=self.backend_api.password,
                timeout_seconds=self.backend_api.timeout_seconds,
            )
            remote_profile = client.get_camera_profile(self.mqtt.camera_id)
            if not remote_profile:
                return

            remote_roi = remote_profile.get("roi_polygon")
            if isinstance(remote_roi, list) and remote_roi:
                self.mqtt.roi_polygon = remote_roi
            remote_queue_roi = remote_profile.get("queue_roi_polygon")
            if isinstance(remote_queue_roi, list) and remote_queue_roi:
                self.mqtt.queue_roi_polygon = remote_queue_roi

            remote_wait = remote_profile.get("queue_wait_threshold")
            if remote_wait is not None:
                self.mqtt.queue_wait_threshold = float(remote_wait)
            remote_dwell = remote_profile.get("queue_dwell_seconds")
            if remote_dwell is not None:
                self.mqtt.queue_dwell_seconds = float(remote_dwell)
            remote_people_threshold = remote_profile.get("queue_alert_people_threshold")
            if remote_people_threshold is not None:
                self.mqtt.queue_alert_people_threshold = int(remote_people_threshold)
            remote_alert_duration = remote_profile.get("queue_alert_duration_seconds")
            if remote_alert_duration is not None:
                self.mqtt.queue_alert_duration_seconds = float(remote_alert_duration)
            remote_max_wait = remote_profile.get("max_allowed_wait_seconds")
            if remote_max_wait is not None:
                self.mqtt.max_allowed_wait_seconds = float(remote_max_wait)
            remote_cashier_count = remote_profile.get("cashier_count")
            if remote_cashier_count is not None:
                self.mqtt.cashier_count = int(remote_cashier_count)
            remote_service_rate = remote_profile.get("service_rate_per_cashier_per_minute")
            if remote_service_rate is not None:
                self.mqtt.service_rate_per_cashier_per_minute = float(remote_service_rate)
        except Exception:
            # El edge debe seguir funcionando aunque el backend no responda.
            return

    def validate(self) -> None:
        """
        Valida la configuración.
        
        Raises:
            ValueError: Si algún parámetro es inválido.
        """
        if self.video.camera_index < 0:
            raise ValueError("camera_index debe ser >= 0")

        if isinstance(self.video.video_source, int) and self.video.video_source < 0:
            raise ValueError("video_source no puede ser un índice negativo")
        
        if self.video.frame_width <= 0 or self.video.frame_height <= 0:
            raise ValueError("Dimensiones de frame deben ser positivas")
        
        if self.video.fps <= 0:
            raise ValueError("FPS debe ser mayor a 0")
        
        if self.ring_buffer.buffer_duration_seconds <= 0:
            raise ValueError("buffer_duration_seconds debe ser mayor a 0")
