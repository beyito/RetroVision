"""
RetroVision Edge Service - Configuración

Módulo de configuración centralizado para el microservicio Edge.
Maneja variables de entorno y parámetros del sistema.
"""

import os
import json
from dataclasses import dataclass
from typing import Optional, Union


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
    keep_alive: int = 60
    enabled: bool = True


@dataclass
class LoggingConfig:
    """Configuración de logging."""
    level: str = "INFO"
    log_file: str = "logs/edge_service.log"
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5


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

        self.mqtt = MQTTConfig(
            broker_host=os.getenv('MQTT_BROKER_HOST', 'localhost'),
            broker_port=int(os.getenv('MQTT_BROKER_PORT', 1883)),
            client_id=os.getenv('MQTT_CLIENT_ID', 'retrovision-edge-01'),
            camera_id=os.getenv('CAMERA_ID', 'camera-01'),
            topic=os.getenv('MQTT_ALERTS_TOPIC', 'retrovision/edge/alerts'),
            telemetry_topic=os.getenv('MQTT_TELEMETRY_TOPIC', 'retrovision/telemetry'),
            roi_polygon=roi_poly,
            queue_wait_threshold=float(os.getenv('QUEUE_WAIT_THRESHOLD', 5.0)),
            keep_alive=int(os.getenv('MQTT_KEEP_ALIVE', 60)),
            enabled=os.getenv('MQTT_ENABLED', 'true').lower() == 'true',
        )

        self.logging = LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'logs/edge_service.log'),
        )

        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

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
